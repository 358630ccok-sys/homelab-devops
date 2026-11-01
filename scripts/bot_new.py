import os
import re
import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from aiogram.client.session.aiohttp import AiohttpSession
from dotenv import load_dotenv

load_dotenv('/opt/telegram-bot/.env')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
ALLOWED_USER_ID = int(os.getenv('ALLOWED_USER_ID', '0'))
PROXY_URL = os.getenv('PROXY_URL')
QB_URL = os.getenv('QB_URL', 'http://192.168.10.119:8080')
QB_USER = os.getenv('QB_USER', 'admin')
QB_PASS = os.getenv('QB_PASS', 'adminadmin')

if not BOT_TOKEN:
    logger.error('BOT_TOKEN not found!')
    exit(1)

WG_CONFIG_PATH = '/opt/telegram-bot/wireguard-phone.conf'
MAGNET_PATTERN = re.compile(r'magnet:\?xt=urn:btih:[a-zA-Z0-9]+')

qb_sid = None

async def qb_login():
    global qb_sid
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{QB_URL}/api/v2/auth/login',
                                    data={'username': QB_USER, 'password': QB_PASS}) as resp:
                if resp.status == 200:
                    cookies = resp.cookies
                    qb_sid = cookies.get('SID', None)
                    if qb_sid:
                        qb_sid = qb_sid.value
                        logger.info(f'qBittorrent SID obtained: {qb_sid[:10]}...')
                        return True
        logger.error('Failed to get qBittorrent SID')
        return False
    except Exception as e:
        logger.error(f'qBittorrent login error: {e}')
        return False

async def qb_add_magnet(magnet: str) -> str:
    global qb_sid
    if not qb_sid:
        if not await qb_login():
            return '╨Ю╤И╨╕╨▒╨║╨░ ╨┐╨╛╨┤╨║╨╗╤О╤З╨╡╨╜╨╕╤П ╨║ qBittorrent'
    try:
        async with aiohttp.ClientSession(cookies={'SID': qb_sid}) as session:
            async with session.post(f'{QB_URL}/api/v2/torrents/add',
                                    data={'urls': magnet}) as resp:
                if resp.status == 200:
                    return '╨Ф╨╛╨▒╨░╨▓╨╗╨╡╨╜╨╛ ╨▓ ╨╖╨░╨║╨░╤З╨║╤Г!'
                elif resp.status == 403:
                    await qb_login()
                    return '╨Ю╤И╨╕╨▒╨║╨░ ╨░╨▓╤В╨╛╤А╨╕╨╖╨░╤Ж╨╕╨╕, ╨┐╨╛╨┐╤А╨╛╨▒╤Г╨╣ ╨╡╤Й╤С ╤А╨░╨╖'
                else:
                    text = await resp.text()
                    return f'╨Ю╤И╨╕╨▒╨║╨░ qBittorrent: {resp.status}'
    except Exception as e:
        return f'╨Ю╤И╨╕╨▒╨║╨░: {e}'

