	LANG = "en_US.UTF-8"
    are supported and installed on your system.
#!/usr/bin/env python3
"""Sync changed Obsidian notes to Dify dataset."""
import hashlib, json, os, urllib.request, urllib.error, glob

ROOT = os.environ.get('OBSIDIAN_ROOT', '/mnt/obsidian')
STATE = '/home/node/.n8n/obsidian_sync_state.json'
FOLDERS = ['01-Infrastructure','02-Security','03-Knowledge','03-Runbooks','04-Portfolio','05-Job']
DIFY_BASE = os.environ.get('DIFY_BASE_URL', 'http://192.168.10.112:3002')
DATASET_ID = os.environ.get('DIFY_DATASET_ID', '')
API_KEY = os.environ.get('DIFY_DATASET_API_KEY', '')

def scan():
    try:
        with open(STATE) as f: state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    changed = []
    for folder in FOLDERS:
        base = os.path.join(ROOT, folder)
        if not os.path.isdir(base): continue
        for dirpath, _, files in os.walk(base):
            for fn in files:
                if not fn.endswith('.md'): continue
                p = os.path.join(dirpath, fn)
                try:
                    with open(p, encoding='utf-8') as f: content = f.read()
                except Exception: continue
                h = hashlib.sha256(content.encode()).hexdigest()
                if state.get(p) != h:
                    changed.append((p, content))
                state[p] = h
    try:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        with open(STATE, 'w') as f: json.dump(state, f)
    except Exception: pass
    return changed

def upload(name, text):
    if not DATASET_ID or not API_KEY: return False
    url = f"{DIFY_BASE}/v1/datasets/{DATASET_ID}/document/create-by-text"
    data = json.dumps({'name': name, 'text': text, 'indexing_technique': 'high_quality', 'process_rule': {'mode': 'automatic'}}).encode()
    req = urllib.request.Request(url, data=data, headers={'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status == 200
    except Exception as e:
        print(f"Upload failed for {name}: {e}")
        return False

def main():
    changed = scan()
    print(f"Found {len(changed)} changed files")
    ok = 0
    for p, content in changed:
        name = os.path.relpath(p, ROOT)
        if upload(name, content):
            ok += 1
            print(f"  Uploaded: {name}")
        else:
            print(f"  Failed: {name}")
    print(f"Synced {ok}/{len(changed)}")

if __name__ == '__main__':
    main()
