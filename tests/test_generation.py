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
