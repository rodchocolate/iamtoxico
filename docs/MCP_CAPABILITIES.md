# iamtoxico MCP Capabilities

> **"liberates laughing"** — deviant but proper, the sporting life

Last Updated: November 28, 2025

---

## 🔌 CONNECTED PLATFORMS

### ✅ Printify (POD Fulfillment)
**Status:** CONNECTED  
**Shop ID:** 22994552  
**Token Expires:** Jan 2027

| Action | Capability |
|--------|------------|
| `get_shops()` | List connected stores |
| `get_blueprints()` | Browse 1,215 product templates (51 hoodies, joggers, tees, etc.) |
| `get_print_providers()` | Find print partners by blueprint |
| `get_variants()` | Get sizes/colors for any product |
| `create_product()` | Create new POD product |
| `publish_product()` | Push to connected store |
| `upload_image()` | Upload design artwork |
| `get_orders()` | List orders |
| `submit_order()` | Send to production |
| `calculate_shipping()` | Get shipping costs |

**Files:** `/toxico/shopify-app/printify_connector.py`

---

### ⏳ Shopify (E-Commerce)
**Status:** READY (needs store creation)  
**App:** toxico  
**Client ID:** `6347ea0e4232c5d68711bb80f0623930`

| Action | Capability |
|--------|------------|
| `get_auth_url()` | Start OAuth flow |
| `exchange_token()` | Complete OAuth |
| `get_products()` | List store products |
| `create_product()` | Add new product |
| `update_product()` | Modify existing |
| `get_orders()` | List orders |
| `fulfill_order()` | Mark as shipped |
| `get_inventory_levels()` | Check stock |
| `adjust_inventory()` | Update quantities |
| `create_collection()` | Organize products |
| `verify_webhook()` | Validate incoming webhooks |

**Files:** `/toxico/shopify-app/shopify_connector.py`

**Next:** Create store at iamtoxico.myshopify.com

---

### ⏳ Spotify (Music Integration)
**Status:** CREDENTIALS NEEDED  
**Purpose:** Song/playlist recommendations in Valet

| Action | Capability |
|--------|------------|
| `search_tracks()` | Find songs |
| `get_recommendations()` | AI-powered suggestions |
| `create_playlist()` | Build playlists |
| `get_audio_features()` | Analyze tempo, energy, etc. |

**Files:** `/toxico/.env` (needs SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)

---

### ✅ Gemini AI (LLM)
**Status:** CONNECTED  
**Model:** gemini-1.5-flash

| Action | Capability |
|--------|------------|
| Product recommendations | "What should I buy for X?" |
| Song/YouTube suggestions | Default valet mode |
| Travel recommendations | Destination ideas |
| Category detection | Auto-detect query type |

**Files:** `/toxico/server.py`

---

### ✅ Groq AI (LLM - Fastest)
**Status:** CONNECTED  
**Rate:** 14,400 req/day free

| Action | Capability |
|--------|------------|
| Fast inference | Sub-second responses |
| Backup LLM | Fallback when Gemini busy |

**Files:** `/toxico/.env`

---

## 🛒 AFFILIATE NETWORKS (Pending)

| Platform | Status | Commission | Action Needed |
|----------|--------|------------|---------------|
| Target Partners | ⏳ | 1-8% | Apply at partners.target.com |
| ShareASale | ⏳ | 5-10% | Apply for Peak Design, Herschel |
| Amazon Associates | ⏳ | 1-10% | Apply (low priority) |
| Impact (Walmart) | ⏳ | 1-4% | Apply (low priority) |

---

## 🌐 VALET SERVER

**Status:** READY  
**Port:** 8080  
**Endpoint:** `http://127.0.0.1:8080/valet.html`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/valet` | POST | AI chat (songs, products, travel) |
| `/api/catalog` | GET | Product catalog |
| `/api/vote` | POST | Like/dislike items |
| `/valet.html` | GET | Frontend UI |

**Modes:**
- **Default:** Songs, YouTube, travel recommendations
- **Product Mode:** Triggers with 7+ commercial likes OR explicit product query

---

## 📦 CATALOG

**Status:** 217 products  
**With Images:** 6 (Crocs, UGG, New Balance)

| Category | Count | Examples |
|----------|-------|----------|
| Footwear | 50+ | UGG, Crocs, Birkenstock, Nike, Adidas |
| Loungewear | 20+ | Hoodies, joggers |
| Travel | 15+ | Backpacks (Peak Design, Away, Open Story) |
| Wellness | 10+ | Maude, etc. |
| Hot Tubs | 5+ | Referral products |

**Files:** `/toxico/data/catalog.json`

---

## 🔧 QUICK COMMANDS

### Start Valet Server
```bash
pkill -9 -f "toxico.*server" 2>/dev/null; sleep 1
source /Users/jasonjenkins/Desktop/localmodels/.venv/bin/activate
python /Users/jasonjenkins/Desktop/alpha/toxico/server.py
```

### Start Shopify Integration Server
```bash
cd /Users/jasonjenkins/Desktop/alpha/toxico/shopify-app
source /Users/jasonjenkins/Desktop/localmodels/.venv/bin/activate
python server.py
# Runs on port 5001
```

### Test Printify Connection
```bash
cd /Users/jasonjenkins/Desktop/alpha/toxico/shopify-app
source /Users/jasonjenkins/Desktop/localmodels/.venv/bin/activate
export $(grep -v '^#' .env | xargs)
python -c "from printify_connector import PrintifyConnector; import os; c = PrintifyConnector(os.getenv('PRINTIFY_API_KEY')); print(c.get_shops())"
```

---

## 🚀 WHEN STORE IS LIVE

### Wire Sales Flow
```
Customer → Shopify → Printify (POD) → Ship
                  ↘ Affiliate (external) → Commission
```

### Order Sync
1. Customer orders on Shopify
2. Webhook fires to `/shopify/webhooks/orders`
3. Bridge creates Printify order (if POD item)
4. Printify produces & ships
5. Tracking synced back to Shopify

### Revenue Streams
| Source | Margin | Notes |
|--------|--------|-------|
| Owned (POD) | 65-75% | Hoodies, joggers, tees |
| Owned (White-label) | 75-82% | Boxers, robes (Q1 2026) |
| Affiliate (High) | 8-10% | Direct brand partnerships |
| Affiliate (Mid) | 5-8% | ShareASale, etc. |
| Affiliate (Low) | 1-4% | Amazon, Walmart |

---

## 📋 CREDENTIAL LOCATIONS

| Service | Location |
|---------|----------|
| Printify | `/toxico/shopify-app/.env` |
| Shopify | `/toxico/shopify-app/.env` |
| Gemini | `/toxico/.env` |
| Groq | `/toxico/.env` |
| Spotify | `/toxico/.env` (empty) |

---

## 🔮 ROADMAP

### Now
- [x] Printify connected
- [x] Shopify app credentials
- [x] Valet AI working
- [ ] Create Shopify store

### Next
- [ ] Connect Shopify to Printify
- [ ] Create first hoodie product
- [ ] Apply to affiliate networks
- [ ] Add Spotify integration

### Q1 2026
- [ ] White-label boxers (Portugal)
- [ ] Expand catalog images
- [ ] Launch Captain Adventure collection

---

*For updates, ask: "Show me the MCP capabilities"*
