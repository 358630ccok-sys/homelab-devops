#!/usr/bin/env python3
import sys, os, re, subprocess, json, urllib.request, urllib.error, urllib.parse
import threading, time
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv("/root/proxmox-local/.env")
except ImportError:
    pass

os.environ['no_proxy'] = os.environ.get('no_proxy', '') + ',192.168.10.103,api.telegram.org'
os.environ['NO_PROXY'] = os.environ.get('NO_PROXY', '') + ',192.168.10.103,api.telegram.org'

OLLAMA_URL = "http://192.168.10.103:11434/api/chat"
OLLAMA_MODEL = "qwen2.5-coder:1.5b"
AGENTS_MD = "/root/proxmox-local/AGENTS.md"
MAX_HISTORY = 10

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
ADMIN_ID = os.getenv("ADMIN_ID", "")
REPORT_HOUR = int(os.getenv("REPORT_HOUR", "9"))

# WARN 2026-09-14: ╨Т╨б╨Х ╨╝╨╛╨┤╨╡╨╗╨╕ ╤Б╨▓╨╡╨┤╨╡╨╜╤Л ╨║ qwen2.5-coder:1.5b (~2.1 GB).
# granite4.1:8b (6.6 GB) ╨╕ mistral:7b (5 GB) ╨Т╨л╨Ч╨л╨Т╨Р╨Ы╨Ш ╨┐╨╡╤А╨╡╨┐╨╛╨╗╨╜╨╡╨╜╨╕╨╡ VRAM
# (GPU 8 GB) ╨╕ ╨╢╤С╤Б╤В╨║╨╕╨╣ ╨║╤А╨░╤Е ╨▓╤Б╨╡╨│╨╛ ╤Е╨╛╤Б╤В╨░ 2026-09-13. ╨Ч╨░╨┐╤Г╤Б╨║╨░╤В╤М >=8B ╨в╨Ю╨Ы╨м╨Ъ╨Ю
# ╨┐╤А╨╕ ╨┐╨╛╨┤╤В╨▓╨╡╤А╨╢╨┤╤С╨╜╨╜╨╛╨╝ ╤Б╨▓╨╛╨▒╨╛╨┤╨╜╨╛╨╝ VRAM > 7.5 GB тАФ ╤Б╨╝. vram_free_gb_ok().
MODEL_TIERS = {
    "FAST": "qwen2.5-coder:1.5b",
    "MEDIUM": "qwen2.5-coder:1.5b",
    "EXPERT": "qwen2.5-coder:1.5b",
}
HEAVY_MODELS = ("granite4.1:8b", "mistral:7b", "qwen3-coder:30b", "granite4.1:8b-gpu")
CLASSIFY_PROMPT = """Classify this admin prompt into EXACTLY one category. Reply with ONE word only:

FAST тАФ routine checks, status, simple one-shot commands (df, free, uptime, pct list, pct status, ss, cat, ls, ping, ollama list)
MEDIUM тАФ writing scripts, editing configs, multi-step tasks, formatting output, moderate analysis, code generation
EXPERT тАФ complex debugging, architectural decisions, long command chains, security analysis, refactoring, system design

Prompt: "{query}"

Category:"""

GENERATIVE_KEYWORDS = re.compile(
    r"(╨╜╨░╨┐╨╕╤И╨╕|╤Б╨╛╨╖╨┤╨░╨╣|╤Б╨│╨╡╨╜╨╡╤А╨╕╤А╤Г╨╣|╤Б╨┤╨╡╨╗╨░╨╣ ╤Б╨║╤А╨╕╨┐╤В|write|create|generate|make a script"
    r"|╨╜╨░╨┐╨╕╤И╨╕ ╤Б╨║╤А╨╕╨┐╤В|╨╜╨░╨┐╨╕╤И╨╕ ╨║╨╛╨┤|хЖЩхЗ║|хЖЩхЗ║шДЪцЬм|coding|╤А╨░╨╖╤А╨░╨▒╨╛╤В╨░╨╣|╨╛╤В╤А╨╡╤Д╨░╨║╤В╨╛╤А╨╕"
    r"|╤А╨╡╤Д╨░╨║╤В╨╛╤А╨╕╨╜╨│|╨┤╨╛╨▒╨░╨▓╤М ╤Д╤Г╨╜╨║╤Ж╨╕|╨┤╨╛╨▒╨░╨▓╤М ╨╝╨╛╨┤╤Г╨╗╤М|implement|refactor|refactoring"
    r"|╨╜╨░╤Б╤В╤А╨╛╨╣\s|╨╛╤В╤А╨╡╨┤╨░╨║╤В╨╕╤А╤Г╨╣|edit config|write a script|write a bash"
    r"|╤Б╨╛╤Б╤В╨░╨▓╤М ╨┐╨╗╨░╨╜|╨░╤А╤Е╨╕╤В╨╡╨║╤В╤Г╤А|╤Б╤В╤А╨░╤В╨╡╨│╨╕|roadmap|╨┐╤А╨╛╨╡╨║╤В|design|╤Б╨┐╤А╨╛╨╡╨║╤В╨╕╤А╤Г╨╣)",
    re.IGNORECASE
)

