"""
Shopify OAuth & Webhook Handler for iamtoxico
Run this alongside the main valet server
"""

import os
from flask import Flask, request, redirect, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment
load_dotenv()

from shopify_connector import ShopifyConnector, ShopifyPrintifyBridge
from printify_connector import PrintifyConnector

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

# Connectors (initialized on first use)
shopify = None
printify = None
bridge = None


@app.route("/")
def home():
    return jsonify({
        "app": "iamtoxico Shopify Integration",
        "status": "running",
        "endpoints": {
            "install": "/shopify/install?shop=YOUR_SHOP.myshopify.com",
            "callback": "/shopify/callback",
            "webhooks": "/shopify/webhooks/orders"
        }
    })


# ============ SHOPIFY OAUTH ============

@app.route("/shopify/install")
def shopify_install():
    """Start OAuth flow - redirect merchant to Shopify authorization"""
    shop = request.args.get("shop")
    if not shop:
        return jsonify({"error": "Missing shop parameter"}), 400
    
    if not shop.endswith(".myshopify.com"):
        shop = f"{shop}.myshopify.com"
    
    connector = ShopifyConnector(shop_domain=shop)
    
    # Generate state for CSRF protection
    state = os.urandom(16).hex()
    session["oauth_state"] = state
    session["shop"] = shop
    
    # Build redirect URL
    redirect_uri = f"{os.getenv('HOST', 'http://localhost:5001')}/shopify/callback"
    auth_url = connector.get_auth_url(redirect_uri, state)
    
    return redirect(auth_url)


@app.route("/shopify/callback")
def shopify_callback():
    """Handle OAuth callback from Shopify"""
    global shopify
    
    # Verify state
    state = request.args.get("state")
    if state != session.get("oauth_state"):
        return jsonify({"error": "Invalid state parameter"}), 403
    
    shop = session.get("shop")
    code = request.args.get("code")
    
    if not shop or not code:
        return jsonify({"error": "Missing shop or code"}), 400
    
    # Exchange code for access token
    connector = ShopifyConnector(shop_domain=shop)
    try:
        token_data = connector.exchange_token(code)
        access_token = token_data.get("access_token")
        
        # Store token securely (in production, use database/vault)
        session["access_token"] = access_token
        session["shop"] = shop
        
        # Initialize global connector
        shopify = ShopifyConnector(shop_domain=shop, access_token=access_token)
        
        return jsonify({
            "status": "connected",
            "shop": shop,
            "scope": token_data.get("scope"),
            "message": "Successfully connected to Shopify!"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============ SHOPIFY WEBHOOKS ============

@app.route("/shopify/webhooks/orders", methods=["POST"])
def webhook_orders():
    """Handle order creation webhook from Shopify"""
    global bridge
    
    # Verify webhook signature
    hmac_header = request.headers.get("X-Shopify-Hmac-SHA256", "")
    if shopify and not shopify.verify_webhook(request.data, hmac_header):
        return jsonify({"error": "Invalid signature"}), 401
    
    order_data = request.json
    topic = request.headers.get("X-Shopify-Topic", "")
    
    print(f"📦 Received webhook: {topic}")
    print(f"   Order ID: {order_data.get('id')}")
    
    # If Printify bridge is configured, sync order
    if bridge:
        try:
            result = bridge.handle_order_webhook(order_data)
            print(f"   Printify sync: {result.get('status')}")
        except Exception as e:
            print(f"   ❌ Printify sync failed: {e}")
    
    return jsonify({"status": "received"}), 200


# ============ PRINTIFY INTEGRATION ============

@app.route("/printify/status")
def printify_status():
    """Check Printify connection status"""
    global printify
    
    api_key = os.getenv("PRINTIFY_API_KEY")
    if not api_key:
        return jsonify({
            "connected": False,
            "message": "PRINTIFY_API_KEY not set",
            "action": "Get API key from https://printify.com/app/account/api"
        })
    
    try:
        printify = PrintifyConnector(api_key)
        shops = printify.get_shops()
        
        return jsonify({
            "connected": True,
            "shops": [{"id": s["id"], "title": s["title"]} for s in shops]
        })
    except Exception as e:
        return jsonify({
            "connected": False,
            "error": str(e)
        })


@app.route("/printify/blueprints")
def printify_blueprints():
    """List available Printify product blueprints"""
    global printify
    
    if not printify:
        return jsonify({"error": "Printify not connected"}), 400
    
    try:
        blueprints = printify.get_blueprints()
        
        # Filter to relevant categories for toxico
        relevant = []
        keywords = ["hoodie", "sweatshirt", "jogger", "tee", "t-shirt", "shorts"]
        
        for bp in blueprints:
            title = bp.get("title", "").lower()
            if any(kw in title for kw in keywords):
                relevant.append({
                    "id": bp["id"],
                    "title": bp["title"],
                    "description": bp.get("description", "")[:100]
                })
        
        return jsonify({
            "total": len(blueprints),
            "relevant_for_toxico": relevant[:20]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============ BRIDGE SETUP ============

@app.route("/bridge/connect", methods=["POST"])
def connect_bridge():
    """Connect Shopify and Printify for automated sync"""
    global shopify, printify, bridge
    
    if not shopify:
        return jsonify({"error": "Shopify not connected"}), 400
    if not printify:
        return jsonify({"error": "Printify not connected"}), 400
    
    try:
        bridge = ShopifyPrintifyBridge(shopify, printify)
        shop_id = bridge.connect_printify_shop()
        
        return jsonify({
            "status": "connected",
            "printify_shop_id": shop_id,
            "message": "Bridge established! Orders will sync automatically."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("=" * 50)
    print("iamtoxico Shopify Integration Server")
    print("=" * 50)
    print()
    print("Credentials:")
    print(f"  Shopify API Key: {os.getenv('SHOPIFY_API_KEY', 'not set')[:15]}...")
    print(f"  Shopify Secret:  {os.getenv('SHOPIFY_API_SECRET', 'not set')[:15]}...")
    print(f"  Printify Key:    {os.getenv('PRINTIFY_API_KEY', 'not set')[:15] if os.getenv('PRINTIFY_API_KEY') else 'NOT SET'}")
    print()
    print("Endpoints:")
    print("  Install: http://localhost:5001/shopify/install?shop=iamtoxico")
    print("  Status:  http://localhost:5001/printify/status")
    print()
    
    app.run(host="0.0.0.0", port=5001, debug=True)
