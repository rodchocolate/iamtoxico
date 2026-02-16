"""
Shopify OAuth & Webhook Handler for iamtoxico
Full lifecycle: OAuth, token persistence, Shopify webhooks,
Printify inbound webhooks, fulfillment tracking.
Run this alongside the main valet server.
"""

import os
import logging
from flask import Flask, request, redirect, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment
load_dotenv()

from shopify_connector import ShopifyConnector, ShopifyPrintifyBridge
from printify_connector import PrintifyConnector

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("iamtoxico")

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

HOST = os.getenv("HOST", "http://localhost:5001")

# Connectors (initialized on first use)
shopify = None
printify = None
bridge = None


# ------------------------------------------------------------------
# Token persistence helpers
# ------------------------------------------------------------------

def _try_restore_shopify():
    """Attempt to restore Shopify connector from persisted token."""
    global shopify
    if shopify:
        return
    tokens = ShopifyConnector._load_tokens_file()
    for domain, entry in tokens.items():
        shopify = ShopifyConnector(shop_domain=domain,
                                   access_token=entry["access_token"])
        log.info("Restored Shopify token for %s", domain)
        break


def _try_init_printify():
    """Attempt to initialise Printify connector from env."""
    global printify
    if printify:
        return
    key = os.getenv("PRINTIFY_API_KEY")
    if key:
        printify = PrintifyConnector(key)
        log.info("Printify connector initialised")


def _try_init_bridge():
    """Wire up bridge if both connectors are ready."""
    global bridge
    if bridge or not shopify or not printify:
        return
    try:
        bridge = ShopifyPrintifyBridge(shopify, printify)
        bridge.connect_printify_shop()
        log.info("Bridge connected — Printify shop %s", bridge.shop_id)
    except Exception as exc:
        log.warning("Bridge init deferred: %s", exc)