def is_generative(query):
    return bool(GENERATIVE_KEYWORDS.search(query))

CODE_KEYWORDS = re.compile(
    r"(╤Б╨║╤А╨╕╨┐╤В|╨║╨╛╨┤|bash|python|function|class|import|def |#!/bin|sql|docker|systemd|nginx|grep|awk|sed|curl|ssh|script)"
    r"|(╨╜╨░╨┐╨╕╤И╨╕|╤Б╨╛╨╖╨┤╨░╨╣|╤Б╨│╨╡╨╜╨╡╤А╨╕╤А╤Г╨╣|╨╛╤В╤А╨╡╤Д╨░╨║╤В╨╛╤А╨╕|╤А╨╡╤Д╨░╨║╤В╨╛╤А╨╕╨╜╨│|╨┤╨╛╨▒╨░╨▓╤М ╤Д╤Г╨╜╨║╤Ж╨╕|implement|refactor)",
    re.IGNORECASE
)

def vram_free_gb_ok(required_gb):
    """╨Я╤А╨╛╨▓╨╡╤А╨║╨░ ╤Б╨▓╨╛╨▒╨╛╨┤╨╜╨╛╨│╨╛ VRAM ╤З╨╡╤А╨╡╨╖ sysfs drm (avoid hot-loading models into full GPU).
       ╨Т╨╛╨╖╨▓╤А╨░╤Й╨░╨╡╤В True, ╨╡╤Б╨╗╨╕ ╤Б╨▓╨╛╨▒╨╛╨┤╨╜╨╛ >= required_gb. ╨Я╤А╨╕ ╨╗╤О╨▒╨╛╨╣ ╨╛╤И╨╕╨▒╨║╨╡ тАФ False (safe)."""
    try:
        for base in ("/sys/class/drm/card0/device", "/sys/class/drm/card1/device"):
            tot = used = None
            with open(base + "/mem_info_vram_total", "rb") as f:
                tot = int(f.read().strip()) / 1e9
            with open(base + "/mem_info_vram_used", "rb") as f:
                used = int(f.read().strip()) / 1e9
            if tot is not None and used is not None:
                free = tot - used
                print(f"[VRAM] total={tot:.1f}G used={used:.1f}G free={free:.1f}G need={required_gb}G -> {free >= required_gb}")
                return free >= required_gb
    except Exception as e:
        print(f"[VRAM] check failed: {e}")
    return False


def select_model(query):
    """╨Ь╨░╤А╤И╤А╤Г╤В╨╕╨╖╨░╤Ж╨╕╤П ╨С╨Х╨Ч╨Ю╨Я╨Р╨б╨Э╨Р╨п (╨┐╨╛╤Б╨╗╨╡ ╨║╤А╨░╤Е╨░ 2026-09-13, ╨┐╨╡╤А╨╡╨┐╨╛╨╗╨╜╨╡╨╜╨╕╨╡ VRAM):
       ╨▓╤Б╨╡╨│╨┤╨░ ╨╗╤С╨│╨║╨░╤П ╨╝╨╛╨┤╨╡╨╗╤М qwen2.5-coder:1.5b. ╨в╤П╨╢╤С╨╗╤Л╨╡ ╨╝╨╛╨┤╨╡╨╗╨╕ ╨╜╨╡╨┤╨╛╤Б╤В╤Г╨┐╨╜╤Л,
       ╤В.╨║. 8B+ ╨╜╨╡ ╨▓╨╗╨╡╨╖╨░╤О╤В ╨▓ 8GB VRAM ╨│╨░╤А╨░╨╜╤В╨╕╤А╨╛╨▓╨░╨╜╨╜╨╛."""
    return "qwen2.5-coder:1.5b"

