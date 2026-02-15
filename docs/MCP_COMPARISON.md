# MCP Comparison: iamtoxico vs MelodicLabs

> Quick reference for platform capabilities

Last Updated: November 28, 2025

---

## 🎯 Purpose & Philosophy

| Aspect | iamtoxico | MelodicLabs |
|--------|-----------|-------------|
| **Core Mission** | AI shopping valet / lifestyle assistant | AI music curation / playlist engine |
| **Tagline** | "liberates laughing" — deviant but proper | "The Rule of 7" — seed discovery flow |
| **Alter Ego** | Captain Adventure | The Musicologist |
| **Revenue Model** | E-commerce + Affiliates + POD | Subscription / Desktop App |

---

## 🔌 CONNECTED PLATFORMS

### iamtoxico

| Platform | Status | Purpose |
|----------|--------|---------|
| **Printify** | ✅ Connected | POD fulfillment (1,215 blueprints) |
| **Shopify** | ⏳ Ready | E-commerce storefront |
| **Gemini AI** | ✅ Connected | Product/song recommendations |
| **Groq AI** | ✅ Connected | Fast inference backup |
| **Spotify** | ⏳ Pending | Song suggestions in Valet |
| **Target Partners** | ⏳ Pending | Affiliate (Open Story) |
| **ShareASale** | ⏳ Pending | Affiliate network |

### MelodicLabs

| Platform | Status | Purpose |
|----------|--------|---------|
| **Spotify API** | ✅ Connected | Metadata, audio features, recommendations |
| **Last.fm** | ✅ Connected | Similar artists, tag-based discovery |
| **MusicBrainz** | ✅ Connected | Canonical metadata |
| **Gemini AI** | ✅ Connected | Playlist reasoning, liner notes |
| **OpenAI** | ✅ Connected | GPT-4o-mini fallback |
| **YouTube** | ✅ Connected | Playback (Electron header spoofing) |
| **Local Library** | ✅ Connected | library.json (owned tracks) |

---

## 🛠️ TOOL ACTIONS

### iamtoxico Tools

| Tool | Actions |
|------|---------|
| **Printify** | `get_shops()`, `get_blueprints()`, `create_product()`, `publish_product()`, `upload_image()`, `submit_order()` |
| **Shopify** | `get_auth_url()`, `exchange_token()`, `get_products()`, `create_product()`, `fulfill_order()`, `create_collection()` |
| **Valet AI** | Product recommendations, song/YouTube suggestions, travel ideas, category detection |
| **Catalog** | 217 products, vote/like system, commercial vs non-commercial tracking |

### MelodicLabs Tools

| Tool | Actions |
|------|---------|
| **Orchestrator (Perl)** | `--fresh` (library filter), `--deep` (seed expansion), tier ranking (💎/🥇) |
| **Media Bridge (Node)** | Generate `PLAYLIST_FUNNEL.md`, `CREATIVE_BRIEF.md`, DALL-E prompts, Giphy keywords |
| **Seed System (JS)** | Rule of 7 flow: 1→7→37→Final, freeze/lock seeds, manual builder |
| **MCP Server** | `generate_playlist(mode)`, `generate_creative_assets()`, `get_status()` |
| **Search Engines** | JSON fuzzy search, embedding/semantic search |

---

## 🏗️ ARCHITECTURE

### iamtoxico
```
Flask Server (8080)
├── /api/valet → Gemini AI → Recommendations
├── /api/catalog → Product database
├── /api/vote → Like/dislike tracking
└── valet.html → Frontend UI

Shopify Integration (5001)
├── OAuth flow → Store connection
├── Webhooks → Order sync
└── Printify Bridge → POD fulfillment
```

### MelodicLabs
```
MCP Server (Node)
├── orchestrator.pl → Playlist generation
├── bridge_mcp.js → API queries (Last.fm, MB)
├── media_bridge.js → Creative assets
└── final_playlist.json → Output

Frontend (Electron/Web)
├── seed-system.js → Rule of 7 UI
├── app.html → Desktop
└── mobile.html → PWA
```

