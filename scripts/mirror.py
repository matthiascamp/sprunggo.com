#!/usr/bin/env python3
"""Download public website dependencies and produce a locally linked static copy."""
import concurrent.futures, hashlib, html, json, os, re, subprocess
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urldefrag, unquote
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://sprung-go.com.au/'
ORIGINAL = ROOT / 'original'
SITE = ROOT / 'site'
records, failures, seen = {}, {}, set()
cache_file = ROOT / 'mirror-manifest.json'
cache = json.loads(cache_file.read_text())['files'] if cache_file.exists() else {}
asset_ext = re.compile(r'\.(?:css|js|png|jpe?g|gif|svg|webp|avif|ico|woff2?|ttf|otf|eot|mp4|webm|pdf|json)(?:\?|$)', re.I)


def clean(url, base):
    return urldefrag(urljoin(base, html.unescape(url).replace('\\/', '/')))[0]


def path_for(url):
    u = urlsplit(url)
    p = unquote(u.path).lstrip('/')
    if u.hostname == 'fonts.googleapis.com':
        p += '.css'
    if not p or p.endswith('/'):
        p += 'index.html'
    elif not Path(p).suffix:
        p += '/index.html'
    if u.hostname not in ('sprung-go.com.au', 'www.sprung-go.com.au'):
        p = '_external/' + u.netloc + '/' + p
        if u.query:
            f = Path(p)
            p = str(f.with_name(f.stem + '-' + hashlib.sha256(u.query.encode()).hexdigest()[:10] + f.suffix))
    if '..' in Path(p).parts:
        raise ValueError(url)
    return p


class Links(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base, self.urls = base, set()
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for key in ('src', 'poster', 'data-src', 'data-lazy-src'):
            if a.get(key): self.urls.add(clean(a[key], self.base))
        if a.get('srcset'):
            for item in a['srcset'].split(','):
                if item.strip(): self.urls.add(clean(item.strip().split()[0], self.base))
        if a.get('href') and (tag == 'a' or (tag == 'link' and a.get('rel') in ('stylesheet','icon','preload','shortcut icon'))):
            self.urls.add(clean(a['href'], self.base))


def discover(s, url, kind):
    urls = set()
    if 'html' in kind:
        parser = Links(url)
        parser.feed(s)
        urls |= parser.urls
    if 'css' in kind or 'html' in kind:
        for x in re.findall(r'url\(\s*[\"\']?([^\)\"\']+)', s): urls.add(clean(x.strip(), url))
        for x in re.findall(r'@import\s+[\"\']([^\"\']+)', s): urls.add(clean(x, url))
    normalized = html.unescape(s).replace('\\/', '/')
    for x in re.findall(r'https?://[^\s<>\"\'\\)]+', normalized):
        if asset_ext.search(x): urls.add(clean(x, url))
    if 'xml' in kind:
        for x in re.findall(r'<loc>(.*?)</loc>', s): urls.add(clean(x, url))
    result = set()
    for x in urls:
        u = urlsplit(x)
        if u.scheme not in ('http', 'https'): continue
        own = u.hostname in ('sprung-go.com.au','www.sprung-go.com.au')
        if own and not any(v in u.path for v in ('wp-admin', 'wp-login', 'xmlrpc.php', '/feed', '/wp-json')):
            result.add(x)
        elif u.hostname in ('fonts.googleapis.com','fonts.gstatic.com'):
            result.add(x)
    return result


def fetch(url):
    p = ORIGINAL / path_for(url)
    p.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.CompletedProcess([], 0, cache[url]['content_type'], '') if url in cache and p.exists() else subprocess.run(['curl','-fL','--retry','2','--connect-timeout','15','--max-time','180','-sS','-A','Mozilla/5.0','-w','%{content_type}',url,'-o',str(p)], capture_output=True, text=True)
    if result.returncode:
        return url, None, result.stderr.strip()
    kind = result.stdout
    rec = {'path': str(p.relative_to(ORIGINAL)), 'content_type': kind, 'bytes': p.stat().st_size}
    deps = set()
    if any(t in kind for t in ('html','css','javascript','json','xml')):
        s = p.read_text(errors='replace')
        deps = discover(s, url, kind)
        # Elementor loads these modules at runtime from a webpack name map.
        if 'webpack' in url and 'runtime' in url:
            for name in re.findall(r'[\"\']([\w.-]+\.js)[\"\']', s):
                deps.add(urljoin(url, name))
            for name in re.findall(r'\d+:[\"\']([^\"\']+)[\"\']', s):
                if re.fullmatch(r'[\w.-]+', name):
                    deps.add(urljoin(url, name + '.min.js'))
    return url, (rec, deps), None


pending = {BASE, BASE+'wp-sitemap.xml'}
while pending:
    batch = sorted(pending - seen)
    pending = set()
    if not batch: break
    seen.update(batch)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for url, result, error in pool.map(fetch, batch):
            if error:
                failures[url] = error
                print('FAILED', url, error, flush=True)
            else:
                rec, deps = result
                records[url] = rec
                pending |= deps - seen
                print('SAVED', rec['path'], rec['bytes'], flush=True)

# Replace known references while retaining all other original markup and code.
replacements = {}
for url, rec in records.items():
    local = '/' + rec['path']
    if local.endswith('/index.html'): local = local[:-10]
    for variant in (url, html.escape(url, quote=False), url.replace('&','&#038;')):
        replacements[variant] = local
        replacements[variant.replace('/', '\\/')] = local.replace('/', '\\/')
# Dynamic Elementor module paths must resolve to the mirrored asset directories.
for prefix in ('https://sprung-go.com.au/wp-content/', 'https://sprung-go.com.au/wp-includes/'):
    replacements[prefix] = '/' + prefix.split('.au/',1)[1]
    replacements[prefix.replace('/', '\\/')] = replacements[prefix].replace('/', '\\/')
pattern = re.compile('|'.join(re.escape(k) for k in sorted(replacements, key=len, reverse=True)))
for rec in records.values():
    src, dst = ORIGINAL / rec['path'], SITE / rec['path']
    dst.parent.mkdir(parents=True, exist_ok=True)
    if any(t in rec['content_type'] for t in ('html','css','javascript','json','xml')):
        s = src.read_text(errors='replace')
        # Relative CSS urls already point to mirrored sibling assets.
        dst.write_text(pattern.sub(lambda m: replacements[m.group()], s))
    else:
        if dst.exists(): dst.unlink()
        os.link(src, dst)
(ROOT/'mirror-manifest.json').write_text(json.dumps({'source':BASE,'files':records,'failures':failures},indent=2))
print('COMPLETE',len(records),'downloaded;',len(failures),'failed',flush=True)