SCRIPT_MARKERS = re.compile(
    r"(#!/bin/(ba)?sh|#!/usr/bin/env (ba)?sh|function\s+\w+\s*\(|for\s+\w+\s+in\s|while\s*\[|if\s*\[\s*['\"]|case\s+\w+\s+in|end\s*$)",
    re.MULTILINE | re.IGNORECASE
)

def is_script_like(text):
    return bool(SCRIPT_MARKERS.search(text))

SYSTEM_TEMPLATE = """╨в╤Л тАФ ╨░╨▓╤В╨╛╨╜╨╛╨╝╨╜╤Л╨╣ ╨Ш╨Ш-╨╛╤А╨║╨╡╤Б╤В╤А╨░╤В╨╛╤А Proxmox. ╨Ю╤В╨▓╨╡╤З╨░╨╣ ╤В╨╛╨╗╤М╨║╨╛ ╨╜╨░ ╤А╤Г╤Б╤Б╨║╨╛╨╝ ╤П╨╖╤Л╨║╨╡.
╨в╨▓╨╛╤П ╤Ж╨╡╨╗╤М тАФ ╤А╨╡╤И╨░╤В╤М ╨╖╨░╨┤╨░╤З╨╕ ╨░╨┤╨╝╨╕╨╜╨░. ╨в╤Л ╨╝╨╛╨╢╨╡╤И╤М ╨▓╤Л╨┐╨╛╨╗╨╜╤П╤В╤М ╨║╨╛╨╝╨░╨╜╨┤╤Л ╨┐╨╛╤Б╨╗╨╡╨┤╨╛╨▓╨░╤В╨╡╨╗╤М╨╜╨╛ (╨╛╨┤╨╜╨░ ╨╖╨░ ╨┤╤А╤Г╨│╨╛╨╣).

╨Я╨а╨Р╨Т╨Ш╨Ы╨Р:
1. ╨Х╤Б╨╗╨╕ ╨┤╨╗╤П ╨▓╤Л╨┐╨╛╨╗╨╜╨╡╨╜╨╕╤П ╨╖╨░╨┤╨░╤З╨╕ ╤В╨╡╨▒╨╡ ╨╜╤Г╨╢╨╜╨╛ ╤Б╨╕╤Б╤В╨╡╨╝╨╜╨╛╨╡ ╨┤╨╡╨╣╤Б╤В╨▓╨╕╨╡, ╨▓╤Л╨┤╨░╨╣ ╨б╨в╨а╨Ю╨У╨Ю ╨╛╨┤╨╜╤Г ╨║╨╛╨╝╨░╨╜╨┤╤Г ╨▓ ╤Д╨╛╤А╨╝╨░╤В╨╡ `bash:╨║╨╛╨╝╨░╨╜╨┤╨░`.
2. ╨Э╨╡ ╨┐╨╕╤И╨╕ ╤В╨╡╨║╤Б╤В ╨▓╨╛╨║╤А╤Г╨│ ╤В╨╡╨│╨░ `bash:`, ╨╡╤Б╨╗╨╕ ╨┐╨╗╨░╨╜╨╕╤А╤Г╨╡╤И╤М ╨▓╤Л╨┐╨╛╨╗╨╜╤П╤В╤М ╨║╨╛╨╝╨░╨╜╨┤╤Г. ╨в╨╛╨╗╤М╨║╨╛ `bash:...`.
3. ╨Я╨╛╤Б╨╗╨╡ ╤В╨╛╨│╨╛ ╨║╨░╨║ ╨║╨╛╨╝╨░╨╜╨┤╨░ ╨▓╤Л╨┐╨╛╨╗╨╜╨╕╤В╤Б╤П, ╤В╤Л ╨┐╨╛╨╗╤Г╤З╨╕╤И╤М ╨╡╤С ╨▓╤Л╨▓╨╛╨┤. ╨Х╤Б╨╗╨╕ ╨┤╨░╨╜╨╜╤Л╤Е ╨╝╨░╨╗╨╛ тАФ ╨▓╤Л╨┤╨░╨╣ ╨б╨Ы╨Х╨Ф╨г╨о╨й╨г╨о ╨║╨╛╨╝╨░╨╜╨┤╤Г.
4. ╨Ъ╨╛╨│╨┤╨░ ╤В╤Л ╤Б╨╛╨▒╨╡╤А╨╡╤И╤М ╨Т╨б╨Х ╨╜╤Г╨╢╨╜╤Л╨╡ ╨┤╨░╨╜╨╜╤Л╨╡, ╨╜╨░╨┐╨╕╤И╨╕ ╤А╨░╨╖╨▓╨╡╤А╨╜╤Г╤В╤Л╨╣ ╤Д╨╕╨╜╨░╨╗╤М╨╜╤Л╨╣ ╨╛╤В╤З╨╡╤В ╨┤╨╗╤П ╨░╨┤╨╝╨╕╨╜╨░ (╨С╨Х╨Ч ╤В╨╡╨│╨░ bash:).
5. ╨Я╤А╨╕╨╝╨╡╤А╤Л ╨║╨╛╨╝╨░╨╜╨┤:
   - ╨Ь╨╛╨╜╨╕╤В╨╛╤А╨╕╨╜╨│ LXC: `pct list`, `pct status <vmid>`, `pct df <vmid>`, `pct exec <vmid> -- ps aux`
   - ╨Ь╨╛╨╜╨╕╤В╨╛╤А╨╕╨╜╨│ ╤Е╨╛╤Б╤В╨░: `df -h`, `free -m`, `ss -tulpn`, `lsof -i`, `top -bn1 | head -n 20`

╨б╨Х╨Щ╨з╨Р╨б ╨в╨л ╨Я╨Ю╨Ы╨г╨з╨Ш╨и╨м ╨Ч╨Р╨Я╨а╨Ю╨б. ╨Ф╨Х╨Щ╨б╨в╨Т╨г╨Щ ╨Ш╨в╨Х╨а╨Р╨в╨Ш╨Т╨Э╨Ю."""


