"""Tests for the PrintifyConnector and ShopifyConnector classes.

These are unit tests — no real API calls. We mock requests.request to
verify URL construction, headers, payload shape, and error handling.
"""
import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOPIFY_APP = os.path.join(ROOT, 'shopify-app')
if SHOPIFY_APP not in sys.path:
    sys.path.insert(0, SHOPIFY_APP)

from printify_connector import PrintifyConnector, TOXICO_BLUEPRINTS, PREFERRED_PROVIDERS
from shopify_connector import ShopifyConnector, ShopifyPrintifyBridge


# ===================================================================
# PrintifyConnector
# ===================================================================

class TestPrintifyConnectorInit:
    def test_raises_without_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop('PRINTIFY_API_KEY', None)
            with pytest.raises(ValueError, match='PRINTIFY_API_KEY'):
                PrintifyConnector(api_key=None)

    def test_accepts_explicit_key(self):
        c = PrintifyConnector(api_key='test-key-123')
        assert c.api_key == 'test-key-123'
        assert 'Bearer test-key-123' in c.headers['Authorization']

    def test_headers_include_content_type(self):
        c = PrintifyConnector(api_key='k')
        assert c.headers['Content-Type'] == 'application/json'


class TestPrintifyConnectorRequests:
    @pytest.fixture
    def connector(self):
        return PrintifyConnector(api_key='test-key')

    def _mock_response(self, json_data=None, status=200):
        resp = MagicMock()
        resp.status_code = status
        resp.content = json.dumps(json_data or {}).encode()
        resp.json.return_value = json_data or {}
        resp.raise_for_status.return_value = None
        return resp

    @patch('printify_connector.requests.request')
    def test_get_shops(self, mock_req, connector):
        mock_req.return_value = self._mock_response([{'id': 1, 'title': 'toxico'}])
        shops = connector.get_shops()
        mock_req.assert_called_once_with(
            'GET',
            'https://api.printify.com/v1/shops.json',
            headers=connector.headers,
            json=None,
            params=None,
            timeout=30
        )
        assert shops == [{'id': 1, 'title': 'toxico'}]

    @patch('printify_connector.requests.request')
    def test_get_blueprints(self, mock_req, connector):
        mock_req.return_value = self._mock_response([{'id': 77, 'title': 'Hoodie'}])
        bps = connector.get_blueprints()
        assert bps[0]['title'] == 'Hoodie'

    @patch('printify_connector.requests.request')
    def test_get_products(self, mock_req, connector):
        mock_req.return_value = self._mock_response([{'id': 'p1'}])
        prods = connector.get_products(shop_id=1)
        assert '/shops/1/products.json' in mock_req.call_args[0][1]

    @patch('printify_connector.requests.request')
    def test_create_product(self, mock_req, connector):
        mock_req.return_value = self._mock_response({'id': 'new-prod'})
        result = connector.create_product(shop_id=1, product_data={'title': 'test'})
        assert result['id'] == 'new-prod'
        assert mock_req.call_args[0][0] == 'POST'

    @patch('printify_connector.requests.request')
    def test_upload_image(self, mock_req, connector):
        mock_req.return_value = self._mock_response({'id': 'img-1'})
        result = connector.upload_image('logo.png', 'https://example.com/logo.png')
        call_data = mock_req.call_args[1]['json']
        assert call_data['file_name'] == 'logo.png'
        assert call_data['url'] == 'https://example.com/logo.png'

    @patch('printify_connector.requests.request')
    def test_delete_product(self, mock_req, connector):
        resp = MagicMock()
        resp.content = b''
        resp.raise_for_status.return_value = None
        mock_req.return_value = resp
        connector.delete_product(shop_id=1, product_id='p1')
        assert mock_req.call_args[0][0] == 'DELETE'

    @patch('printify_connector.requests.request')
    def test_calculate_shipping(self, mock_req, connector):
        mock_req.return_value = self._mock_response({'standard': 5.99})
        result = connector.calculate_shipping(shop_id=1, order_data={'line_items': []})
        assert mock_req.call_args[0][0] == 'POST'


