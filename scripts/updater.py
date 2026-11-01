#!/usr/bin/env python3
import sys
import os
import json
import subprocess
import urllib.request
import urllib.error

OLLAMA_URL = "http://192.168.10.103:11434/api/chat"
DEFAULT_MODEL = "qwen2.5-coder:14b"
TARGET_SCRIPT = "/root/proxmox-local/orchestrator.py"
TEMP_SCRIPT = "/root/proxmox-local/orchestrator_temp.py"
BACKUP_SCRIPT = "/root/proxmox-local/orchestrator.py.bak"

SYSTEM_INSTRUCTION = """╨в╤Л тАФ ╨▓╨╡╨┤╤Г╤Й╨╕╨╣ ╤Б╨╕╤Б╤В╨╡╨╝╨╜╤Л╨╣ ╨┐╤А╨╛╨│╤А╨░╨╝╨╝╨╕╤Б╤В ╨╕ DevOps-╨╕╨╜╨╢╨╡╨╜╨╡╤А.
╨в╨▓╨╛╤П ╨╡╨┤╨╕╨╜╤Б╤В╨▓╨╡╨╜╨╜╨░╤П ╨╖╨░╨┤╨░╤З╨░ тАФ ╨╝╨╛╨┤╨╕╤Д╨╕╤Ж╨╕╤А╨╛╨▓╨░╤В╤М ╨┐╤А╨╡╨┤╨╛╤Б╤В╨░╨▓╨╗╨╡╨╜╨╜╤Л╨╣ Python-╤Б╨║╤А╨╕╨┐╤В orchestrator.py ╤Б╨╛╨│╨╗╨░╤Б╨╜╨╛ ╨╖╨░╨┐╤А╨╛╤Б╤Г ╨┐╨╛╨╗╤М╨╖╨╛╨▓╨░╤В╨╡╨╗╤П.

╨Я╨а╨Р╨Т╨Ш╨Ы╨Р:
1. ╨Т╤Л╨┤╨░╨▓╨░╨╣ ╨б╨в╨а╨Ю╨У╨Ю ╤З╨╕╤Б╤В╤Л╨╣ ╤А╨░╨▒╨╛╤З╨╕╨╣ ╨║╨╛╨┤ Python.
2. ╨Э╨╡ ╨┐╨╕╤И╨╕ ╨╜╨╕╨║╨░╨║╨╕╤Е ╨┐╨╛╤П╤Б╨╜╨╡╨╜╨╕╨╣ ╨╜╨░ ╤А╤Г╤Б╤Б╨║╨╛╨╝ ╤П╨╖╤Л╨║╨╡, ╨┐╤А╨╕╨▓╨╡╤В╤Б╤В╨▓╨╕╨╣ ╨╕╨╗╨╕ markdown-╤А╨░╨╖╨╝╨╡╤В╨║╨╕ (╨Э╨Х ╨╕╤Б╨┐╨╛╨╗╤М╨╖╤Г╨╣ ```python ╨╕╨╗╨╕ ```). ╨Ъ╨╛╨┤ ╨┤╨╛╨╗╨╢╨╡╨╜ ╨╜╨░╤З╨╕╨╜╨░╤В╤М╤Б╤П ╨┐╤А╤П╨╝╨╛ ╤Б '#!/usr/bin/env python3'.
3. ╨б╨╛╤Е╤А╨░╨╜╤П╨╣ ╨▓╤Б╤О ╤Б╤Г╤Й╨╡╤Б╤В╨▓╤Г╤О╤Й╤Г╤О ╨╗╨╛╨│╨╕╨║╤Г, ╨║╨╛╤В╨╛╤А╨░╤П ╨╜╨╡ ╨╛╤В╨╜╨╛╤Б╨╕╤В╤Б╤П ╨║ ╨╕╨╖╨╝╨╡╨╜╨╡╨╜╨╕╤П╨╝ (╨┐╨╛╨┤╨║╨╗╤О╤З╨╡╨╜╨╕╨╡ ╨║ Ollama, ╨╛╨▒╤А╨░╨▒╨╛╤В╨║╤Г ╨╛╤И╨╕╨▒╨╛╨║, ╨╕╨╜╤В╨╡╤А╨░╨║╤В╨╕╨▓╨╜╤Л╨╣ ╤А╨╡╨╢╨╕╨╝, ╤В╨░╨╣╨╝╨░╤Г╤В╤Л).
4. ╨в╨▓╨╛╨╣ ╨║╨╛╨┤ ╨┤╨╛╨╗╨╢╨╡╨╜ ╨▒╤Л╤В╤М ╤Б╨╕╨╜╤В╨░╨║╤Б╨╕╤З╨╡╤Б╨║╨╕ ╨╕╨┤╨╡╨░╨╗╤М╨╜╤Л╨╝ ╨┤╨╗╤П Python 3.11+.
"""

