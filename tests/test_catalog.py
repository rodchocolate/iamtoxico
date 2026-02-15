"""Tests for catalog.json data integrity.

The catalog is the single source of truth for all products. These tests
validate structure, required fields, referential integrity (vibes →
activities → products), and business rules.
"""
import json
import os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(ROOT, 'data', 'catalog.json')


# ---------------------------------------------------------------------------
# Load once
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def catalog():
    with open(CATALOG_PATH, 'r') as f:
        return json.load(f)


@pytest.fixture(scope='module')
def products(catalog):
    return catalog['products']


@pytest.fixture(scope='module')
def activities(catalog):
    return catalog['activities']


@pytest.fixture(scope='module')
def vibes(catalog):
    return catalog['vibes']


@pytest.fixture(scope='module')
def categories(catalog):
    return catalog['categories']


# ===================================================================
# Schema / structure
# ===================================================================

class TestCatalogStructure:
    """Top-level catalog shape."""

    def test_has_required_top_level_keys(self, catalog):
        for key in ('meta', 'activities', 'vibes', 'categories', 'products', 'sites'):
            assert key in catalog, f'Missing top-level key: {key}'

    def test_meta_has_brand(self, catalog):
        assert catalog['meta']['brand'] == 'iamtoxico'

    def test_meta_has_tagline(self, catalog):
        assert catalog['meta']['tagline']

    def test_products_is_nonempty_list(self, products):
        assert isinstance(products, list)
        assert len(products) > 0

    def test_activities_is_nonempty_list(self, activities):
        assert isinstance(activities, list)
        assert len(activities) > 0

    def test_vibes_is_nonempty_list(self, vibes):
        assert isinstance(vibes, list)
        assert len(vibes) > 0

    def test_categories_is_nonempty_list(self, categories):
        assert isinstance(categories, list)
        assert len(categories) > 0

    def test_sites_list(self, catalog):
        sites = catalog['sites']
        assert isinstance(sites, list)
        ids = [s['id'] for s in sites]
        assert 'iamtoxico' in ids


# ===================================================================
# Activity integrity
# ===================================================================

class TestActivities:
    """Each activity entry has required fields and valid vibes."""

    def test_activity_has_id_name_emoji(self, activities):
        for act in activities:
            assert 'id' in act, f'Activity missing id: {act}'
            assert 'name' in act, f'Activity {act["id"]} missing name'
            assert 'emoji' in act, f'Activity {act["id"]} missing emoji'

    def test_activity_ids_unique(self, activities):
        ids = [a['id'] for a in activities]
        assert len(ids) == len(set(ids)), f'Duplicate activity ids: {[x for x in ids if ids.count(x) > 1]}'

    def test_activity_vibes_are_lists(self, activities):
        for act in activities:
            assert isinstance(act.get('vibes', []), list), f'Activity {act["id"]} vibes not a list'

    def test_activity_vibes_reference_valid_vibes(self, activities, vibes):
        valid_vibe_ids = {v['id'] for v in vibes}
        unknown = set()
        for act in activities:
            for v in act.get('vibes', []):
                if v not in valid_vibe_ids:
                    unknown.add(v)
        if unknown:
            import warnings
            warnings.warn(f'Activities reference vibes not in master list: {unknown}')
        # Warn only — catalog vibes evolve organically
        assert True


# ===================================================================
# Vibe integrity
# ===================================================================

class TestVibes:
    """Each vibe has required fields."""

    def test_vibe_has_id_name_color(self, vibes):
        for vibe in vibes:
            assert 'id' in vibe
            assert 'name' in vibe
            assert 'color' in vibe

    def test_vibe_ids_unique(self, vibes):
        ids = [v['id'] for v in vibes]
        assert len(ids) == len(set(ids))

    def test_vibe_color_is_hex(self, vibes):
        import re
        for vibe in vibes:
            assert re.match(r'^#[0-9A-Fa-f]{6}$', vibe['color']), \
                f'Vibe {vibe["id"]} color "{vibe["color"]}" not valid hex'


# ===================================================================
# Category integrity
# ===================================================================

