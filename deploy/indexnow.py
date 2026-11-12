#!/usr/bin/env python3
"""Foro IA al Dia - notifica a IndexNow las URLs nuevas o modificadas del sitemap."""
import json
import re
import sys
import urllib.request
from pathlib import Path

KEY = '9f1c56118e1b49d8a5669ba8cc9bd801'
HOST = 'foroiaaldia.com'
BASE = 'https://' + HOST
STATE = Path('/var/lib/foroia-indexnow/sent.json')
UA = {'User-Agent': 'foroia-indexnow/1.0'}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read().decode()


def entries(xml):
    for block in re.findall(r'<(?:url|sitemap)>(.*?)</(?:url|sitemap)>', xml, re.S):
        loc = re.search(r'<loc>\s*(.*?)\s*</loc>', block)
        mod = re.search(r'<lastmod>\s*(.*?)\s*</lastmod>', block)
        if loc:
            yield loc.group(1), mod.group(1) if mod else ''


def main():
    if get(f'{BASE}/{KEY}.txt').strip() != KEY:
        sys.exit('key file not served')
    current = {}
    for sitemap, _ in entries(get(BASE + '/sitemap.xml')):
        current.update(entries(get(sitemap)))
    sent = json.loads(STATE.read_text()) if STATE.exists() else {}
    changed = [u for u, m in current.items() if sent.get(u) != m and u.startswith(BASE)]
    if not changed:
        print('indexnow: nothing new')
        return
    body = json.dumps({'host': HOST, 'key': KEY, 'keyLocation': f'{BASE}/{KEY}.txt',
                       'urlList': changed[:10000]}).encode()
    req = urllib.request.Request('https://api.indexnow.org/indexnow', data=body, method='POST',
                                 headers={**UA, 'Content-Type': 'application/json; charset=utf-8'})
    with urllib.request.urlopen(req, timeout=30) as r:
        status = r.status
    if status not in (200, 202):
        sys.exit(f'indexnow status {status}')
    sent.update({u: current[u] for u in changed})
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(sent, indent=0))
    print(f'indexnow: {len(changed)} urls -> {status}')


if __name__ == '__main__':
    main()