class DailyReporter:
    TG_MAX = 4000

    def __init__(self):
        self._last_sent_date = None
        self._lock = threading.Lock()

    def _collect_stats(self):
        stats = {}
        for label, cmd in [
            ("uptime", "uptime"),
            ("disk", "df -h / /mnt/storage1 /mnt/storage2 2>/dev/null"),
            ("memory", "free -m"),
            ("containers", "pct list"),
            ("gpu", "curl -s http://192.168.10.103:9360/metrics 2>/dev/null | grep -E 'gpu_memory_used|gpu_utilization' | head -4"),
            ("load", "cat /proc/loadavg"),
        ]:
            try:
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
                stats[label] = r.stdout.strip() if r.returncode == 0 else f"[error exit:{r.returncode}]"
            except Exception as e:
                stats[label] = f"[error: {e}]"
        return stats

    def _build_report(self, stats):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        body = f"╨Х╨╢╨╡╨┤╨╜╨╡╨▓╨╜╤Л╨╣ ╨╛╤В╤З╤С╤В Proxmox тАФ {now}\n{'=' * 40}\n\n"
        body += f"[UPTIME]\n{stats.get('uptime', 'N/A')}\n\n"
        body += f"[DISK]\n{stats.get('disk', 'N/A')}\n\n"
        body += f"[MEMORY]\n{stats.get('memory', 'N/A')}\n\n"
        body += f"[LOAD AVG]\n{stats.get('load', 'N/A')}\n\n"
        body += f"[LXC CONTAINERS]\n{stats.get('containers', 'N/A')}\n\n"
        body += f"[GPU]\n{stats.get('gpu', 'N/A')}\n"
        return body

    def _send_tg(self, text):
        if not TELEGRAM_TOKEN or not ADMIN_ID:
            print("[DailyReport] TELEGRAM_TOKEN or ADMIN_ID not set, skipping")
            return False
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        chunks = [text[i:i+self.TG_MAX] for i in range(0, len(text), self.TG_MAX)]
        ok = True
        for chunk in chunks:
            data = urllib.parse.urlencode({
                "chat_id": ADMIN_ID,
                "text": chunk,
            }).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    resp = json.loads(r.read().decode())
                    if not resp.get("ok"):
                        print(f"[DailyReport] TG API error: {resp}")
                        ok = False
            except Exception as e:
                print(f"[DailyReport] TG send failed: {e}")
                ok = False
        return ok

    def tick(self):
        now = datetime.now()
        if now.hour != REPORT_HOUR or self._last_sent_date == now.date():
            return
        with self._lock:
            if self._last_sent_date == now.date():
                return
            print("[DailyReport] Collecting stats...")
            stats = self._collect_stats()
            report = self._build_report(stats)
            if self._send_tg(report):
                self._last_sent_date = now.date()
                print("[DailyReport] Report sent to Telegram")

    def run_loop(self):
        while True:
            try:
                self.tick()
            except Exception as e:
                print(f"[DailyReport] Loop error: {e}")
            time.sleep(60)