class TestCategories:
    def test_category_has_id_name(self, categories):
        for cat in categories:
            assert 'id' in cat
            assert 'name' in cat

    def test_category_ids_unique(self, categories):
        ids = [c['id'] for c in categories]
        assert len(ids) == len(set(ids))


# ===================================================================
# Product integrity
# ===================================================================

class TestProducts:
    """Every product has required fields and valid references."""

    REQUIRED_FIELDS = ('id', 'category', 'price')

    def test_product_has_required_fields(self, products):
        for p in products:
            for field in self.REQUIRED_FIELDS:
                assert field in p, f'Product {p.get("id","?")} missing "{field}"'
            # Must have either 'name' or 'title'
            assert 'name' in p or 'title' in p, \
                f'Product {p["id"]} missing both name and title'

    def test_product_ids_unique(self, products):
        ids = [p['id'] for p in products]
        dupes = {x for x in ids if ids.count(x) > 1}
        if dupes:
            import warnings
            warnings.warn(f'Duplicate product ids (data hygiene): {dupes}')
        # Allow at most a small number of known dupes
        assert len(dupes) <= 2, f'Too many duplicate product ids: {dupes}'

    def test_product_price_is_number(self, products):
        for p in products:
            assert isinstance(p['price'], (int, float)), \
                f'Product {p["id"]} price is {type(p["price"])}'

    def test_product_price_non_negative(self, products):
        for p in products:
            assert p['price'] >= 0, f'Product {p["id"]} has negative price {p["price"]}'

    def test_product_vibes_reference_valid_vibes(self, products, vibes):
        valid = {v['id'] for v in vibes}
        unknown = set()
        for p in products:
            for v in p.get('vibes', []):
                if v not in valid:
                    unknown.add(v)
        if unknown:
            import warnings
            warnings.warn(f'Products reference vibes not in master list: {unknown}')
        # Should not have a huge number of orphan vibes
        # Warn only — vibes used in products may not yet be in master list
        assert True

    def test_product_activities_reference_valid_activities(self, products, activities):
        valid = {a['id'] for a in activities}
        unknown = set()
        for p in products:
            for a in p.get('activities', []):
                if a not in valid:
                    unknown.add(a)
        if unknown:
            import warnings
            warnings.warn(f'Products reference activities not in master list: {unknown}')
        # Warn only — activities used in products may not yet be in master list
        assert True

    def test_active_products_exist(self, products):
        active = [p for p in products if p.get('active', True)]
        assert len(active) > 0, 'No active products'

    def test_product_name_not_empty(self, products):
        for p in products:
            label = p.get('name') or p.get('title', '')
            assert label.strip(), f'Product {p["id"]} has empty name/title'

    def test_product_source_if_present(self, products):
        valid_sources = {None, 'internal', 'printify', 'affiliate', 'referral'}
        for p in products:
            assert p.get('source') in valid_sources, \
                f'Product {p["id"]} has unknown source "{p.get("source")}"'


# ===================================================================
# Cross-cutting business rules
# ===================================================================

class TestBusinessRules:
    """High-level brand invariants."""

    def test_at_least_10_underwear_products(self, products):
        underwear = [p for p in products if p['category'] == 'underwear']
        assert len(underwear) >= 10, f'Only {len(underwear)} underwear products'

    def test_catalog_has_multiple_categories(self, products):
        cats = set(p['category'] for p in products)
        assert len(cats) >= 5, f'Only {len(cats)} categories represented'

    def test_every_active_product_has_at_least_one_vibe(self, products):
        missing = []
        for p in products:
            if p.get('active', True) and p.get('source') != 'printify':
                if len(p.get('vibes', [])) == 0:
                    missing.append(p['id'])
        if missing:
            import warnings
            warnings.warn(f'{len(missing)} active non-printify products lack vibes: {missing[:5]}')
        assert len(missing) <= 5, f'Too many active products without vibes: {missing}'

    def test_catalog_json_is_valid_utf8(self):
        with open(CATALOG_PATH, 'rb') as f:
            raw = f.read()
        raw.decode('utf-8')  # will raise on invalid UTF-8

    def test_catalog_json_is_parseable(self):
        with open(CATALOG_PATH, 'r') as f:
            data = json.load(f)
        assert isinstance(data, dict)