---

## 📦 DATA STRUCTURES

### iamtoxico
```json
// catalog.json
{
  "products": [
    {
      "id": "crocs-classic",
      "name": "Crocs Classic Clog",
      "price": 55,
      "category": "footwear",
      "margin_tier": "affiliate",
      "image": "https://media.crocs.com/..."
    }
  ]
}
```

### MelodicLabs
```json
// library.json
{
  "tracks": [
    {
      "name": "Bohemian Rhapsody",
      "artist": "Queen",
      "album": "A Night at the Opera",
      "path": "/Music/Queen/...",
      "rating": 5
    }
  ]
}

// final_playlist.json
{
  "playlist": [...],
  "tiers": { "diamond": 37, "gold": 137, "pool": 2137 }
}
```

---

## 🖥️ DEPLOYMENT MODES

| Mode | iamtoxico | MelodicLabs |
|------|-----------|-------------|
| **Local Dev** | Flask + Python venv | Python + Electron |
| **Web** | Apache/Nginx | PHP (`api.php`) |
| **Desktop** | N/A | Electron (header spoofing for YouTube) |
| **Mobile** | PWA (valet.html) | PWA (mobile.html) |

---

## 🔄 KEY WORKFLOWS

### iamtoxico: Purchase Flow
```
User Query → Valet AI → Product Recommendations
     ↓
User Likes → Commercial Mode (7+ likes)
     ↓
Buy Link → Shopify Store → Order
     ↓
POD Items → Printify → Fulfillment
Affiliate Items → Partner Link → Commission
```

### MelodicLabs: Playlist Flow
```
User Seeds → Orchestrator (Perl)
     ↓
API Expansion → Last.fm / MusicBrainz
     ↓
Tiering → 2137 → 259 → 137 → 37
     ↓
Media Bridge → Creative Brief → DALL-E Prompt
     ↓
Final Playlist → YouTube Embed
```

---

## 📋 SHARED CAPABILITIES

| Capability | iamtoxico | MelodicLabs |
|------------|-----------|-------------|
| **AI Chat** | ✅ Gemini/Groq | ✅ Gemini/OpenAI |
| **Vote/Like System** | ✅ | ✅ (Freeze/Lock) |
| **Session Storage** | ✅ | ✅ |
| **PWA Support** | ✅ | ✅ |
| **Dark Theme** | ✅ (Purple) | ✅ |

---

## 🚀 WHAT'S UNIQUE

### iamtoxico Only
- Printify POD integration
- Shopify e-commerce
- Affiliate tracking (margins)
- Product catalog with pricing
- Dual-mode AI (songs + products)

### MelodicLabs Only
- Perl orchestrator (deterministic logic)
- Rule of 7 seed expansion
- Local library integration
- YouTube playback (Electron)
- Creative briefs (DALL-E, Giphy)
- Tiered ranking system (💎/🥇)

---

## 📍 FILE LOCATIONS

| File | iamtoxico | MelodicLabs |
|------|-----------|-------------|
| **Main Server** | `/toxico/server.py` | `/api.py` or `/api.php` |
| **Capabilities Doc** | `/toxico/docs/MCP_CAPABILITIES.md` | `/MCP_MASTER_PLAN.md` |
| **Credentials** | `/toxico/.env` | N/A (in code) |
| **Product/Library** | `/toxico/data/catalog.json` | `/library.json` |

---

## 🔮 POTENTIAL SYNERGIES

1. **Music → Product**: Recommend merchandise based on playlist mood
2. **Shared AI**: Use same Gemini/Groq credentials
3. **Cross-Promote**: Captain Adventure playlists in Valet
4. **Unified Sessions**: Single user profile across both platforms

---

*Ask: "Show me iamtoxico capabilities" or "Show me MelodicLabs architecture"*
