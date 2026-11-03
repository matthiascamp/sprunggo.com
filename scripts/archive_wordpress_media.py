"""Archive the publicly listed WordPress media originals into the static site."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
UPLOADS = (ROOT / "site" / "wp-content" / "uploads").resolve()
API = "https://sprung-go.com.au/wp-json/wp/v2/media?per_page=100&page={}"


def get(url):
    with urlopen(Request(url, headers={"User-Agent": "SprungGoMediaArchive/1.0"}), timeout=30) as response:
        return response.read()


def archive(item):
    url = item["source_url"]
    parsed = urlparse(url)
    prefix = "/wp-content/uploads/"
    if parsed.hostname != "sprung-go.com.au" or not parsed.path.startswith(prefix):
        return {"id": item["id"], "url": url, "error": "Unexpected media URL"}
    path = (UPLOADS / parsed.path.removeprefix(prefix)).resolve()
    if not path.is_relative_to(UPLOADS):
        return {"id": item["id"], "url": url, "error": "Path outside uploads"}
    try:
        if path.exists():
            body = path.read_bytes()
        else:
            body = get(url)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        return {
            "id": item["id"], "url": url,
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
        }
    except Exception as exc:
        return {"id": item["id"], "url": url, "error": str(exc)}


def main():
    items = []
    page = 1
    while True:
        try:
            batch = json.loads(get(API.format(page)))
        except Exception as exc:
            if page == 1:
                raise
            print(f"Stopped at page {page}: {exc}")
            break
        if not batch:
            break
        items.extend(batch)
        page += 1
    by_id = {item["id"]: item for item in items}
    with ThreadPoolExecutor(max_workers=8) as executor:
        records = list(executor.map(archive, by_id.values()))
    records.sort(key=lambda record: record["id"])
    (ROOT / "wordpress-public-media.json").write_text(
        json.dumps({"api": API.format(1), "items": records}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Public media items: {len(records)}")
    print(f"Archived: {sum('path' in r for r in records)}")
    for record in records:
        if "error" in record:
            print(f"FAILED {record['url']}: {record['error']}")


if __name__ == "__main__":
    main()