class TestPrintifyConstants:
    def test_toxico_blueprints_has_required_products(self):
        assert 'hoodie_heavyweight' in TOXICO_BLUEPRINTS
        assert 'joggers' in TOXICO_BLUEPRINTS
        assert 'tshirt_premium' in TOXICO_BLUEPRINTS

    def test_preferred_providers_has_entries(self):
        assert len(PREFERRED_PROVIDERS) >= 2


# ===================================================================
# ShopifyConnector
# ===================================================================

class TestShopifyConnectorInit:
    def test_default_scopes(self):
        c = ShopifyConnector(shop_domain='test.myshopify.com')
        assert 'write_products' in c.scopes
        assert 'read_orders' in c.scopes

    def test_base_url(self):
        c = ShopifyConnector(shop_domain='test.myshopify.com')
        assert 'test.myshopify.com' in c.base_url
        assert c.API_VERSION in c.base_url

    def test_headers_include_access_token(self):
        c = ShopifyConnector(shop_domain='test.myshopify.com', access_token='shpat_xxx')
        assert c.headers['X-Shopify-Access-Token'] == 'shpat_xxx'


class TestShopifyOAuth:
    def test_get_auth_url_contains_required_params(self):
        c = ShopifyConnector(shop_domain='test.myshopify.com')
        url = c.get_auth_url('http://localhost/callback', state='abc123')
        assert 'client_id=' in url
        assert 'redirect_uri=' in url
        assert 'state=abc123' in url
        assert 'scope=' in url

    @patch('shopify_connector.requests.post')
    def test_exchange_token(self, mock_post):
        resp = MagicMock()
        resp.json.return_value = {'access_token': 'shpat_new', 'scope': 'read_products'}
        resp.raise_for_status.return_value = None
        mock_post.return_value = resp

        c = ShopifyConnector(shop_domain='test.myshopify.com')
        result = c.exchange_token('auth-code-123')
        assert result['access_token'] == 'shpat_new'
        assert c.access_token == 'shpat_new'


class TestShopifyWebhookVerification:
    def test_verify_webhook_with_valid_hmac(self):
        import hmac as hmac_mod, hashlib, base64
        c = ShopifyConnector(shop_domain='test.myshopify.com')
        data = b'{"test": true}'
        digest = hmac_mod.new(c.api_secret.encode(), data, hashlib.sha256).digest()
        valid_hmac = base64.b64encode(digest).decode()
        assert c.verify_webhook(data, valid_hmac) is True

    def test_verify_webhook_with_invalid_hmac(self):
        c = ShopifyConnector(shop_domain='test.myshopify.com')
        assert c.verify_webhook(b'data', 'invalid-hmac') is False


class TestShopifyConnectorAPI:
    @pytest.fixture
    def connector(self):
        return ShopifyConnector(shop_domain='test.myshopify.com', access_token='tok')

    def _mock_response(self, json_data=None, status=200):
        resp = MagicMock()
        resp.content = json.dumps(json_data or {}).encode()
        resp.json.return_value = json_data or {}
        resp.raise_for_status.return_value = None
        return resp

    @patch('shopify_connector.requests.request')
    def test_get_products(self, mock_req, connector):
        mock_req.return_value = self._mock_response({'products': [{'id': 1}]})
        prods = connector.get_products()
        assert prods == [{'id': 1}]

    @patch('shopify_connector.requests.request')
    def test_create_product(self, mock_req, connector):
        mock_req.return_value = self._mock_response({'product': {'id': 2, 'title': 'Hoodie'}})
        result = connector.create_product({'title': 'Hoodie'})
        assert result['title'] == 'Hoodie'
        assert mock_req.call_args[0][0] == 'POST'

    @patch('shopify_connector.requests.request')
    def test_get_orders(self, mock_req, connector):
        mock_req.return_value = self._mock_response({'orders': [{'id': 100}]})
        orders = connector.get_orders()
        assert len(orders) == 1

    @patch('shopify_connector.requests.request')
    def test_get_collections(self, mock_req, connector):
        mock_req.return_value = self._mock_response({'custom_collections': [{'id': 5}]})
        cols = connector.get_collections()
        assert cols[0]['id'] == 5

    @patch('shopify_connector.requests.request')
    def test_create_collection(self, mock_req, connector):
        mock_req.return_value = self._mock_response({'custom_collection': {'id': 6, 'title': 'Summer'}})
        result = connector.create_collection('Summer', products=[1, 2])
        assert result['title'] == 'Summer'


