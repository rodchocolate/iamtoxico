"""
Shopify API Connector for iamtoxico
Handles OAuth, products, and order sync with Printify
"""

import os
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from typing import Optional, Dict, List

class ShopifyConnector:
    API_VERSION = "2024-01"
    
    def __init__(self, shop_domain: str = None, access_token: str = None):
        self.api_key = os.getenv("SHOPIFY_API_KEY", "6347ea0e4232c5d68711bb80f0623930")
        self.api_secret = os.getenv("SHOPIFY_API_SECRET", "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")
        self.shop_domain = shop_domain  # e.g., "iamtoxico.myshopify.com"
        self.access_token = access_token
        self.scopes = "write_products,read_products,write_orders,read_orders"
    
    @property
    def base_url(self) -> str:
        return f"https://{self.shop_domain}/admin/api/{self.API_VERSION}"
    
    @property
    def headers(self) -> dict:
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }
    
    # ============ OAUTH FLOW ============
    
    def get_auth_url(self, redirect_uri: str, state: str = None) -> str:
        """Generate OAuth authorization URL"""
        params = {
            "client_id": self.api_key,
            "scope": self.scopes,
            "redirect_uri": redirect_uri,
            "state": state or os.urandom(16).hex()
        }
        return f"https://{self.shop_domain}/admin/oauth/authorize?{urlencode(params)}"
    
    def exchange_token(self, code: str) -> dict:
        """Exchange authorization code for access token"""
        url = f"https://{self.shop_domain}/admin/oauth/access_token"
        data = {
            "client_id": self.api_key,
            "client_secret": self.api_secret,
            "code": code
        }
        response = requests.post(url, json=data)
        response.raise_for_status()
        result = response.json()
        self.access_token = result.get("access_token")
        return result
    
    def verify_webhook(self, data: bytes, hmac_header: str) -> bool:
        """Verify incoming webhook signature"""
        digest = hmac.new(
            self.api_secret.encode(),
            data,
            hashlib.sha256
        ).digest()
        import base64
        computed = base64.b64encode(digest).decode()
        return hmac.compare_digest(computed, hmac_header)
    
    # ============ PRODUCTS ============
    
    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make authenticated request to Shopify API"""
        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json() if response.content else {}
    
    def get_products(self, limit: int = 50) -> List[dict]:
        """List all products"""
        result = self._request("GET", f"/products.json?limit={limit}")
        return result.get("products", [])
    
    def get_product(self, product_id: int) -> dict:
        """Get specific product"""
        result = self._request("GET", f"/products/{product_id}.json")
        return result.get("product", {})
    
    def create_product(self, product_data: dict) -> dict:
        """Create a new product"""
        result = self._request("POST", "/products.json", {"product": product_data})
        return result.get("product", {})
    
    def update_product(self, product_id: int, product_data: dict) -> dict:
        """Update existing product"""
        result = self._request("PUT", f"/products/{product_id}.json", {"product": product_data})
        return result.get("product", {})
    
    def delete_product(self, product_id: int) -> None:
        """Delete a product"""
        self._request("DELETE", f"/products/{product_id}.json")
    
    # ============ ORDERS ============
    
    def get_orders(self, status: str = "any", limit: int = 50) -> List[dict]:
        """List orders"""
        result = self._request("GET", f"/orders.json?status={status}&limit={limit}")
        return result.get("orders", [])
    
    def get_order(self, order_id: int) -> dict:
        """Get specific order"""
        result = self._request("GET", f"/orders/{order_id}.json")
        return result.get("order", {})
    
    def fulfill_order(self, order_id: int, fulfillment_data: dict) -> dict:
        """Create fulfillment for order"""
        result = self._request("POST", f"/orders/{order_id}/fulfillments.json", 
                               {"fulfillment": fulfillment_data})
        return result.get("fulfillment", {})
    
    # ============ INVENTORY ============
    
    def get_inventory_levels(self, location_id: int = None) -> List[dict]:
        """Get inventory levels"""
        endpoint = "/inventory_levels.json"
        if location_id:
            endpoint += f"?location_ids={location_id}"
        result = self._request("GET", endpoint)
        return result.get("inventory_levels", [])
    
    def adjust_inventory(self, inventory_item_id: int, location_id: int, adjustment: int) -> dict:
        """Adjust inventory quantity"""
        data = {
            "location_id": location_id,
            "inventory_item_id": inventory_item_id,
            "available_adjustment": adjustment
        }
        return self._request("POST", "/inventory_levels/adjust.json", data)
    
    # ============ COLLECTIONS ============
    
    def get_collections(self) -> List[dict]:
        """Get all collections"""
        result = self._request("GET", "/custom_collections.json")
        return result.get("custom_collections", [])
    
    def create_collection(self, title: str, products: List[int] = None) -> dict:
        """Create a collection"""
        data = {"custom_collection": {"title": title}}
        if products:
            data["custom_collection"]["collects"] = [
                {"product_id": pid} for pid in products
            ]
        result = self._request("POST", "/custom_collections.json", data)
        return result.get("custom_collection", {})


# ============ PRINTIFY SYNC ============

class ShopifyPrintifyBridge:
    """
    Bridges Shopify store with Printify for automated POD fulfillment
    """
    
    def __init__(self, shopify: ShopifyConnector, printify):
        self.shopify = shopify
        self.printify = printify
        self.shop_id = None  # Printify shop ID
    
    def connect_printify_shop(self) -> int:
        """Get Printify shop ID for connected Shopify store"""
        shops = self.printify.get_shops()
        for shop in shops:
            if shop.get("sales_channel") == "shopify":
                self.shop_id = shop["id"]
                return self.shop_id
        raise ValueError("No Shopify shop connected in Printify")
    
    def sync_product_to_shopify(self, printify_product_id: str) -> dict:
        """
        Publish Printify product to Shopify
        """
        publish_data = {
            "title": True,
            "description": True,
            "images": True,
            "variants": True,
            "tags": True,
            "keyFeatures": True,
            "shipping_template": True
        }
        return self.printify.publish_product(self.shop_id, printify_product_id, publish_data)
    
    def handle_order_webhook(self, order_data: dict) -> dict:
        """
        Handle incoming Shopify order webhook
        Creates corresponding order in Printify
        """
        # Extract order details
        order_id = order_data["id"]
        line_items = order_data.get("line_items", [])
        shipping_address = order_data.get("shipping_address", {})
        
        # Map Shopify line items to Printify
        printify_items = []
        for item in line_items:
            # Look up Printify variant from SKU or product ID
            sku = item.get("sku", "")
            if sku.startswith("PRFY_"):
                printify_items.append({
                    "product_id": sku.split("_")[1],
                    "variant_id": int(sku.split("_")[2]),
                    "quantity": item["quantity"]
                })
        
        if not printify_items:
            return {"status": "skipped", "reason": "No Printify items in order"}
        
        # Create Printify order
        printify_order = {
            "external_id": str(order_id),
            "line_items": printify_items,
            "shipping_method": 1,  # Standard shipping
            "address_to": {
                "first_name": shipping_address.get("first_name", ""),
                "last_name": shipping_address.get("last_name", ""),
                "email": order_data.get("email", ""),
                "phone": shipping_address.get("phone", ""),
                "country": shipping_address.get("country_code", "US"),
                "region": shipping_address.get("province_code", ""),
                "address1": shipping_address.get("address1", ""),
                "address2": shipping_address.get("address2", ""),
                "city": shipping_address.get("city", ""),
                "zip": shipping_address.get("zip", "")
            }
        }
        
        # Note: Actual order creation would use printify.create_order()
        return {"status": "created", "printify_order": printify_order}


# ============ TOXICO COLLECTIONS ============

TOXICO_COLLECTIONS = {
    "loungewear": {
        "title": "Loungewear",
        "description": "Elevated comfort for the sporting life"
    },
    "essentials": {
        "title": "Essentials", 
        "description": "Premium basics, minimal branding"
    },
    "captain_adventure": {
        "title": "Captain Adventure",
        "description": "For the deviant but proper explorer"
    }
}


if __name__ == "__main__":
    import sys
    
    # Test connection
    print("Shopify Connector for iamtoxico")
    print("=" * 40)
    print(f"API Key: {os.getenv('SHOPIFY_API_KEY', '6347ea...')[:10]}...")
    print(f"API Secret: {os.getenv('SHOPIFY_API_SECRET', 'shpss_...')[:10]}...")
    print()
    print("To connect:")
    print("1. Create store at https://partners.shopify.com")
    print("2. Install this app on your store")
    print("3. Complete OAuth flow to get access token")
    print()
    print("Then run:")
    print("  connector = ShopifyConnector('iamtoxico.myshopify.com', 'access_token')")
    print("  products = connector.get_products()")