def call_ollama(model, prompt, current_code):
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": f"╨Т╨╛╤В ╤В╨╡╨║╤Г╤Й╨╕╨╣ ╨║╨╛╨┤ ╤Б╨║╤А╨╕╨┐╤В╨░:\n\n{current_code}\n\n╨Т╤Л╨┐╨╛╨╗╨╜╨╕ ╨╖╨░╨┤╨░╤З╤Г: {prompt}\n╨Т╨╡╤А╨╜╨╕ ╤В╨╛╨╗╤М╨║╨╛ ╨╛╨▒╨╜╨╛╨▓╨╗╨╡╨╜╨╜╤Л╨╣ ╨║╨╛╨┤ ╤Б╨║╤А╨╕╨┐╤В╨░ ╤Ж╨╡╨╗╨╕╨║╨╛╨╝."}
    ]
    
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 3000
        }
    }).encode('utf-8')
    
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode('utf-8'))["message"]["content"]
    except Exception as e:
        print(f"тЭМ ╨Ю╤И╨╕╨▒╨║╨░ ╨┐╨╛╨┤╨║╨╗╤О╤З╨╡╨╜╨╕╤П ╨║ Ollama: {e}")
        sys.exit(1)

def clean_code(response_text):
    lines = response_text.split('\n')
    cleaned = []
    for line in lines:
        if line.strip().startswith('```'):
            continue
        cleaned.append(line)
    return '\n'.join(cleaned).strip()