# Run on import so the server starts ready when possible
_try_restore_shopify()
_try_init_printify()


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
        
        # Initialize global connector
        shopify = ShopifyConnector(shop_domain=shop, access_token=access_token)

        # Persist token to disk
        shopify.save_token()
        log.info("Token saved for %s", shop)

        # Auto-register Shopify webhooks
        try:
            hooks = shopify.ensure_webhooks(HOST)
            log.info("Shopify webhooks registered: %d", len(hooks))
        except Exception as exc:
            log.warning("Webhook registration deferred: %s", exc)

        # Try wiring up the bridge
        _try_init_bridge()

        # Auto-register Printify webhooks
        if bridge and bridge.shop_id:
            try:
                phooks = printify.ensure_webhooks(bridge.shop_id, HOST)
                log.info("Printify webhooks registered: %d", len(phooks))
            except Exception as exc:
                log.warning("Printify webhook registration deferred: %s", exc)

        session["access_token"] = access_token
        session["shop"] = shop
        
        return jsonify({
            "status": "connected",
            "shop": shop,
            "scope": token_data.get("scope"),
            "message": "Successfully connected to Shopify!"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============ SHOPIFY WEBHOOKS ============

def _verify_shopify_webhook() -> bool:
    """Verify Shopify webhook HMAC. Returns False on failure."""
    hmac_header = request.headers.get("X-Shopify-Hmac-SHA256", "")
    if shopify and hmac_header:
        return shopify.verify_webhook(request.data, hmac_header)
    return True  # allow in dev when shopify not initialized


@app.route("/shopify/webhooks/orders", methods=["POST"])
def webhook_orders():
    """Handle order lifecycle webhooks from Shopify."""
    if not _verify_shopify_webhook():
        return jsonify({"error": "Invalid signature"}), 401

    order_data = request.json
    topic = request.headers.get("X-Shopify-Topic", "")
    order_id = order_data.get("id") if order_data else None
    log.info("📦 Shopify webhook: %s  order=%s", topic, order_id)

    if topic == "orders/create":
        if bridge:
            try:
                result = bridge.handle_order_webhook(order_data)
                log.info("   Printify order: %s", result.get("status"))
            except Exception as exc:
                log.error("   Printify order failed: %s", exc)

    elif topic == "orders/cancelled":
        if bridge:
            try:
                result = bridge.handle_order_cancelled(order_data)
                log.info("   Cancel result: %s", result.get("status"))
            except Exception as exc:
                log.error("   Cancel failed: %s", exc)

    elif topic == "orders/fulfilled":
        log.info("   Order %s fulfilled in Shopify", order_id)

    elif topic == "orders/updated":
        log.info("   Order %s updated", order_id)

    return jsonify({"status": "received"}), 200


@app.route("/shopify/webhooks/products", methods=["POST"])
def webhook_products():
    """Handle product lifecycle webhooks from Shopify."""
    if not _verify_shopify_webhook():
        return jsonify({"error": "Invalid signature"}), 401

    product_data = request.json
    topic = request.headers.get("X-Shopify-Topic", "")
    log.info("🎁 Shopify product webhook: %s  product=%s",
             topic, product_data.get("id") if product_data else None)
    return jsonify({"status": "received"}), 200


@app.route("/shopify/webhooks/refunds", methods=["POST"])
def webhook_refunds():
    """Handle refund webhooks from Shopify."""
    if not _verify_shopify_webhook():
        return jsonify({"error": "Invalid signature"}), 401

    refund_data = request.json
    log.info("💸 Shopify refund webhook: order=%s",
             refund_data.get("order_id") if refund_data else None)
    return jsonify({"status": "received"}), 200


@app.route("/shopify/webhooks/app", methods=["POST"])
def webhook_app():
    """Handle app/uninstalled webhook."""
    global shopify, bridge
    topic = request.headers.get("X-Shopify-Topic", "")
    log.info("🔔 Shopify app webhook: %s", topic)
    if topic == "app/uninstalled":
        shopify = None
        bridge = None
        log.info("   App uninstalled — connectors cleared")
    return jsonify({"status": "received"}), 200


# ============ PRINTIFY INBOUND WEBHOOKS ============

@app.route("/printify/webhooks", methods=["POST"])
def printify_webhook():
    """Handle inbound webhooks from Printify.

    Topics: order:created, order:updated, order:sent-to-production,
            order:shipping-update, order:completed,
            product:publish:started, product:publish:succeeded,
            product:publish:failed
    """
    event = request.json or {}
    topic = event.get("type", event.get("topic", "unknown"))
    log.info("🎨 Printify webhook: %s", topic)

    if topic in ("order:shipping-update", "order:completed") and bridge:
        try:
            result = bridge.handle_fulfillment_update(event)
            log.info("   Fulfillment sync: %s", result.get("status"))
        except Exception as exc:
            log.error("   Fulfillment sync failed: %s", exc)

    return jsonify({"status": "received"}), 200


# ============ WEBHOOK MANAGEMENT ============

@app.route("/webhooks/register", methods=["POST"])
def register_webhooks():
    """Manually trigger webhook registration for both platforms."""
    results = {"shopify": [], "printify": []}

    if shopify:
        try:
            results["shopify"] = shopify.ensure_webhooks(HOST)
        except Exception as exc:
            results["shopify"] = {"error": str(exc)}

    if printify and bridge and bridge.shop_id:
        try:
            results["printify"] = printify.ensure_webhooks(bridge.shop_id, HOST)
        except Exception as exc:
            results["printify"] = {"error": str(exc)}

    return jsonify(results)


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
    """Connect Shopify and Printify for automated sync."""
    global shopify, printify, bridge
    
    _try_restore_shopify()
    _try_init_printify()

    if not shopify:
        return jsonify({"error": "Shopify not connected"}), 400
    if not printify:
        return jsonify({"error": "Printify not connected"}), 400
    
    try:
        bridge = ShopifyPrintifyBridge(shopify, printify)
        shop_id = bridge.connect_printify_shop()

        # Auto-register webhooks on both sides
        shopify_hooks = shopify.ensure_webhooks(HOST)
        printify_hooks = printify.ensure_webhooks(shop_id, HOST)
        
        return jsonify({
            "status": "connected",
            "printify_shop_id": shop_id,
            "shopify_webhooks": len(shopify_hooks),
            "printify_webhooks": len(printify_hooks),
            "message": "Bridge established! Orders will sync automatically."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    log.info("=" * 50)
    log.info("iamtoxico Shopify Integration Server")
    log.info("=" * 50)
    log.info("HOST: %s", HOST)
    log.info("Shopify API Key: %s...",
             os.getenv("SHOPIFY_API_KEY", "not set")[:15])
    log.info("Printify Key:    %s...",
             (os.getenv("PRINTIFY_API_KEY") or "NOT SET")[:15])
    log.info("")
    log.info("Endpoints:")
    log.info("  OAuth:     %s/shopify/install?shop=iamtoxico", HOST)
    log.info("  Status:    %s/printify/status", HOST)
    log.info("  Bridge:    POST %s/bridge/connect", HOST)
    log.info("  Webhooks:  POST %s/webhooks/register", HOST)
    log.info("")

    _try_init_bridge()
    app.run(host="0.0.0.0", port=5001, debug=True)
