"""
Printify API Connector for iamtoxico
Connects Shopify store to Printify for POD fulfillment
Full-featured: shops, catalog, products, orders, images, webhooks,
pagination, rate-limit retry.
"""

import os
import time
import requests
from typing import Optional, Dict, List, Any

class PrintifyConnector:
    BASE_URL = "https://api.printify.com/v1"
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PRINTIFY_API_KEY")
        if not self.api_key:
            raise ValueError("PRINTIFY_API_KEY required. Get from https://printify.com/app/account/api")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    # ------------------------------------------------------------------
    # Core HTTP with retry / rate-limit back-off
    # ------------------------------------------------------------------

    def _request(self, method: str, endpoint: str, data: dict = None,
                 params: dict = None) -> Any:
        """Make authenticated request with automatic retry on 429/5xx."""
        url = f"{self.BASE_URL}{endpoint}"
        last_exc = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                resp = requests.request(
                    method, url, headers=self.headers,
                    json=data, params=params, timeout=30,
                )
                if resp.status_code == 429:
                    retry_after = float(
                        resp.headers.get("Retry-After", self.RETRY_DELAY * attempt)
                    )
                    time.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return resp.json() if resp.content else {}
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * attempt)
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Pagination helper
    # ------------------------------------------------------------------

    def _paginate(self, endpoint: str, key: str = "data") -> List[dict]:
        """Fetch all pages from a paginated endpoint."""
        results: List[dict] = []
        page = 1
        while True:
            data = self._request("GET", endpoint, params={"page": page, "limit": 100})
            if isinstance(data, list):
                results.extend(data)
                break  # non-paginated list endpoint
            items = data.get(key, data.get("data", []))
            results.extend(items)
            last_page = data.get("last_page", 1)
            if page >= last_page:
                break
            page += 1
        return results
    
    # ============ SHOP MANAGEMENT ============
    
    def get_shops(self) -> List[dict]:
        """List all connected shops"""
        return self._request("GET", "/shops.json")
    
    def get_shop(self, shop_id: int) -> dict:
        """Get specific shop details"""
        return self._request("GET", f"/shops/{shop_id}.json")
    
    # ============ CATALOG ============
    
    def get_blueprints(self) -> List[dict]:
        """Get all available product blueprints (t-shirts, hoodies, etc.)"""
        return self._request("GET", "/catalog/blueprints.json")
    
    def get_blueprint(self, blueprint_id: int) -> dict:
        """Get specific blueprint details"""
        return self._request("GET", f"/catalog/blueprints/{blueprint_id}.json")
    
    def get_print_providers(self, blueprint_id: int) -> List[dict]:
        """Get print providers for a blueprint"""
        return self._request("GET", f"/catalog/blueprints/{blueprint_id}/print_providers.json")
    
    def get_variants(self, blueprint_id: int, print_provider_id: int) -> dict:
        """Get available variants (sizes, colors) for blueprint + provider"""
        return self._request("GET", f"/catalog/blueprints/{blueprint_id}/print_providers/{print_provider_id}/variants.json")
    
    # ============ PRODUCTS ============
    
    def get_products(self, shop_id: int) -> List[dict]:
        """List all products in a shop (paginated)."""
        return self._paginate(f"/shops/{shop_id}/products.json")
    
    def get_product(self, shop_id: int, product_id: str) -> dict:
        """Get specific product"""
        return self._request("GET", f"/shops/{shop_id}/products/{product_id}.json")
    
    def create_product(self, shop_id: int, product_data: dict) -> dict:
        """Create a new product"""
        return self._request("POST", f"/shops/{shop_id}/products.json", product_data)

    def update_product(self, shop_id: int, product_id: str, product_data: dict) -> dict:
        """Update an existing product."""
        return self._request("PUT", f"/shops/{shop_id}/products/{product_id}.json", product_data)

    def publish_product(self, shop_id: int, product_id: str, publish_data: dict) -> dict:
        """Publish product to connected store (Shopify)"""
        return self._request("POST", f"/shops/{shop_id}/products/{product_id}/publish.json", publish_data)

    def unpublish_product(self, shop_id: int, product_id: str) -> dict:
        """Unpublish product from connected store."""
        return self._request("POST", f"/shops/{shop_id}/products/{product_id}/unpublish.json")
    
    def delete_product(self, shop_id: int, product_id: str) -> dict:
        """Delete a product"""
        return self._request("DELETE", f"/shops/{shop_id}/products/{product_id}.json")
    
    # ============ IMAGES ============
    
    def upload_image(self, file_name: str, image_url: str) -> dict:
        """Upload image from URL"""
        data = {
            "file_name": file_name,
            "url": image_url
        }
        return self._request("POST", "/uploads/images.json", data)
    
    def get_uploaded_images(self) -> List[dict]:
        """List all uploaded images"""
        return self._request("GET", "/uploads.json")
    
    # ============ ORDERS ============
    
    def get_orders(self, shop_id: int) -> List[dict]:
        """List all orders (paginated)."""
        return self._paginate(f"/shops/{shop_id}/orders.json")

    def get_order(self, shop_id: int, order_id: str) -> dict:
        """Get specific order"""
        return self._request("GET", f"/shops/{shop_id}/orders/{order_id}.json")

    def create_order(self, shop_id: int, order_data: dict) -> dict:
        """Create a new order for production."""
        return self._request("POST", f"/shops/{shop_id}/orders.json", order_data)

    def submit_order(self, shop_id: int, order_id: str) -> dict:
        """Submit order for production"""
        return self._request("POST", f"/shops/{shop_id}/orders/{order_id}/send_to_production.json")

    def cancel_order(self, shop_id: int, order_id: str) -> dict:
        """Cancel an order."""
        return self._request("POST", f"/shops/{shop_id}/orders/{order_id}/cancel.json")

    def calculate_shipping(self, shop_id: int, order_data: dict) -> dict:
        """Calculate shipping costs"""
        return self._request("POST", f"/shops/{shop_id}/orders/shipping.json", order_data)

    # ============ WEBHOOKS ============

    def get_webhooks(self, shop_id: int) -> List[dict]:
        """List registered webhooks."""
        return self._request("GET", f"/shops/{shop_id}/webhooks.json")

    def create_webhook(self, shop_id: int, topic: str, url: str) -> dict:
        """Register a webhook.

        Topics:
            order:created, order:updated, order:sent-to-production,
            order:shipping-update, order:completed,
            product:publish:started, product:publish:succeeded,
            product:publish:failed, product:deleted
        """
        return self._request("POST", f"/shops/{shop_id}/webhooks.json", {
            "topic": topic,
            "url": url,
        })

    def delete_webhook(self, shop_id: int, webhook_id: str) -> dict:
        """Delete a webhook."""
        return self._request("DELETE", f"/shops/{shop_id}/webhooks/{webhook_id}.json")

    def ensure_webhooks(self, shop_id: int, base_url: str) -> List[dict]:
        """Ensure all required webhooks are registered (idempotent).

        Returns list of created/existing webhook records.
        """
        required_topics = [
            "order:created",
            "order:updated",
            "order:sent-to-production",
            "order:shipping-update",
            "order:completed",
            "product:publish:started",
            "product:publish:succeeded",
            "product:publish:failed",
        ]
        existing = self.get_webhooks(shop_id)
        existing_topics = {w.get("topic") for w in existing}
        results = list(existing)
        for topic in required_topics:
            if topic not in existing_topics:
                hook_url = f"{base_url}/printify/webhooks"
                wh = self.create_webhook(shop_id, topic, hook_url)
                results.append(wh)
        return results