# ===================================================================
# ShopifyPrintifyBridge
# ===================================================================

class TestShopifyPrintifyBridge:
    def test_bridge_stores_connectors(self):
        shopify = MagicMock()
        printify = MagicMock()
        bridge = ShopifyPrintifyBridge(shopify, printify)
        assert bridge.shopify is shopify
        assert bridge.printify is printify

    def test_connect_printify_shop_finds_shopify_channel(self):
        shopify = MagicMock()
        printify = MagicMock()
        printify.get_shops.return_value = [
            {'id': 10, 'sales_channel': 'etsy'},
            {'id': 20, 'sales_channel': 'shopify'}
        ]
        bridge = ShopifyPrintifyBridge(shopify, printify)
        shop_id = bridge.connect_printify_shop()
        assert shop_id == 20

    def test_connect_printify_shop_raises_if_no_shopify(self):
        shopify = MagicMock()
        printify = MagicMock()
        printify.get_shops.return_value = [{'id': 10, 'sales_channel': 'etsy'}]
        bridge = ShopifyPrintifyBridge(shopify, printify)
        with pytest.raises(ValueError, match='No Shopify shop'):
            bridge.connect_printify_shop()


# ===================================================================
# NEW: PrintifyConnector — orders, webhooks, retry, pagination
# ===================================================================

class TestPrintifyOrders:
    @pytest.fixture
    def connector(self):
        return PrintifyConnector(api_key='test-key')

    def _mock_response(self, json_data=None, status=200):
        resp = MagicMock()
        resp.status_code = status
        resp.content = json.dumps(json_data or {}).encode()
        resp.json.return_value = json_data or {}
        resp.raise_for_status.return_value = None
        return resp

    @patch('printify_connector.requests.request')
    def test_create_order(self, mock_req, connector):
        mock_req.return_value = self._mock_response({'id': 'ord-1', 'status': 'pending'})
        order_data = {'external_id': '100', 'line_items': [{'product_id': 'p1', 'variant_id': 1, 'quantity': 1}]}
        result = connector.create_order(shop_id=1, order_data=order_data)
        assert result['id'] == 'ord-1'
        assert mock_req.call_args[0][0] == 'POST'
        assert '/shops/1/orders.json' in mock_req.call_args[0][1]

    @patch('printify_connector.requests.request')
    def test_cancel_order(self, mock_req, connector):
        mock_req.return_value = self._mock_response({'id': 'ord-1', 'status': 'canceled'})
        result = connector.cancel_order(shop_id=1, order_id='ord-1')
        assert result['status'] == 'canceled'
        assert '/cancel.json' in mock_req.call_args[0][1]

    @patch('printify_connector.requests.request')
    def test_update_product(self, mock_req, connector):
        mock_req.return_value = self._mock_response({'id': 'p1', 'title': 'Updated'})
        result = connector.update_product(shop_id=1, product_id='p1',
                                          product_data={'title': 'Updated'})
        assert result['title'] == 'Updated'
        assert mock_req.call_args[0][0] == 'PUT'

    @patch('printify_connector.requests.request')
    def test_unpublish_product(self, mock_req, connector):
        mock_req.return_value = self._mock_response({})
        connector.unpublish_product(shop_id=1, product_id='p1')
        assert '/unpublish.json' in mock_req.call_args[0][1]


