"""Static public routes and no-JS purchase destinations."""
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Anchors(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.anchors = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.anchors.append(dict(attrs))


def test_all_product_buy_links_have_canonical_no_js_fallback():
    failures = []
    pages = sorted((ROOT / 'product').glob('*.html'))
    assert pages
    for page in pages:
        for anchor in Anchors(page.read_text()).anchors:
            if 'buy' in anchor.get('class', '').split():
                expected = f'https://shop.iamtoxico.com/products/{page.stem}'
                if anchor.get('href') != expected:
                    failures.append((page.name, anchor.get('href')))
    assert not failures, failures


def test_landing_enters_existing_shop_page():
    anchors = Anchors((ROOT / 'landing.html').read_text()).anchors
    entry = next(a for a in anchors if a.get('aria-label') == 'Enter')
    assert entry['href'] == '/shop.html'
    assert (ROOT / entry['href'].lstrip('/')).is_file()
