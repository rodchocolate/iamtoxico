"""Deterministic audit fixtures: no network or storefront mutation."""
import json
from pathlib import Path
import subprocess
import sys

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/audit_site.py'


def run_audit(root):
    assert SCRIPT.is_file(), 'artifact audit CLI is missing'
    result = subprocess.run([sys.executable, str(SCRIPT), '--root', str(root)],
                            capture_output=True, text=True)
    return result.returncode, json.loads(result.stdout)


def test_artifact_links_include_tiles_css_and_ignore_tooling(tmp_path):
    (tmp_path / 'index.html').write_text('''<a href="/ok/?x=1#top">ok</a>
    <img src="/missing.png"><a href="https://iamtoxico.com/gone.html">bad</a>
    <script id="tiles-data" type="application/json">[{"u":"/product/gone.html","f":"/tile.png"}]</script>
    <style>.x{background:url('/inline.png')}</style><link href="/style.css" rel="stylesheet">
    <script>const template = '<a href="fake-template">';</script>''')
    (tmp_path / 'ok').mkdir()
    (tmp_path / 'ok/index.html').write_text('ok')
    (tmp_path / 'style.css').write_text('.x{background:url("/css.png")}')
    (tmp_path / 'tests').mkdir()
    (tmp_path / 'tests/private.html').write_text('<a href="/not-public">')
    code, report = run_audit(tmp_path)
    assert code == 1
    assert {f['url'] for f in report['findings']} == {
        '/missing.png', 'https://iamtoxico.com/gone.html', '/product/gone.html',
        '/tile.png', '/inline.png', '/css.png'}
    assert all(f['code'] == 'missing_target' for f in report['findings'])
    assert run_audit(tmp_path)[1] == report


def test_catalog_predicates_do_not_coerce_empty_missing_or_status(tmp_path):
    (tmp_path / 'data').mkdir()
    products = [
        {'id': 'missing', 'active': True, 'url': 'https://example.com/p'},
        {'id': 'empty', 'price': '', 'status': 'active', 'url': 'https://example.com/p'},
        {'id': 'zero', 'price': 0, 'status': 'active', 'url': 'https://example.com/p'},
        {'id': 'draft', 'price': 0, 'status': 'draft'},
        {'id': 'inactive', 'price': 0, 'active': False},
        {'id': 'unknown', 'price': 0, 'active': 'false'},
        {'id': 'conflict', 'price': 12, 'active': True, 'status': 'draft'},
        {'id': 'ok', 'price': '12.50', 'active': True, 'url': 'https://example.com/p'},
        {'id': 'ok', 'price': 12, 'status': 'active'},
        {'id': 'bool-price', 'price': False, 'active': True},
    ]
    (tmp_path / 'data/catalog.json').write_text(json.dumps({'products': products}))
    code, report = run_audit(tmp_path)
    assert code == 1
    rows = {p['id']: p for p in report['catalog']['products']}
    assert rows['missing']['price_state'] == 'missing'
    assert rows['empty']['price_state'] == 'empty'
    assert rows['zero']['price_state'] == 'zero'
    assert rows['zero']['sale_ready'] is True
    assert rows['draft']['availability'] == 'inactive'
    assert rows['inactive']['availability'] == 'inactive'
    assert rows['unknown']['availability'] == 'unknown'
    assert rows['conflict']['availability'] == 'conflict'
    assert rows['bool-price']['price_state'] == 'invalid'
    assert report['catalog']['duplicates'] == [{'id': 'ok', 'indices': [7, 8]}]
    errors = {f['code'] for f in report['findings']}
    assert {'duplicate_product_id', 'sale_ready_zero_price', 'active_price_missing',
            'active_price_empty', 'ambiguous_availability'} <= errors
    assert report['needs_jason']
    assert not any(f.get('id') in {'draft', 'inactive'} for f in report['needs_jason'])


def test_catalog_public_urls_are_checked_but_explicit_drafts_are_not(tmp_path):
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data/catalog.json').write_text(json.dumps({'products': [
        {'id': 'live', 'status': 'active', 'price': 25, 'url': 'https://iamtoxico.com/products/missing'},
        {'id': 'draft', 'status': 'draft', 'price': 0, 'url': '/unpublished'},
    ]}))
    code, report = run_audit(tmp_path)
    assert code == 1
    missing = [f for f in report['findings'] if f['code'] == 'missing_target']
    assert [(f['id'], f['target']) for f in missing] == [('live', 'products/missing')]
    assert report['catalog']['products'][1]['availability'] == 'inactive'


def test_active_catalog_url_states_and_untrusted_targets(tmp_path):
    (tmp_path / 'data').mkdir()
    (tmp_path / 'product').mkdir()
    (tmp_path / 'product/ok.html').write_text('ok')
    urls = {
        'empty': '', 'null': None, 'spaces': '  ', 'number': 42,
        'broken-host': 'https://[bad/products/x',
        'script': 'javascript:alert(1)', 'nul': '/product/%00.html',
        'traversal': '/../outside.html', 'encoded-traversal': '/%2e%2e/outside.html',
        'missing-page': '/product/gone.html',
        'local': '/product/ok.html?x=1#top', 'relative': 'product/ok.html',
        'external': 'https://example.com/products/ok',
        'external-root': 'https://example.com',
    }
    products = [dict(id=key, status='active', price=25, url=url) for key, url in urls.items()]
    products += [dict(id='absent', active=True, price=25),
                 dict(id='draft', status='draft', price=25, url='https://[bad'),
                 dict(id='inactive', active=False, price=25),
                 dict(id='unknown', price=25, url='/missing')]
    (tmp_path / 'data/catalog.json').write_text(json.dumps({'products': products}))
    code, report = run_audit(tmp_path)
    assert code == 1
    by_id = {f['id']: f for f in report['findings']}
    assert {key: f['code'] for key, f in by_id.items()} == {
        'absent': 'active_url_missing', 'empty': 'active_url_empty',
        'null': 'active_url_empty', 'spaces': 'active_url_empty',
        'number': 'active_url_invalid', 'broken-host': 'active_url_invalid',
        'script': 'active_url_invalid', 'nul': 'active_url_invalid',
        'traversal': 'missing_target', 'encoded-traversal': 'missing_target',
        'missing-page': 'missing_target', 'unknown': 'ambiguous_availability',
    }
    assert by_id['traversal']['target'] == '<outside-root>'
    assert by_id['encoded-traversal']['target'] == '<outside-root>'
    assert by_id['missing-page']['target'] == 'product/gone.html'
    assert not any('target' in by_id[key] for key in ('absent', 'empty', 'null', 'number'))