class TestPrintifyWebhooks:
    @pytest.fixture
    def connector(self):
        return PrintifyConnector(api_key='test-key')

    def _mock_response(self, json_data=None, status=200):
        resp = MagicMock()
        resp.status_code = status
        resp.content = json.dumps(json_data or {}).encode()
        resp.json.return_value = json_data or {}
        resp.raise_for_status.return_value = None
        return resp

    @patch('printify_connector.requests.request')
    def test_get_webhooks(self, mock_req, connector):
        mock_req.return_value = self._mock_response([{'id': 'wh1', 'topic': 'order:created'}])
        hooks = connector.get_webhooks(shop_id=1)
        assert len(hooks) == 1
        assert hooks[0]['topic'] == 'order:created'

    @patch('printify_connector.requests.request')
    def test_create_webhook(self, mock_req, connector):
        mock_req.return_value = self._mock_response({'id': 'wh2', 'topic': 'order:completed'})
        result = connector.create_webhook(shop_id=1, topic='order:completed',
                                          url='https://example.com/hook')
        assert result['topic'] == 'order:completed'
        call_data = mock_req.call_args[1]['json']
        assert call_data['topic'] == 'order:completed'
        assert call_data['url'] == 'https://example.com/hook'

    @patch('printify_connector.requests.request')
    def test_delete_webhook(self, mock_req, connector):
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b''
        resp.raise_for_status.return_value = None
        mock_req.return_value = resp
        connector.delete_webhook(shop_id=1, webhook_id='wh1')
        assert mock_req.call_args[0][0] == 'DELETE'
        assert '/webhooks/wh1.json' in mock_req.call_args[0][1]

    @patch('printify_connector.requests.request')
    def test_ensure_webhooks_creates_missing(self, mock_req, connector):
        # First call: get_webhooks returns one existing
        existing = [{'id': 'wh1', 'topic': 'order:created'}]
        new_hook = {'id': 'wh-new', 'topic': 'order:completed'}
        mock_req.side_effect = [
            self._mock_response(existing),  # get_webhooks
        ] + [self._mock_response(new_hook)] * 10  # create_webhook calls

        result = connector.ensure_webhooks(shop_id=1, base_url='https://example.com')
        # Should have created hooks for all required topics minus the existing one
        assert len(result) >= 2  # at least existing + 1 new


class TestPrintifyRetryAndPagination:
    def _mock_response(self, json_data=None, status=200, headers=None):
        resp = MagicMock()
        resp.status_code = status
        resp.content = json.dumps(json_data or {}).encode()
        resp.json.return_value = json_data or {}
        resp.raise_for_status.return_value = None
        resp.headers = headers or {}
        return resp

    @patch('printify_connector.time.sleep')
    @patch('printify_connector.requests.request')
    def test_retry_on_429(self, mock_req, mock_sleep):
        connector = PrintifyConnector(api_key='test-key')
        rate_resp = self._mock_response(status=429, headers={'Retry-After': '0.01'})
        rate_resp.raise_for_status.side_effect = None
        ok_resp = self._mock_response([{'id': 1}])
        mock_req.side_effect = [rate_resp, ok_resp]
        result = connector._request('GET', '/shops.json')
        assert result == [{'id': 1}]
        assert mock_req.call_count == 2

    @patch('printify_connector.requests.request')
    def test_paginate_single_page(self, mock_req):
        connector = PrintifyConnector(api_key='test-key')
        page_data = {'data': [{'id': 'p1'}, {'id': 'p2'}], 'last_page': 1}
        mock_req.return_value = self._mock_response(page_data)
        result = connector._paginate('/shops/1/products.json')
        assert len(result) == 2

    @patch('printify_connector.requests.request')
    def test_paginate_list_endpoint(self, mock_req):
        connector = PrintifyConnector(api_key='test-key')
        mock_req.return_value = self._mock_response([{'id': 1}, {'id': 2}])
        result = connector._paginate('/shops.json')
        assert len(result) == 2


# ===================================================================
# NEW: ShopifyConnector — webhooks, tokens, pagination, API version
# ===================================================================

class TestShopifyAPIVersion:
    def test_api_version_is_2025(self):
        c = ShopifyConnector(shop_domain='test.myshopify.com')
        assert c.API_VERSION == '2025-01'
        assert '2025-01' in c.base_url


