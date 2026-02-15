"""Shared fixtures for the iamtoxico test suite."""
import sys
import os
import json
import importlib.util
import pytest

# Ensure project root is on path so we can import connectors, etc.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
SHOPIFY_APP = os.path.join(ROOT, 'shopify-app')
if SHOPIFY_APP not in sys.path:
    sys.path.append(SHOPIFY_APP)  # append (not insert) to avoid shadowing root server


# ---------------------------------------------------------------------------
# Catalog fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def catalog_path():
    return os.path.join(ROOT, 'data', 'catalog.json')


@pytest.fixture
def catalog(catalog_path):
    with open(catalog_path, 'r') as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Flask test client for server.py (root)
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    """Create a Flask test client from the main server (root server.py)."""
    os.environ.pop('SPOTIFY_CLIENT_ID', None)
    os.environ.pop('SPOTIFY_CLIENT_SECRET', None)

    # Import root server.py explicitly by path to avoid shopify-app clash
    spec = importlib.util.spec_from_file_location(
        'main_server', os.path.join(ROOT, 'server.py'))
    mod = importlib.util.module_from_spec(spec)
    old_cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        spec.loader.exec_module(mod)
    finally:
        os.chdir(old_cwd)

    mod.app.config['TESTING'] = True
    mod.app.config['SECRET_KEY'] = 'test-secret'
    return mod.app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Shopify-app Flask test client
# ---------------------------------------------------------------------------

@pytest.fixture
def shopify_app():
    """Create a Flask test client for the shopify-app server."""
    os.environ.setdefault('SHOPIFY_API_KEY', 'test-key')
    os.environ.setdefault('SHOPIFY_API_SECRET', 'test-secret')
    os.environ.setdefault('PRINTIFY_API_KEY', 'test-printify-key')

    # Import shopify-app/server.py explicitly by path
    spec = importlib.util.spec_from_file_location(
        'shopify_server', os.path.join(SHOPIFY_APP, 'server.py'))
    mod = importlib.util.module_from_spec(spec)
    old_cwd = os.getcwd()
    os.chdir(SHOPIFY_APP)
    try:
        spec.loader.exec_module(mod)
    finally:
        os.chdir(old_cwd)

    mod.app.config['TESTING'] = True
    mod.app.config['SECRET_KEY'] = 'test-secret'
    return mod.app


@pytest.fixture
def shopify_client(shopify_app):
    return shopify_app.test_client()