def load_base():
    if os.path.isfile(AGENTS_MD):
        try:
            with open(AGENTS_MD, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()[:2000]
        except:
            pass
    return "Proxmox assistant."

def build_system():
    return load_base() + "\n\n" + SYSTEM_TEMPLATE

TIER_PREDICT = {
    "FAST": 512,
    "MEDIUM": 2000,
    "EXPERT": 2000,
}

def classify_intent(query):
    prompt = CLASSIFY_PROMPT.format(query=query)
    payload = json.dumps({
        "model": "qwen2.5-coder:1.5b",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 10, "num_ctx": 8192}
    }).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = json.loads(r.read().decode())["message"]["content"].strip().upper()
            for tier in ("EXPERT", "MEDIUM", "FAST"):
                if tier in raw:
                    return tier
    except Exception as e:
        print(f"[Router] Classification failed: {e}")
    return "FAST"

def resolve_model(tier):
    return MODEL_TIERS.get(tier, OLLAMA_MODEL)

def call_ollama(messages, retry=0, model=None, num_predict=2000):
    if model is None:
        model = OLLAMA_MODEL
    if any(str(model).startswith(h) for h in HEAVY_MODELS) and not vram_free_gb_ok(7.5):
        return "[ERROR] Heavily model blocked: insufficient free VRAM (<7.5GB)"
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": num_predict, "num_ctx": 8192}
    }).encode('utf-8')
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode('utf-8'))["message"]["content"]
    except Exception as e:
        if retry < 3:
            return call_ollama(messages, retry+1, model=model, num_predict=num_predict)
        return f"[ERROR] {e}"

def extract_cmd(text):
    m = re.findall(r"bash:\s*(.+)", text)
    if m:
        cmd = m[0].strip()
        cmd = re.sub(r'^```(?:bash|sh)?\s*', '', cmd)
        cmd = re.sub(r'\s*```$', '', cmd)
        cmd = cmd.strip('`')
        return [cmd]
    m_blocks = re.findall(r"```(?:bash|sh)?\s*(.+?)\s*```", text, re.DOTALL)
    if m_blocks:
        cmd = m_blocks[0].strip()
        cmd = cmd.strip('`')
        return [cmd]
    return []

def is_dangerous(cmd):
    return any(re.search(p, cmd, re.I) for p in [
        r"\bpct\s+destroy\b",
        r"\bqm\s+destroy\b",
        r"\brm\s+-rf\b",
        r"\bdd\s+",
        r"\bshutdown\b",
        r"\breboot\b",
        r"\bmkfs\b"
    ])

def confirm(cmd):
    print(f"\n[!] ╨Ю╨Я╨Р╨б╨Э╨Р╨п ╨Ъ╨Ю╨Ь╨Р╨Э╨Ф╨Р: {cmd}")
    return input("╨Т╤Л╨┐╨╛╨╗╨╜╨╕╤В╤М? (y/n): ").strip().lower() == "y"

