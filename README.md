# Sprung Go local copy

Downloaded from https://sprung-go.com.au/ on 2 November 2026 (Australia/Brisbane).

## Open the copy

Double-click `Start.command`, or run from this folder:

```sh
python3 -m http.server 8000 --bind 127.0.0.1 --directory site
```

Then open http://127.0.0.1:8000. Press Control-C in the terminal to stop.
Use the local server rather than opening HTML files directly, because the site uses root-relative asset URLs.

## Files

- `site/`: local copy with rewritten page and asset links.
- `original/`: original downloaded response bodies, before link rewriting.
- `mirror-manifest.json`: source URLs, downloaded file paths, sizes, content types, SHA-256 checksums, and failures.
- `verification.json`: results of the asset checks.
- `scripts/mirror.py`: downloader, using Python 3 and curl. Reuses files recorded in the manifest.
- `scripts/verify.py`: validates files and local HTML/CSS asset references.

The snapshot contains 160 successfully downloaded URLs (approximately 111 MB), including the homepage, two public author archives, sitemaps, styles, scripts, fonts, images, and videos. It includes dependencies discovered in HTML, CSS, and Elementor's runtime module references. Unmodified binary files are hard-linked between `original/` and `site/` to avoid duplicate storage; replace a binary file rather than modifying it in place if you want to preserve its original.

## Limits

This is a static copy of publicly accessible files discovered from the site, not a WordPress installation or complete hosting backup. PHP source, the database, admin features, private files, and unlinked files cannot be recovered from the public URL. The quote form needs a working backend; local submissions are not processed. External service integrations may still require internet access and the original services.

The original site references a video that currently returns HTTP 404:

https://sprung-go.com.au/wp-content/uploads/2026/10/luxury_ad_final.mp4

That file could not be copied. All 105 checked local HTML/CSS asset paths exist except this upstream-missing video. Browser rendering and interactive behavior have not been visually verified because the browser execution tool was unavailable. Consequently, pixel-perfect or fully functional equivalence is not certified.

## Publishing

Repository: https://github.com/matthiascamp/sprunggo.com

Pushes to `main` deploy the contents of `site/` through GitHub Pages. The custom domain is `sprung-go.com`. GitHub Pages must use **GitHub Actions** as its build source; publishing from the repository root serves this README instead of the website.

At the domain's DNS provider, configure four `A` records for `@`:
`185.199.108.153`, `185.199.109.153`, `185.199.110.153`, and `185.199.111.153`.
Optionally configure `www` as a `CNAME` pointing to `matthiascamp.github.io`.
After DNS resolves and GitHub provisions the certificate, enable Enforce HTTPS in the repository's Pages settings.
