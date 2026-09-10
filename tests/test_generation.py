"""Offline generator contracts. All writes use isolated fixture directories."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
STOREFRONT = SCRIPTS / "storefront" / "build_storefront.py"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def product_fixture(root):
    (root / "data").mkdir()
    (root / "data/shopify_variants.json").write_text(json.dumps({"products": {
        "new-shirt": {"t": "New Shirt", "v": [{"p": "80"}]},
        "missing-image": {"t": "Missing Image", "v": [{"p": "90"}]},
    }}))
    (root / "index.html").write_text('<main>authored introduction</main><script>' + json.dumps([
        {"u": "https://iamtoxico.myshopify.com/products/new-shirt", "f": "/shirt.jpg"},
        {"u": "https://iamtoxico.myshopify.com/products/missing-image"},
    ]) + '</script>')


def test_product_root_is_explicit_and_build_is_offline(tmp_path, monkeypatch):
    module = load("build_product_pages")
    product_fixture(tmp_path)
    def forbid_network(*args, **kwargs):
        raise AssertionError("generation must not read the network")
    monkeypatch.setattr(module.urllib.request, "urlopen", forbid_network)
    module.main(root=tmp_path)
    page = tmp_path / "product/new-shirt.html"
    assert page.is_file()
    assert 'name="robots" content="noindex, nofollow"' in page.read_text()
    assert not (tmp_path / "product/missing-image.html").exists()
    first = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    module.main(root=tmp_path)
    assert first == {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert 'authored introduction' in (tmp_path / 'index.html').read_text()


def test_buy_href_is_canonical_shopify_while_tiles_stay_local(tmp_path):
    """Product-page BUY button must fall back to the real Shopify checkout URL
    (cart.js progressively enhances it into the on-site picker); site tiles/nav
    that link to the product must repoint to the local /product/<handle>.html
    page instead, per the site's local-navigation convention."""
    module = load("build_product_pages")
    product_fixture(tmp_path)
    module.main(root=tmp_path)
    page = (tmp_path / "product/new-shirt.html").read_text()
    assert 'class="buy" href="https://shop.iamtoxico.com/products/new-shirt"' in page
    tile = (tmp_path / "index.html").read_text()
    assert '"/product/new-shirt.html"' in tile
    assert "myshopify.com/products/new-shirt" not in tile


def test_assets_exclusion_is_root_relative_not_substring(tmp_path):
    """The '_assets' exclusion must match a path *component* relative to
    --root, not a substring of the absolute path. A tmp_path containing the
    literal text '_assets' anywhere in its ancestry (e.g. a fixture dir named
    'site_assets_fixture') must not have its real site pages skipped; but a
    genuine <root>/_assets/x.html must still be excluded."""
    module = load("build_product_pages")

    tricky_root = tmp_path / "site_assets_fixture" / "site"
    tricky_root.mkdir(parents=True)
    product_fixture(tricky_root)
    (tricky_root / "_assets").mkdir()
    (tricky_root / "_assets" / "x.html").write_text(
        '<script>' + json.dumps([
            {"u": "https://iamtoxico.myshopify.com/products/new-shirt"}]) + '</script>')
    module.main(root=tricky_root)

    plain_root = tmp_path / "plain" / "site"
    plain_root.mkdir(parents=True)
    product_fixture(plain_root)
    (plain_root / "_assets").mkdir()
    (plain_root / "_assets" / "x.html").write_text(
        '<script>' + json.dumps([
            {"u": "https://iamtoxico.myshopify.com/products/new-shirt"}]) + '</script>')
    module.main(root=plain_root)

    def snapshot(root):
        return {str(p.relative_to(root)): p.read_bytes()
                for p in root.rglob('*') if p.is_file()}

    assert snapshot(tricky_root) == snapshot(plain_root)
    assert (plain_root / "product" / "new-shirt.html").is_file()
    assert (tricky_root / "product" / "new-shirt.html").is_file()
    # the real _assets folder is still excluded as a scan source: its handle
    # link must not have triggered a product page build from it alone (the
    # site index.html already references new-shirt so it will exist; verify
    # the _assets file itself was left untouched/unrepointed)
    assets_text = (plain_root / "_assets" / "x.html").read_text()
    assert "myshopify.com/products/new-shirt" in assets_text


def test_legacy_storefront_script_is_retired_not_run(tmp_path):
    """build_storefront.py's inputs (/tmp/*.json, a scratchpad sys.path hack)
    and hardcoded runtime REPO are long gone; it must refuse to run instead of
    crashing halfway or writing into the read-only runtime checkout."""
    result = subprocess.run(
        [sys.executable, str(STOREFRONT)], cwd=tmp_path,
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "retired" in (result.stdout + result.stderr).lower()
    assert "build_product_pages.py" in (result.stdout + result.stderr)
    assert not any(tmp_path.iterdir())


def test_canonical_shop_domain_tiles_are_built_and_repointed(tmp_path):
    """A tile whose only destination is the canonical shop.iamtoxico.com URL
    must be harvested (page built) and repointed to the local page; the built
    page's BUY stays canonical; unrelated hosts are left alone; second run is
    byte-identical."""
    module = load("build_product_pages")
    (tmp_path / "data").mkdir()
    (tmp_path / "data/shopify_variants.json").write_text(json.dumps({"products": {
        "canon-shirt": {"t": "Canon Shirt", "v": [{"p": "70"}]},
    }}))
    (tmp_path / "index.html").write_text('<script>' + json.dumps([
        {"u": "https://shop.iamtoxico.com/products/canon-shirt", "f": "/canon.jpg"},
        {"u": "https://example.com/products/other", "f": "/x.jpg"},
    ]) + '</script>')
    module.main(root=tmp_path)
    page = tmp_path / "product/canon-shirt.html"
    assert page.is_file()
    assert 'class="buy" href="https://shop.iamtoxico.com/products/canon-shirt"' in page.read_text()
    tile = (tmp_path / "index.html").read_text()
    assert '"/product/canon-shirt.html"' in tile
    assert "shop.iamtoxico.com/products/canon-shirt" not in tile
    assert "https://example.com/products/other" in tile
    snap = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    module.main(root=tmp_path)
    assert snap == {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