class TestShopifyWebhookRegistration:
    @pytest.fixture
    def connector(self):
        return ShopifyConnector(shop_domain='test.myshopify.com', access_token='tok')

    def _mock_response(self, json_data=None, status=200):
        resp = MagicMock()
        resp.status_code = status
        resp.content = json.dumps(json_data or {}).encode()
        resp.json.return_value = json_data or {}
        resp.raise_for_status.return_value = None
        return resp

    @patch('shopify_connector.requests.request')
    def test_register_webhook(self, mock_req, connector):
        mock_req.return_value = self._mock_response(
            {'webhook': {'id': 1, 'topic': 'orders/create'}})
        result = connector.register_webhook('orders/create', 'https://ex.com/hook')
        assert result['topic'] == 'orders/create'

    @patch('shopify_connector.requests.request')
    def test_list_webhooks(self, mock_req, connector):
        mock_req.return_value = self._mock_response(
            {'webhooks': [{'id': 1, 'topic': 'orders/create'}]})
        hooks = connector.list_webhooks()
        assert len(hooks) == 1

    @patch('shopify_connector.requests.request')
    def test_delete_webhook(self, mock_req, connector):
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b''
        resp.raise_for_status.return_value = None
        mock_req.return_value = resp
        connector.delete_webhook(webhook_id=1)
        assert mock_req.call_args[0][0] == 'DELETE'

    @patch('shopify_connector.requests.request')
    def test_ensure_webhooks_idempotent(self, mock_req, connector):
        existing = {'webhooks': [{'id': 1, 'topic': 'orders/create',
                                  'address': 'https://ex.com/hook'}]}
        new_hook = {'webhook': {'id': 2, 'topic': 'orders/updated'}}
        mock_req.side_effect = [
            self._mock_response(existing),  # list_webhooks
        ] + [self._mock_response(new_hook)] * 10  # register calls
        result = connector.ensure_webhooks('https://ex.com')
        assert len(result) >= 2


class TestShopifyTokenPersistence:
    def test_save_and_load_token(self, tmp_path):
        token_file = str(tmp_path / 'tokens.json')
        c = ShopifyConnector(shop_domain='test.myshopify.com', access_token='shpat_test')
        # Temporarily override TOKEN_FILE
        original = ShopifyConnector.TOKEN_FILE
        ShopifyConnector.TOKEN_FILE = token_file
        try:
            c.save_token()
            loaded = ShopifyConnector.load_token('test.myshopify.com')
            assert loaded is not None
            assert loaded.access_token == 'shpat_test'
            assert loaded.shop_domain == 'test.myshopify.com'
        finally:
            ShopifyConnector.TOKEN_FILE = original

    def test_load_token_returns_none_for_unknown(self, tmp_path):
        token_file = str(tmp_path / 'tokens.json')
        original = ShopifyConnector.TOKEN_FILE
        ShopifyConnector.TOKEN_FILE = token_file
        try:
            result = ShopifyConnector.load_token('unknown.myshopify.com')
            assert result is None
        finally:
            ShopifyConnector.TOKEN_FILE = original


class TestShopifyRetryAndPagination:
    def _mock_response(self, json_data=None, status=200, headers=None):
        resp = MagicMock()
        resp.status_code = status
        resp.content = json.dumps(json_data or {}).encode()
        resp.json.return_value = json_data or {}
        resp.raise_for_status.return_value = None
        resp.headers = headers or {}
        return resp

    @patch('shopify_connector.time.sleep')
    @patch('shopify_connector.requests.request')
    def test_retry_on_429(self, mock_req, mock_sleep):
        c = ShopifyConnector(shop_domain='t.myshopify.com', access_token='tok')
        rate_resp = self._mock_response(status=429, headers={'Retry-After': '0.01'})
        ok_resp = self._mock_response({'products': [{'id': 1}]})
        mock_req.side_effect = [rate_resp, ok_resp]
        result = c._request('GET', '/products.json')
        assert result['products'] == [{'id': 1}]

    @patch('shopify_connector.requests.get')
    def test_get_all_products_pagination(self, mock_get):
        c = ShopifyConnector(shop_domain='t.myshopify.com', access_token='tok')
        page1 = MagicMock()
        page1.status_code = 200
        page1.json.return_value = {'products': [{'id': 1}]}
        page1.headers = {'Link': '<https://t.myshopify.com/next>; rel="next"'}
        page1.raise_for_status.return_value = None

        page2 = MagicMock()
        page2.status_code = 200
        page2.json.return_value = {'products': [{'id': 2}]}
        page2.headers = {}
        page2.raise_for_status.return_value = None

        mock_get.side_effect = [page1, page2]
        prods = c.get_all_products()
        assert len(prods) == 2
        assert prods[0]['id'] == 1
        assert prods[1]['id'] == 2