async def main():
    session = AiohttpSession(proxy=PROXY_URL) if PROXY_URL else None
    bot = Bot(token=BOT_TOKEN, session=session)
    dp = Dispatcher()
    router = Router()

    def is_allowed(user_id: int) -> bool:
        return user_id == ALLOWED_USER_ID

    @router.message(Command('start'))
    async def cmd_start(message: Message):
        if not is_allowed(message.from_user.id):
            await message.answer('Access denied')
            return
        await message.answer('╨Я╤А╨╕╨▓╨╡╤В! ╨Ф╨╛╤Б╤В╤Г╨┐╨╜╤Л╨╡ ╨║╨╛╨╝╨░╨╜╨┤╤Л:\n/getwg - ╨┐╨╛╨╗╤Г╤З╨╕╤В╤М WireGuard ╨║╨╛╨╜╤Д╨╕╨│\n/help - ╨┐╨╛╨╝╨╛╤Й╤М\n\n╨в╨░╨║╨╢╨╡ ╨╝╨╛╨╢╨╜╨╛ ╨┐╤А╨╕╤Б╨╗╨░╤В╤М magnet-╤Б╤Б╤Л╨╗╨║╤Г тАФ ╤П ╨┤╨╛╨▒╨░╨▓╨╗╤О ╨╡╤С ╨▓ ╨╖╨░╨║╨░╤З╨║╤Г.\n\n╨Ы╤О╨▒╨╛╨╣ ╨┤╤А╤Г╨│╨╛╨╣ ╤В╨╡╨║╤Б╤В ╤П ╨╛╤В╨┐╤А╨░╨▓╨╗╤О ╨╛╤А╨║╨╡╤Б╤В╤А╨░╤В╨╛╤А╤Г Proxmox ╨┤╨╗╤П ╨▓╤Л╨┐╨╛╨╗╨╜╨╡╨╜╨╕╤П.')

    @router.message(Command('help'))
    async def cmd_help(message: Message):
        if not is_allowed(message.from_user.id):
            await message.answer('Access denied')
            return
        await message.answer('/start - ╨┐╤А╨╕╨▓╨╡╤В╤Б╤В╨▓╨╕╨╡\n/getwg - ╤Б╨║╨░╤З╨░╤В╤М WireGuard ╨║╨╛╨╜╤Д╨╕╨│\n/help - ╤Н╤В╨░ ╤Б╨┐╤А╨░╨▓╨║╨░\n\n╨Я╤А╨╕╤И╨╗╨╕ magnet-╤Б╤Б╤Л╨╗╨║╤Г тАФ ╤Б╨║╨░╤З╨░╤О ╨╜╨░ ╤Б╨╡╤А╨▓╨╡╤А.\n\n╨Ш╨╗╨╕ ╨┐╤А╨╛╤Б╤В╨╛ ╨╜╨░╨┐╨╕╤И╨╕ ╨╗╤О╨▒╤Г╤О ╨║╨╛╨╝╨░╨╜╨┤╤Г ╨┤╨╗╤П Proxmox ╨╜╨░ ╤А╤Г╤Б╤Б╨║╨╛╨╝ ╤П╨╖╤Л╨║╨╡.')

    @router.message(Command('getwg'))
    async def cmd_getwg(message: Message):
        if not is_allowed(message.from_user.id):
            await message.answer('Access denied')
            return
        if not os.path.exists(WG_CONFIG_PATH):
            await message.answer('╨д╨░╨╣╨╗ ╨║╨╛╨╜╤Д╨╕╨│╨░ ╨╜╨╡ ╨╜╨░╨╣╨┤╨╡╨╜')
            return
        doc = FSInputFile(WG_CONFIG_PATH)
        await message.answer_document(doc, caption='WireGuard ╨║╨╛╨╜╤Д╨╕╨│ ╨┤╨╗╤П ╤В╨╡╨╗╨╡╤Д╨╛╨╜╨░')

    @router.message()
    async def handle_message(message: Message):
        if not is_allowed(message.from_user.id):
            return
        if not message.text:
            return

        match = MAGNET_PATTERN.search(message.text)
        if match:
            magnet = match.group(0)
            await message.answer('╨Ф╨╛╨▒╨░╨▓╨╗╤П╤О ╨▓ ╨╖╨░╨║╨░╤З╨║╤Г...')
            result = await qb_add_magnet(magnet)
            await message.answer(result)
            logger.info(f'Magnet added from user {message.from_user.id}: {magnet[:50]}...')
            return

        await message.answer('ЁЯдЦ ╨Ч╨░╨┐╤А╨╛╤Б ╨╛╤В╨┐╤А╨░╨▓╨╗╨╡╨╜ ╨╛╤А╨║╨╡╤Б╤В╤А╨░╤В╨╛╤А╤Г Proxmox, ╨▓╤Л╨┐╨╛╨╗╨╜╤П╤О...')
        try:
            safe_text = message.text.replace('"', '\\"')
            cmd = f'ssh -o StrictHostKeyChecking=no root@192.168.10.100 "python3 /root/proxmox-local/orchestrator.py \\"{safe_text}\\""'
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            output = stdout.decode('utf-8', errors='ignore')
            if stderr:
                output += f"\n[STDERR]\n{stderr.decode('utf-8', errors='ignore')}"
            if not output.strip():
                output = "╨Ъ╨╛╨╝╨░╨╜╨┤╨░ ╨▓╤Л╨┐╨╛╨╗╨╜╨╡╨╜╨░, ╤Б╨╕╤Б╤В╨╡╨╝╨╜╤Л╨╣ ╨▓╤Л╨▓╨╛╨┤ ╨┐╤Г╤Б╤В."
            for i in range(0, len(output), 4000):
                await message.answer(output[i:i+4000])
        except Exception as e:
            await message.answer(f'╨Ю╤И╨╕╨▒╨║╨░: {e}')

    logger.info('Starting bot...')
    await qb_login()
    dp.include_router(router)
    await dp.start_polling(bot, logger=logger)

if __name__ == '__main__':
    asyncio.run(main())
