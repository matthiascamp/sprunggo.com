#!/usr/bin/env python3
"""Check downloaded originals and local HTML/CSS asset references."""
import hashlib, json, re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote
ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
m = json.loads((ROOT / 'mirror-manifest.json').read_text())
missing = set()
checked = set()

def check(value, source):
    value = unescape(value.strip())
    if not value or value.startswith(('data:', '#', 'blob:')): return
    url = urljoin('http://local/' + source, value)
    u = urlsplit(url)
    if u.netloc != 'local': return
    p = SITE / unquote(u.path).lstrip('/')
    if u.path.endswith('/'): p /= 'index.html'
    checked.add(str(p.relative_to(SITE)))
    if not p.is_file(): missing.add(str(p.relative_to(SITE)))

class Assets(HTMLParser):
    def __init__(self, source): super().__init__(); self.source = source
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for attr in ('src','poster','data-src','data-lazy-src'):
            if a.get(attr): check(a[attr], self.source)
        if tag == 'link' and a.get('rel') in ('stylesheet','icon','preload','shortcut icon'):
            check(a.get('href',''), self.source)
        for part in a.get('srcset','').split(','):
            if part.strip(): check(part.strip().split()[0], self.source)

for p in SITE.rglob('*'):
    if p.suffix not in ('.html','.css'): continue
    source = str(p.relative_to(SITE))
    s = p.read_text()
    if p.suffix == '.html': Assets(source).feed(s)
    for value in re.findall(r'url\(\s*[\"\']?([^\)\"\']+)',s): check(value, source)
for url, record in m['files'].items():
    p = ROOT / 'original' / record['path']
    assert p.stat().st_size == record['bytes'], p
    assert (SITE / record['path']).is_file(), record['path']
    record['sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
(ROOT/'mirror-manifest.json').write_text(json.dumps(m,indent=2))
report = {'downloaded_urls':len(m['files']), 'downloaded_bytes':sum(r['bytes'] for r in m['files'].values()), 'local_asset_paths_checked':len(checked), 'missing_local_assets': sorted(missing), 'upstream_failures':m['failures'], 'visual_verification':'Not performed: in-app browser execution tool unavailable.'}
(ROOT/'verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
