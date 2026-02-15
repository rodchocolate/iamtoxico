#!/usr/bin/env python3
"""
Fetch images listed in a markdown file and save them locally with normalized names.

Markdown format (anywhere in the file):
- Title: <short-title>
- Source URL: <https://example.com/file.jpg>
- Rights: PD | CC0 | Other (skipped by default unless --allow-non-pd)
- Save As: <relative/path/filename.ext>  # optional; otherwise auto-derived

Example block:
1) Joe Louis Army mess hall 1942
- Source URL: https://commons.wikimedia.org/wiki/Special:FilePath/Joe_Louis_Army_mess_hall_1942.jpg?download
- Rights: PD
- Save As: docs/design/reference-images/prize-fighters/black/joe-louis_army-mess-hall_1942.jpg

Usage:
  python3 scripts/fetch_images.py reference-md-file.md [--base-dir .] [--allow-non-pd]
  
New options:
  --staging-dir <dir>      Also write a flat copy of each fetched asset into this folder (default: docs/design/reference-images/_staging)
  --no-staging             Disable writing a second copy to staging
  --backfill-only          Do not fetch; only run backfill tasks (used/staging)
  --backfill-used          Copy all existing images under images-root into a flat 'used' folder (one-time setup)
  --used-dir <dir>         Flat curated folder where you keep only in-use images (default: docs/design/reference-images/_used)
  --images-root <dir>      Root folder to scan for images when backfilling (default: docs/design/reference-images)
  --write-resolved         After fetching, replace Source URL lines with resolved direct file URLs in-place

Smart search resolution:
- Resolves Commons search links and LoC/NARA searches to concrete Commons files where possible.

Notes:
- Supports <...> or plain URLs.
- Writes a fetch_images.log with successes and failures.
"""
from __future__ import annotations
import argparse
import os
import re
import sys
import urllib.parse
from pathlib import Path

import hashlib
import shutil
import requests
import json

COMMONS_API = "https://commons.wikimedia.org/w/api.php"

# Global HTTP session with headers to avoid 403 from some hosts (e.g., Wikimedia Commons)
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "iamtoxico-fetch/1.0 (+https://iamtoxico.com)",
    "Accept": "*/*",
})

TITLE_RE = re.compile(r"^\s*\d+\)\s*(?P<title>.+)$", re.I)
URL_RE = re.compile(r"^\s*-\s*Source URL:\s*<?(?P<url>https?[^>\s]+)>?\s*$", re.I)
RIGHTS_RE = re.compile(r"^\s*-\s*Rights( statement)?:\s*(?P<rights>.+)$", re.I)
SAVEAS_RE = re.compile(r"^\s*-\s*Save As:\s*(?P<save>.+)$", re.I)
BULK_COMM_RE = re.compile(r"^\s*-\s*Bulk Commons Search:\s*(?P<query>.+)$", re.I)
BULK_LIMIT_RE = re.compile(r"^\s*-\s*Limit:\s*(?P<limit>\d+)\s*$", re.I)
BULK_SAVEDIR_RE = re.compile(r"^\s*-\s*Save Dir:\s*(?P<dir>.+)$", re.I)
BULK_PREFIX_RE = re.compile(r"^\s*-\s*Filename Prefix:\s*(?P<prefix>.+)$", re.I)

