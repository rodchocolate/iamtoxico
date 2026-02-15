"""
Printify API Connector for iamtoxico
Connects Shopify store to Printify for POD fulfillment
"""

import os
import requests
from typing import Optional, Dict, List

class PrintifyConnector:
    BASE_URL = "https://api.printify.com/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PRINTIFY_API_KEY")
        if not self.api_key:
            raise ValueError("PRINTIFY_API_KEY required. Get from https://printify.com/app/account/api")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make authenticated request to Printify API"""
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.request(method, url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json() if response.content else {}
    
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
        """List all products in a shop"""
        return self._request("GET", f"/shops/{shop_id}/products.json")
    
    def get_product(self, shop_id: int, product_id: str) -> dict:
        """Get specific product"""
        return self._request("GET", f"/shops/{shop_id}/products/{product_id}.json")
    
    def create_product(self, shop_id: int, product_data: dict) -> dict:
        """Create a new product"""
        return self._request("POST", f"/shops/{shop_id}/products.json", product_data)
    
    def publish_product(self, shop_id: int, product_id: str, publish_data: dict) -> dict:
        """Publish product to connected store (Shopify)"""
        return self._request("POST", f"/shops/{shop_id}/products/{product_id}/publish.json", publish_data)
    
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
        """List all orders"""
        return self._request("GET", f"/shops/{shop_id}/orders.json")
    
    def get_order(self, shop_id: int, order_id: str) -> dict:
        """Get specific order"""
        return self._request("GET", f"/shops/{shop_id}/orders/{order_id}.json")
    
    def submit_order(self, shop_id: int, order_id: str) -> dict:
        """Submit order for production"""
        return self._request("POST", f"/shops/{shop_id}/orders/{order_id}/send_to_production.json")
    
    def calculate_shipping(self, shop_id: int, order_data: dict) -> dict:
        """Calculate shipping costs"""
        return self._request("POST", f"/shops/{shop_id}/orders/shipping.json", order_data)


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
    # Quick test
    import sys
    
    api_key = os.getenv("PRINTIFY_API_KEY")
    if not api_key:
        print("❌ PRINTIFY_API_KEY not set")
        print("   Get your key from: https://printify.com/app/account/api")
        print("   Then: export PRINTIFY_API_KEY=your_key_here")
        sys.exit(1)
    
    try:
        connector = PrintifyConnector(api_key)
        shops = connector.get_shops()
        
        print("✓ Connected to Printify!")
        print(f"  Shops: {len(shops)}")
        for shop in shops:
            print(f"    - {shop['title']} (ID: {shop['id']})")
        
        # Show some blueprints
        blueprints = connector.get_blueprints()
        print(f"\n  Available blueprints: {len(blueprints)}")
        for bp in blueprints[:5]:
            print(f"    - {bp['title']} (ID: {bp['id']})")
        
    except Exception as e:
        print(f"❌ Error: {e}")