def main():
    if len(sys.argv) < 2:
        print("ЁЯдЦ ╨Ш╨Ш-╨Ф╨╡╨┐╨╗╨╛╨╣╨╡╤А ╨░╨║╤В╨╕╨▓╨╡╨╜.")
        print("╨Ш╤Б╨┐╨╛╨╗╤М╨╖╨╛╨▓╨░╨╜╨╕╨╡: python3 updater.py [--model <╨╕╨╝╤П>] \"╨╛╨┐╨╕╤Б╨░╨╜╨╕╨╡ ╨╕╨╖╨╝╨╡╨╜╨╡╨╜╨╕╨╣ ╨╜╨░ ╤А╤Г╤Б╤Б╨║╨╛╨╝\"")
        print("╨Я╤А╨╕╨╝╨╡╤А: python3 updater.py \"╨┤╨╛╨▒╨░╨▓╤М ╨╖╨░╨┐╨╕╤Б╤М ╨╗╨╛╨│╨╛╨▓ ╨▓╤Б╨╡╤Е ╨▓╤Л╨┐╨╛╨╗╨╜╨╡╨╜╨╜╤Л╤Е ╨║╨╛╨╝╨░╨╜╨┤ ╨▓ /var/log/orchestrator.log\"")
        sys.exit(0)

    args = sys.argv[1:]
    model = DEFAULT_MODEL

    if "--model" in args:
        try:
            m_idx = args.index("--model")
            model = args[m_idx + 1]
            args.pop(m_idx + 1)
            args.pop(m_idx)
        except IndexError:
            print("тЭМ ╨Ю╤И╨╕╨▒╨║╨░: ╨╜╨╡ ╤Г╨║╨░╨╖╨░╨╜╨░ ╨╝╨╛╨┤╨╡╨╗╤М ╨┐╨╛╤Б╨╗╨╡ ╤Д╨╗╨░╨│╨░ --model")
            sys.exit(1)

    task = " ".join(args)

    if not os.path.exists(TARGET_SCRIPT):
        print(f"тЭМ ╨ж╨╡╨╗╨╡╨▓╨╛╨╣ ╤Б╨║╤А╨╕╨┐╤В ╨╜╨╡ ╨╜╨░╨╣╨┤╨╡╨╜ ╨┐╨╛ ╨┐╤Г╤В╨╕: {TARGET_SCRIPT}")
        sys.exit(1)

    print(f"ЁЯУЦ ╨з╨╕╤В╨░╨╡╨╝ ╤В╨╡╨║╤Г╤Й╨╕╨╣ ╨║╨╛╨┤ {TARGET_SCRIPT}...")
    with open(TARGET_SCRIPT, "r", encoding="utf-8") as f:
        current_code = f.read()

    print(f"ЁЯза ╨Ю╤В╨┐╤А╨░╨▓╨╗╤П╨╡╨╝ ╨╖╨░╨┤╨░╤З╤Г ╨▓ Ollama ({model}). ╨Я╨╛╨╢╨░╨╗╤Г╨╣╤Б╤В╨░, ╨┐╨╛╨┤╨╛╨╢╨┤╨╕╤В╨╡...")
    raw_response = call_ollama(model, task, current_code)
    new_code = clean_code(raw_response)

    if not new_code.startswith("#!"):
        print("тЭМ ╨Ю╤И╨╕╨▒╨║╨░: ╨Ш╨Ш ╨▓╨╡╤А╨╜╤Г╨╗ ╨╜╨╡╨║╨╛╤А╤А╨╡╨║╤В╨╜╤Л╨╣ ╤Д╨╛╤А╨╝╨░╤В (╨║╨╛╨┤ ╨┤╨╛╨╗╨╢╨╡╨╜ ╨╜╨░╤З╨╕╨╜╨░╤В╤М╤Б╤П ╤Б shebang-╤Б╤В╤А╨╛╨║╨╕). ╨Я╨╛╨┐╤А╨╛╨▒╤Г╨╣╤В╨╡ ╨╡╤Й╨╡ ╤А╨░╨╖.")
        sys.exit(1)

    print(f"ЁЯТ╛ ╨Ч╨░╨┐╨╕╤Б╤Л╨▓╨░╨╡╨╝ ╨▓╤А╨╡╨╝╨╡╨╜╨╜╤Г╤О ╨▓╨╡╤А╤Б╨╕╤О ╨▓ {TEMP_SCRIPT}...")
    with open(TEMP_SCRIPT, "w", encoding="utf-8") as f:
        f.write(new_code)

    print("ЁЯФм ╨Я╤А╨╛╨▓╨╡╤А╤П╨╡╨╝ ╤Б╨╕╨╜╤В╨░╨║╤Б╨╕╤Б ╨┐╨╛╨╗╤Г╤З╨╡╨╜╨╜╨╛╨│╨╛ ╨║╨╛╨┤╨░ ╨╜╨░ ╨╛╤И╨╕╨▒╨║╨╕...")
    test_compile = subprocess.run(
        [sys.executable, "-m", "py_compile", TEMP_SCRIPT],
        capture_output=True,
        text=True
    )

    if test_compile.returncode != 0:
        print("\nЁЯТе ╨б╨Ш╨Э╨в╨Р╨Ъ╨б╨Ш╨з╨Х╨б╨Ъ╨Р╨п ╨Ю╨и╨Ш╨С╨Ъ╨Р ╨Т ╨б╨У╨Х╨Э╨Х╨а╨Ш╨а╨Ю╨Т╨Р╨Э╨Э╨Ю╨Ь ╨Ъ╨Ю╨Ф╨Х!")
        print("╨Ю╨▒╨╜╨╛╨▓╨╗╨╡╨╜╨╕╨╡ ╨╛╤В╨║╨╗╨╛╨╜╨╡╨╜╨╛ ╤А╨░╨┤╨╕ ╨▒╨╡╨╖╨╛╨┐╨░╤Б╨╜╨╛╤Б╤В╨╕ ╨▓╨░╤И╨╡╨╣ ╤Б╨╕╤Б╤В╨╡╨╝╤Л.")
        print("╨Ю╤И╨╕╨▒╨║╨░ ╨║╨╛╨╝╨┐╨╕╨╗╤П╤В╨╛╤А╨░:")
        print(test_compile.stderr)
        if os.path.exists(TEMP_SCRIPT):
            os.remove(TEMP_SCRIPT)
        sys.exit(1)

    print("тЬЕ ╨Ъ╨╛╨┤ ╤Г╤Б╨┐╨╡╤И╨╜╨╛ ╨┐╤А╨╛╤И╨╡╨╗ ╤Б╨╕╨╜╤В╨░╨║╤Б╨╕╤З╨╡╤Б╨║╨╕╨╣ ╨║╨╛╨╜╤В╤А╨╛╨╗╤М (0 ╨╛╤И╨╕╨▒╨╛╨║).")

    print(f"ЁЯУж ╨б╨╛╨╖╨┤╨░╨╡╨╝ ╤А╨╡╨╖╨╡╤А╨▓╨╜╤Г╤О ╨║╨╛╨┐╨╕╤О ╨┐╤А╨╡╨╢╨╜╨╡╨╣ ╨▓╨╡╤А╤Б╨╕╨╕: {BACKUP_SCRIPT}")
    if os.path.exists(TARGET_SCRIPT):
        if os.path.exists(BACKUP_SCRIPT):
            os.remove(BACKUP_SCRIPT)
        os.rename(TARGET_SCRIPT, BACKUP_SCRIPT)

    os.rename(TEMP_SCRIPT, TARGET_SCRIPT)
    os.chmod(TARGET_SCRIPT, 0o755)

    print("\nЁЯОЙ ╨Ю╨С╨Э╨Ю╨Т╨Ы╨Х╨Э╨Ш╨Х ╨Ч╨Р╨Т╨Х╨а╨и╨Х╨Э╨Ю ╨г╨б╨Я╨Х╨и╨Э╨Ю! ╨б╨║╤А╨╕╨┐╤В orchestrator.py ╨│╨╛╤В╨╛╨▓ ╨║ ╤А╨░╨▒╨╛╤В╨╡ ╨▓ ╨╜╨╛╨▓╨╛╨╣ ╨║╨╛╨╜╤Д╨╕╨│╤Г╤А╨░╤Ж╨╕╨╕.")

if __name__ == "__main__":
    main()
