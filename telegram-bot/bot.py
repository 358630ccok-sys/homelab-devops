import os
import re
import html
import shlex
import shutil
import tempfile
import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, Voice, Audio
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.methods import SendChatAction
from dotenv import load_dotenv

load_dotenv('/opt/telegram-bot/.env')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
ALLOWED_USER_ID = int(os.getenv('ALLOWED_USER_ID', '0'))
PROXY_URL = os.getenv('PROXY_URL')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://192.168.10.103:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5-coder:1.5b')
DIFY_APP_URL = os.getenv('DIFY_APP_URL', 'http://192.168.10.112:3002').rstrip('/')
DIFY_APP_API_KEY = os.getenv('DIFY_APP_API_KEY', '')
WHISPER_URL = os.getenv('WHISPER_URL', 'http://192.168.10.103:8080').rstrip('/')
CONVERSATIONS = {}

if not BOT_TOKEN:
    logger.error('BOT_TOKEN not found!')
    exit(1)

WG_CONFIG_PATH = '/opt/telegram-bot/wireguard-phone.conf'
MAGNET_PATTERN = re.compile(r'magnet:\?xt=urn:btih:[a-zA-Z0-9]+')
YOUTUBE_RE = re.compile(r'(?:youtube\.com/(?:watch\?.*?v=|shorts/|embed/|live/)|youtu\.be/)([\w-]{11})', re.IGNORECASE)

SYSTEM_PROMPT = (
    "Ты — полезный ассистент. Отвечай ИСКЛЮЧИТЕЛЬНО на русском языке. "
    "Не пиши свои размышления, внутренние мысли, черновики и рассуждения — выдавай только готовый ответ. "
    "Если тебя просят написать код — выводи только код, без пояснений. "
    "Никогда не используй теги  thinking, <thinking> и подобные."
)
THINK_PAIR_RE = re.compile(r'<think\b[^>]*>.*?</think\s*>', re.DOTALL | re.IGNORECASE)
THINK_TAG_RE = re.compile(r'</?think\b[^>]*>', re.IGNORECASE)
THINK_OPEN_RE = re.compile(r'<think\b[^>]*>', re.IGNORECASE)
THINK_CLOSE = '</think>'


def clean_reply(text: str) -> str:
    """Убрать размышления модели: парные теги, одиночный </think> и незакрытый  thinking."""
    if not text:
        return ''
    text = THINK_PAIR_RE.sub('', text)
    pos = text.lower().rfind(THINK_CLOSE)
    if pos != -1:
        text = text[pos + len(THINK_CLOSE):]
    m = THINK_OPEN_RE.search(text)
    if m:
        text = text[:m.start()]
    text = THINK_TAG_RE.sub('', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()



async def ask_dify(chat_id: int, query: str) -> str:
    if not DIFY_APP_API_KEY:
        return 'Ошибка: не настроен DIFY_APP_API_KEY.'
    headers = {'Authorization': f'Bearer {DIFY_APP_API_KEY}', 'Content-Type': 'application/json'}
    payload = {
        'inputs': {},
        'query': query,
        'response_mode': 'blocking',
        'user': f'tg-{chat_id}',
    }
    conv = CONVERSATIONS.get(chat_id)
    if conv:
        payload['conversation_id'] = conv
    timeout = aiohttp.ClientTimeout(total=300)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f'{DIFY_APP_URL}/v1/chat-messages', headers=headers, json=payload) as resp:
                data = await resp.json(content_type=None)
                if resp.status != 200:
                    logger.error('Dify error %s: %s', resp.status, str(data)[:500])
                    return f'Ошибка Dify ({resp.status}): {str(data)[:300]}'
                cid = data.get('conversation_id')
                if cid:
                    CONVERSATIONS[chat_id] = cid
                answer = data.get('answer') or ''
                return clean_reply(answer).strip() or 'Пустой ответ от Dify.'
    except Exception as e:
        logger.exception('Dify request failed')
        return f'Ошибка запроса к Dify: {e}'