# ===================================================================
# NEW: Bridge — order creation, fulfillment, cancellation
# ===================================================================

class TestBridgeOrderCreation:
    def test_handle_order_webhook_calls_create_order(self):
        shopify_mock = MagicMock()
        printify_mock = MagicMock()
        printify_mock.create_order.return_value = {'id': 'printify-ord-1'}
        bridge = ShopifyPrintifyBridge(shopify_mock, printify_mock)
        bridge.shop_id = 42

        order = {
            'id': 999,
            'email': 'test@test.com',
            'line_items': [{'sku': 'PRFY_prod1_12345', 'quantity': 2}],
            'shipping_address': {
                'first_name': 'Test', 'last_name': 'User',
                'address1': '123 Main', 'city': 'NYC',
                'province_code': 'NY', 'country_code': 'US',
                'zip': '10001'
            }
        }
        result = bridge.handle_order_webhook(order)
        assert result['status'] == 'created'
        printify_mock.create_order.assert_called_once()

    def test_handle_order_webhook_skips_non_printify(self):
        shopify_mock = MagicMock()
        printify_mock = MagicMock()
        bridge = ShopifyPrintifyBridge(shopify_mock, printify_mock)
        bridge.shop_id = 42

        order = {'id': 100, 'line_items': [{'sku': 'MANUAL-123', 'quantity': 1}],
                 'shipping_address': {}}
        result = bridge.handle_order_webhook(order)
        assert result['status'] == 'skipped'
        printify_mock.create_order.assert_not_called()


class TestBridgeFulfillment:
    def test_handle_fulfillment_update(self):
        shopify_mock = MagicMock()
        shopify_mock.fulfill_order.return_value = {'id': 1}
        printify_mock = MagicMock()
        bridge = ShopifyPrintifyBridge(shopify_mock, printify_mock)

        event = {
            'resource': {
                'external_id': '999',
                'shipments': [{'tracking_number': 'TRK123', 'carrier': 'USPS'}]
            }
        }
        result = bridge.handle_fulfillment_update(event)
        assert result['status'] == 'fulfilled'
        shopify_mock.fulfill_order.assert_called_once()

    def test_handle_fulfillment_skips_without_shipments(self):
        shopify_mock = MagicMock()
        printify_mock = MagicMock()
        bridge = ShopifyPrintifyBridge(shopify_mock, printify_mock)
        result = bridge.handle_fulfillment_update({'resource': {}})
        assert result['status'] == 'skipped'


class TestBridgeCancellation:
    def test_handle_order_cancelled(self):
        shopify_mock = MagicMock()
        printify_mock = MagicMock()
        printify_mock.get_orders.return_value = [
            {'id': 'p-ord-1', 'external_id': '999'}
        ]
        printify_mock.cancel_order.return_value = {}
        bridge = ShopifyPrintifyBridge(shopify_mock, printify_mock)
        bridge.shop_id = 42

        result = bridge.handle_order_cancelled({'id': 999})
        assert result['status'] == 'cancelled'
        printify_mock.cancel_order.assert_called_once_with(42, 'p-ord-1')

    def test_handle_order_cancelled_skips_unknown(self):
        shopify_mock = MagicMock()
        printify_mock = MagicMock()
        printify_mock.get_orders.return_value = []
        bridge = ShopifyPrintifyBridge(shopify_mock, printify_mock)
        bridge.shop_id = 42

        result = bridge.handle_order_cancelled({'id': 000})
        assert result['status'] == 'skipped'