# ============ TOXICO PRODUCT TEMPLATES ============

# Blueprint IDs for common products (from Printify catalog)
TOXICO_BLUEPRINTS = {
    "hoodie_heavyweight": 77,      # Unisex Heavy Blend Hoodie (Gildan 18500)
    "hoodie_premium": 468,         # Premium Hoodie (Bella+Canvas 3719)
    "joggers": 1119,               # Unisex Joggers
    "tshirt_premium": 145,         # Unisex Premium T-Shirt
    "sweatshirt": 380,             # Unisex Crewneck Sweatshirt
}

# Preferred print providers (US-based, fast shipping)
PREFERRED_PROVIDERS = {
    "monster_digital": 99,         # Monster Digital - quality, fast
    "awkward_styles": 28,          # Awkward Styles - good hoodies
    "drive_fulfillment": 211,      # Drive Fulfillment - premium
}


def create_toxico_hoodie(connector: PrintifyConnector, shop_id: int, 
                         design_url: str, title: str, description: str) -> dict:
    """
    Create a toxico-branded hoodie
    
    Example:
        connector = PrintifyConnector()
        shops = connector.get_shops()
        shop_id = shops[0]['id']
        
        product = create_toxico_hoodie(
            connector, shop_id,
            design_url="https://example.com/toxico-logo.png",
            title="toxico Heavyweight Hoodie",
            description="Premium comfort, minimal branding"
        )
    """
    
    # Upload design image
    image = connector.upload_image("toxico-design.png", design_url)
    
    product_data = {
        "title": title,
        "description": description,
        "blueprint_id": TOXICO_BLUEPRINTS["hoodie_heavyweight"],
        "print_provider_id": PREFERRED_PROVIDERS["monster_digital"],
        "variants": [
            # Add variants (sizes/colors) - get from get_variants()
            {"id": 71867, "price": 9500, "is_enabled": True},  # Black / S
            {"id": 71868, "price": 9500, "is_enabled": True},  # Black / M
            {"id": 71869, "price": 9500, "is_enabled": True},  # Black / L
            {"id": 71870, "price": 9500, "is_enabled": True},  # Black / XL
            {"id": 71871, "price": 9500, "is_enabled": True},  # Black / 2XL
        ],
        "print_areas": [
            {
                "variant_ids": [71867, 71868, 71869, 71870, 71871],
                "placeholders": [
                    {
                        "position": "back",  # Small back neck label
                        "images": [
                            {
                                "id": image["id"],
                                "x": 0.4,
                                "y": 0.05,
                                "scale": 0.15,
                                "angle": 0
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    return connector.create_product(shop_id, product_data)


if __name__ == "__main__":
    import sys

    api_key = os.getenv("PRINTIFY_API_KEY")
    if not api_key:
        print("❌ PRINTIFY_API_KEY not set")
        sys.exit(1)
    try:
        c = PrintifyConnector(api_key)
        shops = c.get_shops()
        print(f"✓ Connected — {len(shops)} shop(s)")
        for s in shops:
            print(f"  • {s['title']} (ID: {s['id']})")
            hooks = c.get_webhooks(s["id"])
            print(f"    Webhooks: {len(hooks)}")
    except Exception as e:
        print(f"❌ {e}")