async def transcribe_telegram_file(bot: Bot, file_id: str, suffix: str = '.ogg') -> str:
    tg_file = await bot.get_file(file_id)
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        await bot.download_file(tg_file.file_path, tmp_path)
        timeout = aiohttp.ClientTimeout(total=300)
        with open(tmp_path, 'rb') as f:
            form = aiohttp.FormData()
            form.add_field('file', f, filename=os.path.basename(tmp_path), content_type='application/octet-stream')
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f'{WHISPER_URL}/transcribe', data=form) as resp:
                    data = await resp.json(content_type=None)
                    if resp.status != 200:
                        raise RuntimeError(f'whisper {resp.status}: {str(data)[:300]}')
                    return (data.get('text') or '').strip()
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


YTDLP_BIN = '/opt/telegram-bot/venv/bin/yt-dlp'
AUDIO_DIR = '/tmp/ytaudio'
FFMPEG_PATH = '/usr/bin/ffmpeg'
MAX_AUDIO_SIZE = 50 * 1024 * 1024  # лимит Telegram Bot API на отправку файлов


def normalize_youtube_url(text: str):
    m = YOUTUBE_RE.search(text)
    if not m:
        return None
    return f'https://www.youtube.com/watch?v={m.group(1)}'


async def download_audio(url: str) -> tuple[str, str]:
    """Скачать аудио c YouTube в MP3 через yt-dlp. Возвращает (путь_к_mp3, название)."""
    os.makedirs(AUDIO_DIR, exist_ok=True)
    workdir = tempfile.mkdtemp(prefix='audio_', dir=AUDIO_DIR)
    try:
        cmd = [
            YTDLP_BIN,
            '--proxy', PROXY_URL or 'socks5://192.168.10.115:1080',
            '-x', '--audio-format', 'mp3',
            '--audio-quality', '0',
            '--no-playlist',
            '--no-warnings',
            '--ffmpeg-location', FFMPEG_PATH,
            '-o', os.path.join(workdir, 'audio.%(ext)s'),
            '--print', 'after_move:%(filepath)s',
            '--print', '%(title)s',
            url,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=300)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            raise RuntimeError('Таймаут при скачивании (видео слишком длинное?)')
        if proc.returncode != 0:
            raise RuntimeError(err.decode('utf-8', errors='replace')[-1200:] or 'Ошибка yt-dlp')
        path = None
        title = ''
        for line in out.decode('utf-8', errors='replace').splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith('/'):
                path = line
            elif not title:
                title = line
        if not path or not os.path.exists(path):
            path = os.path.join(workdir, 'audio.mp3')
        if not os.path.exists(path):
            raise RuntimeError('Не удалось найти скачанный файл')
        title = title or 'audio'
        return path, title
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        raise