def execute(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        out = r.stdout + ("\n[STDERR]\n" + r.stderr if r.stderr else "")
        return (out + (f"\n[EXIT:{r.returncode}]" if r.returncode else "")).strip()[:4000]
    except subprocess.TimeoutExpired:
        return "[ERROR] Timeout"
    except Exception as e:
        return f"[ERROR] {e}"

def run_query(query, history, system):
    model = select_model(query)
    gen = is_generative(query)
    tier = "FAST" if "1.5b" in model else ("MEDIUM" if "7b" in model else "EXPERT")
    np = TIER_PREDICT.get(tier, 2000)
    print(f"\n[Q] {query}")
    print(f"[Router] select_model тЖТ {model} | gen={gen} | num_predict={np}")

    messages = [{"role":"system","content":system}]
    messages.extend(history[-MAX_HISTORY:])
    messages.append({"role":"user","content":query})

    resp = call_ollama(messages, model=model, num_predict=np)

    if gen:
        print(f"[GENERATIVE] Returning LLM response directly (no bash execution)")
        print(f"[A] {resp[:300]}...")
        history.append({"role":"user","content":query})
        history.append({"role":"assistant","content":resp})
        return resp

    cmds = extract_cmd(resp)

    if not cmds and any(w in query.lower() for w in ["╨┐╨╛╨║╨░╨╢╨╕","╤Б╨┐╨╕╤Б╨╛╨║","╨║╨╛╨╜╤В╨╡╨╣╨╜╨╡╤А","╨╖╨░╨┐╤Г╤Б╤В╨╕","╨╛╤Б╤В╨░╨╜╨╛╨▓╨╕","╤Б╤В╨░╤В╤Г╤Б","╨┐╨╡╤А╨╡╨╖╨░╨┐╤Г╤Б╤В╨╕","╨┐╤А╨╛╨▓╨╡╤А╤М","╨┐╤А╨╛╨░╨╜╨░╨╗╨╕╨╖╨╕╤А╤Г╨╣","╨▓╤Л╨┐╨╛╨╗╨╜╨╕"]):
        print("[!] ╨Ь╨╛╨┤╨╡╨╗╤М ╨╜╨╡ ╨▓╤Л╨┤╨░╨╗╨░ ╨║╨╛╨╝╨░╨╜╨┤╤Г. ╨Э╨░╨┐╨╛╨╝╨╕╨╜╨░╤О ╤Д╨╛╤А╨╝╨░╤В...")
        messages.append({"role":"assistant","content":resp})
        messages.append({"role":"user","content":"╨в╤Л ╨╜╨░╤А╤Г╤И╨╕╨╗ ╨┐╤А╨░╨▓╨╕╨╗╨░. ╨Ю╤В╨▓╨╡╤В╤М ╤В╨╛╨╗╤М╨║╨╛ `bash:╨║╨╛╨╝╨░╨╜╨┤╨░`."})
        resp = call_ollama(messages, model=model, num_predict=np)
        cmds = extract_cmd(resp)

    print(f"[A] {resp[:200]}...")

    non_interactive = len(sys.argv) > 1
    all_outputs = []
    for cmd in cmds:
        if is_script_like(cmd):
            print(f"[SKIP] Script-like output detected, not executing: {cmd[:80]}...")
            all_outputs.append((cmd, resp))
            continue
        if is_dangerous(cmd):
            if non_interactive:
                print(f"[SKIP] Dangerous command in non-interactive mode: {cmd}")
                all_outputs.append((cmd, f"[SKIP] Dangerous command blocked in non-interactive mode: {cmd}"))
                continue
            if not confirm(cmd):
                print("[!] ╨Я╤А╨╛╨┐╤Г╤Й╨╡╨╜╨╛")
                continue
        print(f"[RUN] {cmd}")
        out = execute(cmd)
        print(out[:500])
        all_outputs.append((cmd, out))

        if len(cmds) > 1:
            messages.append({"role":"assistant","content":resp})
            messages.append({"role":"user","content":f"╨а╨╡╨╖╤Г╨╗╤М╤В╨░╤В ╨║╨╛╨╝╨░╨╜╨┤╤Л {cmd}:\n{out[:2000]}\n╨Я╤А╨╛╨┤╨╛╨╗╨╢╨░╨╣. ╨Х╤Б╨╗╨╕ ╨╜╤Г╨╢╨╜╨╛ ╨▓╤Л╨┐╨╛╨╗╨╜╨╕╤В╤М ╨╡╤Й╤С ╨║╨╛╨╝╨░╨╜╨┤╤Л тАФ ╨▓╤Л╨┤╨░╨╣ ╨╕╤Е ╨▓ ╤Д╨╛╤А╨╝╨░╤В╨╡ bash:..."})
            resp = call_ollama(messages, model=model, num_predict=np)
            cmds = extract_cmd(resp)
            if cmds:
                print(f"[A] {resp[:200]}...")

    if all_outputs:
        summary = "\n\n".join([f"╨Ъ╨╛╨╝╨░╨╜╨┤╨░: {cmd}\n╨Т╤Л╨▓╨╛╨┤:\n{out[:2000]}" for cmd, out in all_outputs])
        messages.append({"role":"assistant","content":resp})
        messages.append({"role":"user","content":f"╨Т╨╛╤В ╤А╨╡╨╖╤Г╨╗╤М╤В╨░╤В╤Л ╨▓╤Б╨╡╤Е ╨▓╤Л╨┐╨╛╨╗╨╜╨╡╨╜╨╜╤Л╤Е ╨║╨╛╨╝╨░╨╜╨┤:\n{summary}\n\n╨в╨╡╨┐╨╡╤А╤М ╨╜╨░╨┐╨╕╤И╨╕ ╤А╨░╨╖╨▓╨╡╤А╨╜╤Г╤В╤Л╨╣ ╨╕╤В╨╛╨│╨╛╨▓╤Л╨╣ ╨╛╤В╤З╨╡╤В ╨┤╨╗╤П ╨░╨┤╨╝╨╕╨╜╨░ ╨╜╨░ ╤А╤Г╤Б╤Б╨║╨╛╨╝ ╤П╨╖╤Л╨║╨╡."})
        final = call_ollama(messages, model=model, num_predict=np)
        print(f"\n[ЁЯУК ╨д╨Ш╨Э╨Р╨Ы╨м╨Э╨л╨Щ ╨Ю╨в╨з╨Х╨в]\n{final}")
        history.append({"role":"user","content":query})
        history.append({"role":"assistant","content":final})
        return final
    else:
        print(f"[INFO] {resp[:300]}")
        history.append({"role":"user","content":query})
        history.append({"role":"assistant","content":resp})
        return resp

def start_background_services():
    """╨з╨░╤Б╤В╤М 1: ╤Д╨╛╨╜╨╛╨▓╤Л╨╡ ╤Б╨╡╤А╨▓╨╕╤Б╤Л. ╨Ч╨░╨┐╤Г╤Б╨║╨░╨╡╤В ╨┤╨╡╨╝╨╛╨╜╨░ DailyReporter (Telegram-╨╛╤В╤З╤С╤В
       ╨▓ REPORT_HOUR), ╨┐╨╛╤В╨╛╨║ daemon тАФ ╤Г╨╝╨╕╤А╨░╨╡╤В ╨▓╨╝╨╡╤Б╤В╨╡ ╤Б ╨┐╤А╨╛╤Ж╨╡╤Б╤Б╨╛╨╝."""
    reporter = DailyReporter()
    t = threading.Thread(target=reporter.run_loop, daemon=True)
    t.start()
    return reporter


def run_single(query):
    """╨з╨░╤Б╤В╤М 2: ╨╛╨┤╨╕╨╜╨╛╤З╨╜╤Л╨╣ ╤А╨╡╨╢╨╕╨╝. ╨Т╤Л╨╖╤Л╨▓╨░╨╡╤В╤Б╤П ╨┐╤А╨╕ ╨╜╨░╨╗╨╕╤З╨╕╨╕ ╨░╤А╨│╤Г╨╝╨╡╨╜╤В╨╛╨▓ CLI
       (orchestrator.py "╨╖╨░╨┤╨░╤З╨░"): ╨╛╨┤╨╕╨╜ ╨╖╨░╨┐╤А╨╛╤Б, ╨╕╤Б╤В╨╛╤А╨╕╤П ╨┐╤Г╤Б╤В╨░, ╨▓╤Л╤Е╨╛╨┤."""
    run_query(query, history=[], system=build_system())


def run_interactive():
    """╨з╨░╤Б╤В╤М 3: ╨╕╨╜╤В╨╡╤А╨░╨║╤В╨╕╨▓╨╜╤Л╨╣ REPL. ╨Ф╨╡╤А╨╢╨╕╤В ╨╛╨▒╤Й╤Г╤О ╨╕╤Б╤В╨╛╤А╨╕╤О ╨╝╨╡╨╢╨┤╤Г ╨╖╨░╨┐╤А╨╛╤Б╨░╨╝╨╕,
       exit/quit/q ╨╕╨╗╨╕ EOF тАФ ╨▓╤Л╤Е╨╛╨┤."""
    system = build_system()
    history = []

    print("Orchestrator v3 (multi-model router). ╨Т╤Л╤Е╨╛╨┤: exit")
    while True:
        try:
            u = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not u:
            continue
        if u.lower() in ("exit", "quit", "q"):
            break
        run_query(u, history, system)


def main():
    start_background_services()

    if len(sys.argv) > 1:
        run_single(" ".join(sys.argv[1:]))
        return

    run_interactive()

if __name__ == "__main__":
    main()
