"""Tests for the Shopify-app Flask server (shopify-app/server.py).

Routes: /, /shopify/install, /shopify/webhooks/orders, /printify/status, etc.
"""
import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOPIFY_APP = os.path.join(ROOT, 'shopify-app')
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if SHOPIFY_APP not in sys.path:
    sys.path.insert(0, SHOPIFY_APP)


@pytest.fixture(scope='module')
def shopify_app():
    os.environ.setdefault('SHOPIFY_API_KEY', 'test-key')
    os.environ.setdefault('SHOPIFY_API_SECRET', 'test-secret')

    # Need to import from shopify-app directory
    import importlib
    spec = importlib.util.spec_from_file_location('shopify_server', os.path.join(SHOPIFY_APP, 'server.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.app.config['TESTING'] = True
    mod.app.config['SECRET_KEY'] = 'test'
    return mod


@pytest.fixture
def shopify_client(shopify_app):
    return shopify_app.app.test_client()


class TestShopifyAppHome:
    def test_home_returns_json(self, shopify_client):
        rv = shopify_client.get('/')
        assert rv.status_code == 200
        data = rv.get_json()
        assert data['app'] == 'iamtoxico Shopify Integration'
        assert data['status'] == 'running'

    def test_home_lists_endpoints(self, shopify_client):
        rv = shopify_client.get('/')
        data = rv.get_json()
        assert 'endpoints' in data
        assert 'install' in data['endpoints']
        assert 'callback' in data['endpoints']
        assert 'webhooks' in data['endpoints']


class TestShopifyInstall:
    def test_install_requires_shop_param(self, shopify_client):
        rv = shopify_client.get('/shopify/install')
        assert rv.status_code == 400

    def test_install_redirects_with_shop(self, shopify_client):
        rv = shopify_client.get('/shopify/install?shop=test.myshopify.com')
        # Should redirect to Shopify OAuth
        assert rv.status_code == 302
        assert 'test.myshopify.com' in rv.headers.get('Location', '')


class TestShopifyWebhook:
    def test_webhook_accepts_post(self, shopify_client):
        rv = shopify_client.post(
            '/shopify/webhooks/orders',
            json={'id': 12345, 'line_items': []},
            headers={'X-Shopify-Hmac-SHA256': '', 'X-Shopify-Topic': 'orders/create'}
        )
        assert rv.status_code == 200
        data = rv.get_json()
        assert data['status'] == 'received'


class TestPrintifyStatus:
    def test_printify_status_without_key(self, shopify_client):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('PRINTIFY_API_KEY', None)
            rv = shopify_client.get('/printify/status')
            assert rv.status_code == 200
            data = rv.get_json()
            assert data['connected'] is False

    @patch('printify_connector.requests.request')
    def test_printify_status_with_key(self, mock_req, shopify_client):
        os.environ['PRINTIFY_API_KEY'] = 'test-key'
        resp = MagicMock()
        resp.json.return_value = [{'id': 1, 'title': 'toxico-shop'}]
        resp.content = json.dumps([{'id': 1, 'title': 'toxico-shop'}]).encode()
        resp.raise_for_status.return_value = None
        mock_req.return_value = resp
        rv = shopify_client.get('/printify/status')
        data = rv.get_json()
        assert data['connected'] is True


class TestPrintifyBlueprints:
    def test_blueprints_without_connection(self, shopify_client, shopify_app):
        shopify_app.printify = None
        rv = shopify_client.get('/printify/blueprints')
        assert rv.status_code == 400


# ===================================================================
# NEW: Additional webhook endpoints
# ===================================================================

class TestShopifyProductWebhook:
    def test_webhook_products_accepts_post(self, shopify_client):
        rv = shopify_client.post(
            '/shopify/webhooks/products',
            json={'id': 777, 'title': 'New Hoodie'},
            headers={'X-Shopify-Hmac-SHA256': '', 'X-Shopify-Topic': 'products/create'}
        )
        assert rv.status_code == 200
        assert rv.get_json()['status'] == 'received'


class TestShopifyRefundWebhook:
    def test_webhook_refunds_accepts_post(self, shopify_client):
        rv = shopify_client.post(
            '/shopify/webhooks/refunds',
            json={'id': 50, 'order_id': 100},
            headers={'X-Shopify-Hmac-SHA256': '', 'X-Shopify-Topic': 'refunds/create'}
        )
        assert rv.status_code == 200
        assert rv.get_json()['status'] == 'received'


class TestShopifyAppWebhook:
    def test_webhook_app_uninstalled(self, shopify_client):
        rv = shopify_client.post(
            '/shopify/webhooks/app',
            json={},
            headers={'X-Shopify-Hmac-SHA256': '', 'X-Shopify-Topic': 'app/uninstalled'}
        )
        assert rv.status_code == 200
        assert rv.get_json()['status'] == 'received'


class TestPrintifyInboundWebhook:
    def test_printify_webhook_accepts_post(self, shopify_client):
        rv = shopify_client.post(
            '/printify/webhooks',
            json={'type': 'order:shipping-update', 'resource': {}}
        )
        assert rv.status_code == 200
        assert rv.get_json()['status'] == 'received'

    def test_printify_webhook_handles_completion(self, shopify_client):
        rv = shopify_client.post(
            '/printify/webhooks',
            json={'type': 'order:completed', 'resource': {'external_id': '123'}}
        )
        assert rv.status_code == 200


class TestWebhookRegistration:
    def test_register_webhooks_endpoint(self, shopify_client):
        rv = shopify_client.post('/webhooks/register')
        assert rv.status_code == 200
        data = rv.get_json()
        assert 'shopify' in data
        assert 'printify' in data


class TestOrderTopicRouting:
    def test_orders_create_topic(self, shopify_client):
        rv = shopify_client.post(
            '/shopify/webhooks/orders',
            json={'id': 1, 'line_items': [{'sku': 'PRFY_p1_100', 'quantity': 1}],
                  'shipping_address': {'first_name': 'A', 'last_name': 'B',
                                       'address1': '1 St', 'city': 'NY',
                                       'province_code': 'NY', 'country_code': 'US',
                                       'zip': '10001'}, 'email': 'a@b.com'},
            headers={'X-Shopify-Topic': 'orders/create'}
        )
        assert rv.status_code == 200

    def test_orders_cancelled_topic(self, shopify_client):
        rv = shopify_client.post(
            '/shopify/webhooks/orders',
            json={'id': 2, 'line_items': []},
            headers={'X-Shopify-Topic': 'orders/cancelled'}
        )
        assert rv.status_code == 200

    def test_orders_fulfilled_topic(self, shopify_client):
        rv = shopify_client.post(
            '/shopify/webhooks/orders',
            json={'id': 3},
            headers={'X-Shopify-Topic': 'orders/fulfilled'}
        )
        assert rv.status_code == 200

    def test_orders_updated_topic(self, shopify_client):
        rv = shopify_client.post(
            '/shopify/webhooks/orders',
            json={'id': 4},
            headers={'X-Shopify-Topic': 'orders/updated'}
        )
        assert rv.status_code == 200