async def ask_ollama(prompt: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                'model': OLLAMA_MODEL,
                'system': SYSTEM_PROMPT,
                'prompt': prompt,
                'stream': False,
                'options': {'num_ctx': 2048}
            }
            async with session.post(f'{OLLAMA_URL}/api/generate', json=payload, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    reply = clean_reply(data.get('response', ''))
                    if not reply:
                        return 'Нет ответа'
                    return reply
                else:
                    return f'Ошибка Ollama: {resp.status}'
    except Exception as e:
        logger.error(f'Ollama error: {e}')
        return 'Ошибка подключения к Ollama'


async def run_ssh(cmd: str) -> str:
    """Выполнить команду на хосте Proxmox через SSH (ключ уже настроен)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            'ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=no',
            '-o', 'ConnectTimeout=6', 'ai-agent@192.168.10.100', cmd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        text = out.decode('utf-8', errors='replace').strip()
        return text or 'Нет вывода'
    except asyncio.TimeoutError:
        return 'Ошибка: таймаут SSH-команды'
    except Exception as e:
        logger.error(f'SSH error: {e}')
        return f'Ошибка SSH: {e}'


async def main():
    session = AiohttpSession(proxy=PROXY_URL, timeout=600) if PROXY_URL else None
    bot = Bot(token=BOT_TOKEN, session=session)
    dp = Dispatcher()
    router = Router()

    def is_allowed(user_id: int) -> bool:
        return user_id == ALLOWED_USER_ID

    async def send_youtube_audio(message: Message, url: str):
        status = await message.answer('Скачиваю аудио, подожди...')
        await bot(SendChatAction(chat_id=message.chat.id, action='upload_audio'))
        try:
            path, title = await asyncio.wait_for(download_audio(url), timeout=360)
        except asyncio.TimeoutError:
            await status.edit_text('Скачивание заняло слишком много времени, попробуй ещё раз')
            return
        except Exception as e:
            logger.error(f'yt-dlp error: {e}')
            await status.edit_text('Не удалось скачать аудио, проверь ссылку.')
            return
        try:
            size = os.path.getsize(path)
            if size > MAX_AUDIO_SIZE:
                await status.edit_text('Файл больше 50 МБ — Telegram не принимает такие аудио. Попробуй более короткое видео.')
                return
            fname = re.sub(r'[^\w\- ]+', '', title) or 'audio'
            audio = FSInputFile(path, filename=f'{fname[:120]}.mp3')
            await status.delete()
            await message.answer_audio(audio, caption=title[:1024])
        finally:
            shutil.rmtree(os.path.dirname(path), ignore_errors=True)

    @router.message(Command('start'))
    async def cmd_start(message: Message):
        if message.chat.type != 'private':
            return
        if not is_allowed(message.from_user.id):
            await message.answer('Access denied')
            return
        parts = message.text.split()
        if len(parts) >= 2:
            # /start <ID> — запустить контейнер
            ct_id = parts[1]
            if not re.fullmatch(r'\d+', ct_id):
                await message.answer('Некорректный ID контейнера (только цифры)')
                return
            await bot(SendChatAction(chat_id=message.chat.id, action='typing'))
            reply = await run_ssh(f'sudo -n /usr/sbin/pct start {ct_id}')
            await message.answer(f'Контейнер {ct_id} запускается:\n<pre>{reply[:3500]}</pre>', parse_mode='HTML')
            return
        await message.answer(
            'Привет! Доступные команды:\n'
            '/status - статус контейнеров Proxmox\n'
            '/start <ID> - запустить контейнер\n'
            '/stop <ID> - остановить контейнер\n'
            '/logs <ID> - логи контейнера\n'
            '/getwg - получить WireGuard конфиг\n'
            '/audio <ссылка YouTube> - скачать аудио в MP3\n'
            '/ai <текст> - спросить у Ollama\n'
            '/help - помощь\n\n'
            'Прислать magnet-ссылку — добавлю в закачку.\n'
            'Прислать ссылку на YouTube — скачаю аудио.\n'
            'Любой другой текст — отвечу через Ollama.'
        )

    @router.message(Command('status'))
    async def cmd_status(message: Message):
        if message.chat.type != 'private':
            return
        if not is_allowed(message.from_user.id):
            await message.answer('Access denied')
            return
        await bot(SendChatAction(chat_id=message.chat.id, action='typing'))
        reply = await run_ssh('sudo -n /usr/sbin/pct list')
        await message.answer(f'<pre>{reply[:3500]}</pre>', parse_mode='HTML')

    @router.message(Command('stop'))
    async def cmd_stop(message: Message):
        if message.chat.type != 'private':
            return
        if not is_allowed(message.from_user.id):
            await message.answer('Access denied')
            return
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer('Используйте: /stop <ID>')
            return
        ct_id = parts[1]
        if not re.fullmatch(r'\d+', ct_id):
            await message.answer('Некорректный ID контейнера (только цифры)')
            return
        await bot(SendChatAction(chat_id=message.chat.id, action='typing'))
        reply = await run_ssh(f'sudo -n /usr/sbin/pct stop {ct_id}')
        await message.answer(f'Контейнер {ct_id} останавливается:\n<pre>{reply[:3500]}</pre>', parse_mode='HTML')

    @router.message(Command('logs'))
    async def cmd_logs(message: Message):
        if message.chat.type != 'private':
            return
        if not is_allowed(message.from_user.id):
            await message.answer('Access denied')
            return
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer('Используйте: /logs <ID>')
            return
        ct_id = parts[1]
        if not re.fullmatch(r'\d+', ct_id):
            await message.answer('Некорректный ID контейнера (только цифры)')
            return
        await bot(SendChatAction(chat_id=message.chat.id, action='typing'))
        reply = await run_ssh(f'sudo -n /usr/sbin/pct logs {ct_id} 2>/dev/null | tail -30')
        await message.answer(f'<pre>{reply[:3500]}</pre>', parse_mode='HTML')

    @router.message(Command('help'))
    async def cmd_help(message: Message):
        if message.chat.type != 'private':
            return
        if not is_allowed(message.from_user.id):
            await message.answer('Access denied')
            return
        await message.answer(
            '/start - приветствие\n'
            '/status - статус контейнеров Proxmox\n'
            '/start <ID> - запустить контейнер\n'
            '/stop <ID> - остановить контейнер\n'
            '/logs <ID> - логи контейнера\n'
            '/getwg - скачать WireGuard конфиг\n'
            '/audio <ссылка YouTube> - скачать аудио в MP3\n'
            '/ai <текст> - вопрос к Ollama\n'
            '/model - текущая модель\n'
            '/help - эта справка\n\n'
            'Пришли magnet-ссылку — скачаю на сервер.\n'
            'Пришли ссылку на YouTube — скачаю аудио.\n'
            'Или просто напиши — отвечу через Ollama.'
        )

    @router.message(Command('model'))
    async def cmd_model(message: Message):
        if message.chat.type != 'private':
            return
        if not is_allowed(message.from_user.id):
            return
        await message.answer(f'Текущая модель: {OLLAMA_MODEL}')

    @router.message(Command('getwg'))
    async def cmd_getwg(message: Message):
        if message.chat.type != 'private':
            return
        if not is_allowed(message.from_user.id):
            await message.answer('Access denied')
            return
        if not os.path.exists(WG_CONFIG_PATH):
            await message.answer('Файл конфига не найден')
            return
        doc = FSInputFile(WG_CONFIG_PATH)
        await message.answer_document(doc, caption='WireGuard конфиг для телефона')

    @router.message(Command('audio'))
    async def cmd_audio(message: Message):
        if message.chat.type != 'private':
            return
        if not is_allowed(message.from_user.id):
            await message.answer('Access denied')
            return
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await message.answer('Используйте: /audio <ссылка на YouTube>')
            return
        url = normalize_youtube_url(parts[1])
        if not url:
            await message.answer('Это не похоже на ссылку YouTube')
            return
        await send_youtube_audio(message, url)

    @router.message(Command('reset'))
    async def cmd_reset(message: Message):
        if message.chat.type != 'private':
            return
        if not is_allowed(message.from_user.id):
            return
        CONVERSATIONS.pop(message.chat.id, None)
        await message.answer('Контекст диалога сброшен.')

    @router.message(Command('ai'))
    async def cmd_ai(message: Message):
        if message.chat.type != 'private':
            return
        if not is_allowed(message.from_user.id):
            return
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await message.answer('Используйте: /ai <вопрос>')
            return
        await bot(SendChatAction(chat_id=message.chat.id, action='typing'))
        reply = await ask_ollama(parts[1])
        await message.answer(reply)

    @router.message(lambda m: m.voice is not None or m.audio is not None)
    async def handle_voice(message: Message):
        if message.chat.type != 'private':
            return
        if not is_allowed(message.from_user.id):
            return
        try:
            if message.voice:
                file_id = message.voice.file_id
                suffix = '.ogg'
            else:
                file_id = message.audio.file_id
                fname = getattr(message.audio, 'file_name', None) or 'audio.mp3'
                suffix = os.path.splitext(fname)[1] or '.mp3'
            await bot(SendChatAction(chat_id=message.chat.id, action='typing'))
            text = await transcribe_telegram_file(bot, file_id, suffix=suffix)
            if not text:
                await message.answer('Не удалось распознать речь (пустой результат).')
                return
            await message.answer(f'🎙️ Распознано: {text}')
            await bot(SendChatAction(chat_id=message.chat.id, action='typing'))
            reply = await ask_dify(message.chat.id, text)
            await message.answer(reply)
        except Exception as e:
            logger.exception('voice handling failed')
            await message.answer(f'Ошибка обработки голосового: {e}')

    @router.message()
    async def handle_message(message: Message):
        if message.chat.type != 'private':
            return
        if not is_allowed(message.from_user.id):
            return
        if not message.text:
            return

        match = MAGNET_PATTERN.search(message.text)
        if match:
            magnet = match.group(0)
            await message.answer('Добавляю в закачку...')
            await message.answer('magnet-ссылки пока не поддерживаются')
            return

        yt_link = normalize_youtube_url(message.text)
        if yt_link:
            await send_youtube_audio(message, yt_link)
            return

        await bot(SendChatAction(chat_id=message.chat.id, action='typing'))
        reply = await ask_dify(message.chat.id, message.text)
        await message.answer(reply)

    logger.info('Starting bot...')
    dp.include_router(router)
    await dp.start_polling(bot, logger=logger)

if __name__ == '__main__':
    asyncio.run(main())
