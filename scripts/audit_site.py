#!/usr/bin/env python3
"""Offline public-artifact audit. JSON stdout, exit 1 for unresolved errors.

Use --root with the actual lftp artifact, not a regex approximation. Tooling
folders are excluded as *scan sources*, never as link targets: a public link
to an omitted tool still fails. No network requests or data modifications.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

PRIVATE_DIRS = {'.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache',
                'tests', 'scripts', 'docs', 'branding', 'shopify-app', '_assets'}
LOCAL_HOSTS = {'iamtoxico.com', 'www.iamtoxico.com'}
CSS_URL = re.compile(r'url\(\s*[\'"]?([^\s\)\'"]+)[\'"]?\s*\)', re.I)
CSS_IMPORT = re.compile(r'@import\s+[\'"]([^\'"]+)[\'"]', re.I)


def css_links(text):
    return [('css', url) for url in CSS_URL.findall(text) + CSS_IMPORT.findall(text)]


class PageLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.errors = []
        self.capture = None
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ('href', 'src'):
            if attrs.get(key):
                self.links.append((key, attrs[key]))
        if attrs.get('style'):
            self.links.extend(css_links(attrs['style']))
        if tag == 'style' or (tag == 'script' and attrs.get('id') == 'tiles-data'):
            self.capture = tag
            self.parts = []

    def handle_data(self, data):
        if self.capture:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag != self.capture:
            return
        text = ''.join(self.parts)
        if tag == 'style':
            self.links.extend(css_links(text))
        else:
            try:
                self.tile_links(json.loads(text))
            except (ValueError, TypeError):
                self.errors.append('invalid_tiles_json')
        self.capture = None

    def tile_links(self, value):
        if isinstance(value, list):
            for item in value:
                self.tile_links(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                if key in {'u', 'buy', 'f', 'b', 'image', 'src'} and isinstance(item, str) and item:
                    self.links.append(('tiles-data.' + key, item))
                elif isinstance(item, (dict, list)):
                    self.tile_links(item)


def local_target(root, source, url):
    parsed = urlsplit(url)
    if parsed.netloc and parsed.hostname not in LOCAL_HOSTS:
        return None
    if parsed.scheme and parsed.scheme not in {'http', 'https'}:
        return None
    if not parsed.path:
        return None
    path = unquote(parsed.path)
    target = ((root / path.lstrip('/')) if path.startswith('/') else
              root / source.parent / path).resolve()
    if not target.is_relative_to(root):
        return target  # escapes the artifact: reported as missing
    if target.is_dir():
        target /= 'index.html'
    return target


def price_state(product):
    if 'price' not in product:
        return 'missing'
    value = product['price']
    if value is None or (isinstance(value, str) and not value.strip()):
        return 'empty'
    if isinstance(value, bool):
        return 'invalid'
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        return 'invalid'
    if not number.is_finite() or number < 0:
        return 'invalid'
    return 'zero' if number == 0 else 'positive'


def availability(product):
    """No truthiness/default-active coercion; conflicting signals need an owner."""
    signals = []
    if 'active' in product:
        if not isinstance(product['active'], bool):
            return 'unknown'
        signals.append(product['active'])
    if 'status' in product:
        status = product['status']
        if not isinstance(status, str) or status.strip().lower() not in {'active', 'draft', 'archived', 'inactive'}:
            return 'unknown'
        signals.append(status.strip().lower() == 'active')
    if not signals:
        return 'unknown'
    if len(set(signals)) > 1:
        return 'conflict'
    return 'active' if signals[0] else 'inactive'


def audit_catalog(root, findings):
    path = root / 'data/catalog.json'
    if not path.is_file():
        return {'present': False, 'products': [], 'duplicates': []}
    data = json.loads(path.read_text(encoding='utf-8'))
    products = data['products']
    rows, ids = [], defaultdict(list)
    for index, product in enumerate(products):
        identifier = product.get('id')
        state = price_state(product)
        active = availability(product)
        has_url = isinstance(product.get('url'), str) and bool(product['url'].strip())
        sale_ready = active == 'active' and has_url
        row = {'index': index, 'id': identifier, 'price_state': state,
               'availability': active, 'sale_ready': sale_ready}
        rows.append(row)
        if active == 'active':
            url = product.get('url')
            url_code, target = None, None
            if 'url' not in product:
                url_code = 'active_url_missing'
            elif url is None or (isinstance(url, str) and not url.strip()):
                url_code = 'active_url_empty'
            elif not isinstance(url, str):
                url_code = 'active_url_invalid'
            else:
                try:
                    parsed = urlsplit(url)
                    if (parsed.scheme not in {'', 'http', 'https'} or
                            (parsed.scheme and not parsed.hostname) or
                            (not parsed.path and not parsed.netloc) or
                            any(ord(c) < 32 for c in unquote(url))):
                        raise ValueError('invalid catalog URL')
                    # Catalog URLs are storefront-relative, not relative to data/.
                    target = local_target(root, Path('index.html'), url)
                    if target is not None and (not target.is_relative_to(root) or not target.is_file()):
                        url_code = 'missing_target'
                except (ValueError, OSError):
                    url_code = 'active_url_invalid'
            if url_code:
                finding = dict(row, code=url_code, severity='error',
                               source='data/catalog.json', kind='catalog.url',
                               url=url, needs_jason=True)
                if url_code == 'missing_target' and target is not None:
                    finding['target'] = (target.relative_to(root).as_posix()
                                         if target.is_relative_to(root) else '<outside-root>')
                findings.append(finding)
        if identifier is not None:
            ids[str(identifier)].append(index)
        code = None
        if active in {'unknown', 'conflict'}:
            code = 'ambiguous_availability'
        elif active == 'active' and state != 'positive':
            code = 'sale_ready_zero_price' if state == 'zero' and sale_ready else 'active_price_' + state
        if code:
            findings.append(dict(row, code=code, source='data/catalog.json',
                                 severity='error', needs_jason=True,
                                 price=product.get('price'), url=product.get('url')))
    duplicates = [{'id': identifier, 'indices': indices} for identifier, indices in sorted(ids.items())
                  if len(indices) > 1]
    for duplicate in duplicates:
        findings.append(dict(duplicate, code='duplicate_product_id', severity='error',
                             source='data/catalog.json', needs_jason=True))
    return {'present': True, 'products': rows, 'duplicates': duplicates,
            'price_states': dict(sorted(Counter(r['price_state'] for r in rows).items())),
            'availability_states': dict(sorted(Counter(r['availability'] for r in rows).items()))}


def audit(root):
    root = Path(root).resolve()
    findings = []
    sources = []
    checked = 0
    for path in sorted(root.rglob('*')):
        source = path.relative_to(root)
        if any(part in PRIVATE_DIRS or part.startswith('.') for part in source.parts):
            continue
        if not path.is_file() or path.suffix.lower() not in {'.html', '.css'}:
            continue
        sources.append(source.as_posix())
        text = path.read_text(encoding='utf-8', errors='replace')
        if path.suffix.lower() == '.html':
            page = PageLinks()
            page.feed(text)
            links = page.links
            findings.extend({'code': e, 'source': source.as_posix(), 'severity': 'error'}
                            for e in page.errors)
        else:
            links = css_links(text)
        for kind, url in links:
            target = local_target(root, source, url)
            if target is None:
                continue
            checked += 1
            if not target.is_relative_to(root) or not target.is_file():
                findings.append({'code': 'missing_target', 'severity': 'error',
                                 'source': source.as_posix(), 'kind': kind, 'url': url,
                                 'target': target.relative_to(root).as_posix()
                                 if target.is_relative_to(root) else '<outside-root>'})
    catalog = audit_catalog(root, findings)
    findings.sort(key=lambda f: json.dumps(f, sort_keys=True))
    return {'schema_version': 1, 'summary': {'sources': len(sources),
            'internal_references': checked, 'errors': len(findings)}, 'findings': findings,
            'catalog': catalog, 'needs_jason': [f for f in findings if f.get('needs_jason')]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, help='also write the JSON report here')
    args = parser.parse_args()
    if not args.root.is_dir():
        parser.error('--root must be an existing artifact directory')
    report = audit(args.root)
    text = json.dumps(report, indent=2, sort_keys=True) + '\n'
    if args.evidence:
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(text, encoding='utf-8')
    print(text, end='')
    return 1 if report['summary']['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