ALLOWED_RIGHTS = {"pd", "public domain", "cc0", "no known restrictions"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
HEADER_RE = re.compile(r"^\s*##\s+")

# Request extmetadata for license checks
COMMONS_IMGINFO_PROPS = "url|mime|extmetadata"


def slugify(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")
    return text.lower()[:80]


def derive_filename(title: str, url: str) -> str:
    # Try to get extension from URL path
    path = urllib.parse.urlparse(url).path
    ext = os.path.splitext(path)[1] or ".jpg"
    return f"{slugify(title)}{ext}"


def iter_blocks(lines):
    """Yield blocks of (title, url, rights, saveas) from markdown lines.

    Notes:
    - Only the first Source URL / Rights / Save As after a Title line are used.
    - Section headers (## ...) act as boundaries; they will flush any pending block.
    """
    title = url = rights = saveas = None
    for line in lines:
        # Section header boundary flush
        if HEADER_RE.match(line):
            if title and url:
                yield title, url, rights, saveas
            title = url = rights = saveas = None
            continue

        m = TITLE_RE.match(line)
        if m:
            if title and url:
                yield title, url, rights, saveas
            title, url, rights, saveas = m.group("title").strip(), None, None, None
            continue
        m = URL_RE.match(line)
        if m:
            if url is None:  # ignore subsequent Source URL lines until next Title
                url = m.group("url").strip()
            continue
        m = RIGHTS_RE.match(line)
        if m:
            if rights is None:
                rights = m.group("rights").strip().lower()
            continue
        m = SAVEAS_RE.match(line)
        if m:
            if saveas is None:
                saveas = m.group("save").strip()
            continue
        # Flush on blank line if we have a complete block
        if not line.strip() and title and url:
            yield title, url, rights, saveas
            title = url = rights = saveas = None
    if title and url:
        yield title, url, rights, saveas


def should_fetch(rights: str | None, allow_non_pd: bool) -> bool:
    if allow_non_pd:
        return True
    if not rights:
        return False
    return rights.lower() in ALLOWED_RIGHTS


def _hash8(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:8]


def _safe_flat_path(flat_dir: Path, base_name: str, unique_key: str) -> Path:
    # Ensure the file name is unique in flat folder; if exists, append a short hash
    candidate = flat_dir / base_name
    if candidate.exists():
        stem, ext = os.path.splitext(base_name)
        candidate = flat_dir / f"{stem}__{_hash8(unique_key)}{ext}"
    return candidate


def fetch(url: str, dest_path: Path) -> tuple[bool, str]:
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    def _download(u: str) -> None:
        # Add a Referer for hosts that check it
        headers = {}
        parsed = urllib.parse.urlparse(u)
        if "commons.wikimedia.org" in parsed.netloc:
            headers["Referer"] = "https://commons.wikimedia.org/"
        with SESSION.get(u, timeout=90, allow_redirects=True, stream=True, headers=headers) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

    try:
        try:
            _download(url)
        except requests.HTTPError as e:
            status = getattr(e.response, "status_code", None)
            # Fallback: resolve Special:FilePath to upload URL via HEAD, then GET
            if status in (403, 404) and "commons.wikimedia.org" in url:
                try:
                    h = SESSION.head(url, timeout=60, allow_redirects=True)
                    h.raise_for_status()
                    final_url = h.url
                    _download(final_url)
                except Exception as e2:
                    return False, f"{e} | head-fallback: {e2}"
            else:
                return False, str(e)
        size = os.path.getsize(dest_path)
        return True, f"saved {dest_path} ({size} bytes)"
    except Exception as e:
        return False, str(e)


def backfill_to_flat(images_root: Path, flat_dir: Path, log_lines: list[str]) -> None:
    images_root = images_root.resolve()
    flat_dir = flat_dir.resolve()
    for root, dirs, files in os.walk(images_root):
        # Skip the flat directory itself to avoid loops
        root_path = Path(root).resolve()
        if root_path == flat_dir or root_path.as_posix().startswith(flat_dir.as_posix() + "/"):
            continue
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext not in IMAGE_EXTS:
                continue
            src_path = Path(root) / name
            base_name = name
            dest_path = _safe_flat_path(flat_dir, base_name, str(src_path))
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(src_path, dest_path)
                log_lines.append(f"FLAT-BACKFILL: {src_path} -> {dest_path}")
            except Exception as e:
                log_lines.append(f"ERR-FLAT-BACKFILL: {src_path} -> {dest_path} :: {e}")


def _clean_search_terms(q: str) -> str:
    q2 = re.sub(r"[()]+", " ", q)
    q2 = re.sub(r"\b(Bain News Service|photograph|photo|images?)\b", " ", q2, flags=re.I)
    q2 = re.sub(r"\s+", " ", q2).strip()
    return q2


def extract_query_param(url: str, key: str) -> str | None:
    try:
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        vals = qs.get(key)
        if vals:
            return vals[0]
    except Exception:
        return None
    return None


def is_pd_commons_imageinfo(imageinfo: dict) -> bool:
    try:
        meta = imageinfo.get("extmetadata", {}) or {}
        license_short = meta.get("LicenseShortName", {}).get("value", "")
        usage_terms = meta.get("UsageTerms", {}).get("value", "")
        credit = meta.get("Credit", {}).get("value", "")
        # Consider PD if explicitly marked Public domain
        if "public domain" in license_short.lower() or "public domain" in usage_terms.lower():
            return True
        # Many Gottlieb and Bain files include LC credit; these are PD pre-1929 or PD-Gottlieb
        if any(k in credit.lower() for k in ["library of congress", "william p. gottlieb", "bain news service", "harris & ewing", "us navy", "nara"]):
            # Not strictly license-based, but high-confidence PD set we target
            return True
        return False
    except Exception:
        return False


def resolve_commons_search(search_terms: str, log_lines: list[str], limit: int = 10) -> list[dict]:
    results: list[dict] = []
    try:
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": search_terms,
            "srnamespace": 6,
            "srlimit": limit,
        }
        r = SESSION.get(COMMONS_API, params=params, timeout=45)
        r.raise_for_status()
        data = r.json()
        for res in data.get("query", {}).get("search", []):
            title = res.get("title")
            if not title:
                continue
            # Fetch imageinfo with extmetadata for PD filtering
            params2 = {
                "action": "query",
                "format": "json",
                "prop": "imageinfo",
                "titles": title,
                "iiprop": COMMONS_IMGINFO_PROPS,
            }
            r2 = SESSION.get(COMMONS_API, params=params2, timeout=45)
            r2.raise_for_status()
            d2 = r2.json()
            pages = d2.get("query", {}).get("pages", {})
            for _, page in pages.items():
                ii_list = page.get("imageinfo")
                if not ii_list:
                    continue
                ii = ii_list[0]
                url = ii.get("url")
                mime = ii.get("mime", "")
                if not url or not mime.startswith("image/"):
                    continue
                pd_ok = is_pd_commons_imageinfo(ii)
                results.append({
                    "title": title,
                    "url": url,
                    "pd": pd_ok,
                })
        log_lines.append(f"RESOLVED-BULK: commons '{search_terms}' -> {len(results)} candidates")
    except Exception as e:
        log_lines.append(f"ERR-RESOLVE-BULK: commons '{search_terms}' :: {e}")
    return results


def run_bulk_tasks(md_path: Path, base: Path, staging_enabled: bool, staging_dir: Path | None, log_lines: list[str], only_pd: bool = True) -> None:
    try:
        lines = md_path.read_text(encoding="utf-8").splitlines()
    except Exception as e:
        log_lines.append(f"ERR: reading {md_path}: {e}")
        return

    i = 0
    while i < len(lines):
        line = lines[i]
        m = BULK_COMM_RE.match(line)
        if not m:
            i += 1
            continue
        query = _clean_search_terms(m.group("query").strip())
        limit = 50  # desired number of images to SAVE
        save_dir = None
        prefix = None
        j = i + 1
        while j < len(lines):
            l2 = lines[j]
            if l2.strip().startswith("-"):
                lm = BULK_LIMIT_RE.match(l2) or BULK_SAVEDIR_RE.match(l2) or BULK_PREFIX_RE.match(l2)
                if lm:
                    if BULK_LIMIT_RE.match(l2):
                        limit = int(BULK_LIMIT_RE.match(l2).group("limit"))
                    elif BULK_SAVEDIR_RE.match(l2):
                        save_dir = BULK_SAVEDIR_RE.match(l2).group("dir").strip()
                    elif BULK_PREFIX_RE.match(l2):
                        prefix = BULK_PREFIX_RE.match(l2).group("prefix").strip()
                    j += 1
                    continue
            break
        i = j  # advance cursor past this bulk block
        if not save_dir:
            log_lines.append(f"ERR-BULK: Missing 'Save Dir' for bulk query '{query}'")
            continue
        # Execute bulk search: fetch more than needed to survive PD filtering
        search_limit = max(120, limit * 3)
        candidates = resolve_commons_search(query, log_lines, limit=search_limit)
        count = 0
        for res in candidates:
            if only_pd and not res.get("pd"):
                continue
            url = res["url"]
            title = res["title"]  # File:...
            # Derive filename
            base_name = urllib.parse.unquote(os.path.basename(urllib.parse.urlparse(url).path))
            stem, ext = os.path.splitext(base_name)
            safe_stem = slugify(stem.replace("File:", ""))
            if prefix:
                fname = f"{prefix}{safe_stem}{ext}"
            else:
                fname = f"{safe_stem}{ext}"
            dest = base / save_dir / fname
            ok, msg = fetch(url, dest)
            status = "OK" if ok else "ERR"
            log_lines.append(f"{status}-BULK: {title} <- {url} -> {dest} :: {msg}")
            print(log_lines[-1])
            if ok and staging_enabled and staging_dir is not None:
                try:
                    staging_dir.mkdir(parents=True, exist_ok=True)
                    flat_dest = _safe_flat_path(staging_dir, fname, url)
                    shutil.copy2(dest, flat_dest)
                    log_lines.append(f"STAGING-BULK: {dest} -> {flat_dest}")
                    print(log_lines[-1])
                except Exception as se:
                    log_lines.append(f"ERR-STAGING-BULK: {dest} -> {staging_dir} :: {se}")
            count += 1
            if count >= limit:
                break
        log_lines.append(f"BULK-DONE: saved {count}/{limit} images for '{query}' to {save_dir}")


def write_resolved_urls_in_md(md_path: Path, replacements: dict[str, str]) -> None:
    try:
        lines = md_path.read_text(encoding="utf-8").splitlines(True)
        new_lines = []
        for line in lines:
            m = URL_RE.match(line)
            if m:
                orig = m.group("url").strip()
                new_url = replacements.get(orig)
                if new_url and new_url != orig:
                    # Preserve angle brackets if present
                    prefix = line.split("Source URL:", 1)[0]
                    if "<" in line and ">" in line:
                        line = re.sub(r"<https?[^>\s]+>", f"<{new_url}>", line)
                    else:
                        line = f"{prefix}Source URL: {new_url}\n"
            new_lines.append(line)
        md_path.write_text("".join(new_lines), encoding="utf-8")
    except Exception:
        pass


def resolve_source_url(title: str, url: str, log_lines: list[str]) -> str:
    """Resolve search/listing URLs to a concrete direct image URL when possible.
    Preference order: first PD result from Commons search; otherwise first result.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path
        ext = os.path.splitext(path)[1].lower()

        # Already a direct image or Special:FilePath with an image extension
        if ext in IMAGE_EXTS:
            return url
        if "/wiki/Special:FilePath".lower() in path.lower() and (ext in IMAGE_EXTS):
            return url

        # Commons search links (MediaSearch or index search)
        if "commons.wikimedia.org" in host and ("/w/index.php" in path or "Special:MediaSearch" in path):
            q = extract_query_param(url, "search") or extract_query_param(url, "q") or title
            q = _clean_search_terms(q)
            results = resolve_commons_search(q, log_lines, limit=10)
            for r in results:
                if r.get("pd"):
                    return r["url"]
            return results[0]["url"] if results else url

        # LOC searches -> try Commons with hints
        if "loc.gov" in host:
            q = extract_query_param(url, "q") or title
            q_clean = _clean_search_terms(q)
            lower = q_clean.lower()
            if any(n in lower for n in ["duke", "dizzy", "miles", "monk", "parker", "basie", "armstrong", "hawkins", "blakey", "powell", "lester", "rollins", "machito", "bauza", "pozo"]):
                if "gottlieb" not in lower:
                    q_clean = f"{q_clean} \"William P. Gottlieb\""
            if any(n in lower for n in ["sam langford", "joe gans", "panama al brown", "sugar ray robinson", "henry armstrong"]):
                q_clean = f"{q_clean} boxer"
            results = resolve_commons_search(q_clean, log_lines, limit=10)
            for r in results:
                if r.get("pd"):
                    return r["url"]
            return results[0]["url"] if results else url

        # NARA catalog searches -> Commons
        if "catalog.archives.gov" in host and "/search" in path:
            q = extract_query_param(url, "q") or title
            q = _clean_search_terms(q)
            results = resolve_commons_search(q, log_lines, limit=10)
            for r in results:
                if r.get("pd"):
                    return r["url"]
            return results[0]["url"] if results else url

        # U.S. Navy -> Commons
        if "history.navy.mil" in host:
            q = extract_query_param(url, "q") or title
            q = _clean_search_terms(q)
            results = resolve_commons_search(f"{q} US Navy", log_lines, limit=10)
            for r in results:
                if r.get("pd"):
                    return r["url"]
            return results[0]["url"] if results else url

        return url
    except Exception:
        return url


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("md_file", help="Markdown file with image entries")
    ap.add_argument("--base-dir", default=".", help="Base directory to resolve Save As paths")
    ap.add_argument("--allow-non-pd", action="store_true", help="Fetch even if rights not PD/CC0")
    # Flat copy on fetch (staging)
    ap.add_argument("--staging-dir", default="docs/design/reference-images/_staging", help="Flat folder where an extra copy of each fetched asset will be written")
    ap.add_argument("--no-staging", action="store_true", help="Disable writing a second copy to staging")
    # Backfill/flat workflows
    ap.add_argument("--backfill-only", action="store_true", help="Do not fetch; only run backfill tasks")
    ap.add_argument("--backfill-used", action="store_true", help="Copy all existing images under images-root into the flat curated 'used' folder")
    ap.add_argument("--used-dir", default="docs/design/reference-images/_used", help="Flat curated folder where you keep only in-use images")
    ap.add_argument("--images-root", default="docs/design/reference-images", help="Root folder to scan for images when backfilling to flat folders")
    # new arg
    ap.add_argument("--write-resolved", action="store_true", help="After fetching, replace Source URL lines with resolved direct file URLs in-place")
    # bulk processing args
    ap.add_argument("--enable-bulk", action="store_true", help="Process '- Bulk Commons Search' directives in the markdown before per-item fetches")
    ap.add_argument("--no-pd-filter", action="store_true", help="Do not filter bulk results by Public Domain metadata")
    args = ap.parse_args()

    base = Path(args.base_dir).resolve()
    md_path = Path(args.md_file).resolve()
    if not md_path.exists():
        print(f"Markdown file not found: {md_path}", file=sys.stderr)
        sys.exit(1)

    staging_enabled = not args.no_staging
    staging_dir = (base / args.staging_dir).resolve() if staging_enabled else None

    log_lines: list[str] = []
    replacements: dict[str, str] = {}

    # Bulk pass first (optional)
    if args.enable_bulk and not args.backfill_only:
        run_bulk_tasks(md_path, base, staging_enabled, staging_dir, log_lines, only_pd=(not args.no_pd_filter))

    if not args.backfill_only:
        with open(md_path, "r", encoding="utf-8") as fh:
            for title, url, rights, saveas in iter_blocks(fh):
                if not should_fetch(rights, args.allow_non_pd):
                    log_lines.append(f"SKIP: {title} — rights={rights!r}")
                    continue
                # Resolve search links to concrete image URLs when possible
                resolved_url = resolve_source_url(title, url, log_lines)
                if resolved_url and resolved_url != url:
                    replacements[url] = resolved_url
                filename = saveas or derive_filename(title, resolved_url)
                dest = base / filename
                ok, msg = fetch(resolved_url, dest)
                status = "OK" if ok else "ERR"
                log_lines.append(f"{status}: {title} <- {url} [resolved: {resolved_url}] -> {dest} :: {msg}")
                print(log_lines[-1])

                # Write flat copy to staging folder (second copy)
                if ok and staging_enabled and staging_dir is not None:
                    try:
                        staging_dir.mkdir(parents=True, exist_ok=True)
                        base_name = os.path.basename(filename)
                        flat_dest = _safe_flat_path(staging_dir, base_name, resolved_url)
                        shutil.copy2(dest, flat_dest)
                        log_lines.append(f"STAGING: {dest} -> {flat_dest}")
                        print(log_lines[-1])
                    except Exception as se:
                        log_lines.append(f"ERR-STAGING: {dest} -> {staging_dir} :: {se}")
                        print(log_lines[-1])

    # Optional one-time backfill of curated 'used' folder
    if args.backfill_used:
        used_dir = (base / args.used_dir).resolve()
        used_dir.mkdir(parents=True, exist_ok=True)
        images_root = (base / args.images_root).resolve()
        backfill_to_flat(images_root, used_dir, log_lines)

    # Optionally write back resolved URLs into the markdown file
    if not args.backfill_only and getattr(args, "write_resolved", False):
        write_resolved_urls_in_md(md_path, replacements)

    log_path = base / "fetch_images.log"
    with open(log_path, "w", encoding="utf-8") as lf:
        lf.write("\n".join(log_lines) + "\n")
    print(f"Log written to {log_path}")


if __name__ == "__main__":
    main()
