# MCP Product Research Integration

## 🎯 Overview

When you share a product link, I'll run a structured research routine using MCP tools to:
1. **Fetch** product details from the URL
2. **Analyze** pricing, specs, and positioning
3. **Source** alternatives across tiers (high/mid/budget)
4. **Integrate** into catalog.json with proper structure

---

## ⚡ QUICK PRODUCT SUBMISSION (Primary Workflow)

### How It Works
Send me a product (URL, name, or description) and I'll quickly:

1. **Fetch & Parse** - Get product details, price, images
2. **Ask You** - "This one, something else, or both?"
3. **Source Photo** - Find official product image (required for display)
4. **Add to Catalog** - With proper tier, tags, affiliate info

### Command Format
```
[URL or product description]
```

### Example Flow
```
You: https://www.ugg.com/classic-ultra-mini

Me: Found: UGG Classic Ultra Mini - $150
    Category: footwear (cozy boots)
    Tier: High
    Image: ✅ Found official photo
    
    Options:
    1. Add this product
    2. Find alternatives (same vibe, different prices)
    3. Add this + alternatives
    
    Which?

You: 3

Me: Added to catalog:
    ✅ UGG Classic Ultra Mini - $150 (high tier)
    ✅ EMU Australia Stinger - $140 (high tier)  
    ✅ Bearpaw Brady - $80 (mid tier)
    ✅ Koolaburra Burra - $60 (low tier)
    
    All have real photos. Displaying now.
```

### Photo Requirement
**Products only display if they have REAL product photography.**

- `REAL_PHOTOS_ONLY = true` (default)
- Placeholders are rejected
- I'll source official brand CDN images when adding products
- If no photo available, product stays in catalog but won't display until you add one

### Quick Add Variants
| Input | Action |
|-------|--------|
| `[URL]` | Fetch, analyze, offer options |
| `Add: [product name]` | Search and add with photo |
| `Like [product] but cheaper` | Find alternatives |
| `[URL] + alternatives` | Add product and find 3-6 alternatives |
| `Just add it: [URL]` | Skip confirmation, add immediately |

---

## 🔗 Supported Link Types

| Source | What I Extract | Notes |
|--------|----------------|-------|
| **Amazon** | Title, price, ASIN, images, reviews | Best for alternatives |
| **Brand sites** | MSRP, materials, sizing | For premium tier |
| **Affiliate networks** | Commission rates, cookie duration | ShareASale, CJ, etc. |
| **Alibaba/1688** | MOQ, factory price, supplier info | White-label sourcing |
| **Shopify stores** | Product JSON, variants, inventory | Competitor research |

---

## 🛠️ Research Routine

### Step 1: Link Analysis
```
Input: https://example.com/product/cool-item
```
I will:
- Fetch webpage content
- Extract product name, price, description, images
- Identify brand and category
- Check for affiliate program availability

### Step 2: Tier Positioning
Based on price point, I determine tier:
| Price Range | Tier | Strategy |
|-------------|------|----------|
| $150+ | High | Premium affiliate, aspirational |
| $50-149 | Mid | Core affiliate, volume |
| <$50 | Low | Value affiliate, accessibility |

### Step 3: Alternative Sourcing
I search for:
- **Same category, different brands** (3-5 alternatives per tier)
- **White-label options** if margin opportunity exists
- **Affiliate program availability** for each

### Step 4: Catalog Integration
I add to `/toxico/data/catalog.json`:
```json
{
  "id": "product-category-brand-001",
  "name": "Product Name",
  "brand": "Brand",
  "category": "category",
  "tier": "high|mid|low",
  "price": "$XX",
  "priceValue": XX,
  "url": "https://...",
  "image": "https://...",
  "description": "...",
  "vibes": ["comfort", "adventure"],
  "activities": ["lounging", "travel"],
  "tags": ["captain adventure", "cozy"],
  "affiliate": {
    "network": "ShareASale|CJ|Amazon|Direct",
    "program": "brand-name",
    "commission": "8%",
    "cookie": "30 days"
  },
  "sourcing": {
    "type": "affiliate|white-label|printify",
    "cost": null,
    "margin": null,
    "moq": null
  },
  "active": true
}
```

---

## 📋 Research Request Format

### Quick Add (Single Product)
```
Add this: [URL]
```
I'll fetch, analyze, and add to catalog.

### Category Research
```
Research: [category] - find high/mid/low options
Example: "Research: weighted blankets - find high/mid/low options"
```
I'll source 9-12 products across tiers.

### Competitor Analysis
```
Analyze: [brand or store URL]
```
I'll map their product lineup and find alternatives.

### White-Label Sourcing
```
Source white-label: [product type]
Example: "Source white-label: shearling slippers"
```
I'll find Alibaba/factory options with MOQ and pricing.

---

## 🔧 MCP Tools Used

### fetch_webpage
- Extract product details from any URL
- Parse pricing, descriptions, images
- Check for structured data (JSON-LD)

### semantic_search / grep_search
- Find existing similar products in catalog
- Avoid duplicates
- Match vibes/activities

### run_in_terminal
- cURL for API calls (affiliate networks)
- JSON parsing with jq

### create_file / replace_string_in_file
- Add new products to catalog.json
- Update existing entries

---

## 📊 Research Output Template

When I complete research, I'll provide:

```
## Product Research: [Category/Item]

### Added to Catalog:
| Tier | Brand | Product | Price | Affiliate |
|------|-------|---------|-------|-----------|
| High | ... | ... | $XXX | ✅/❌ |
| Mid | ... | ... | $XX | ✅/❌ |
| Low | ... | ... | $X | ✅/❌ |

### White-Label Opportunity:
- Supplier: [name]
- MOQ: [quantity]
- Cost: $X/unit
- Potential Margin: XX%

### Affiliate Programs:
- [Brand]: [Network], [Commission], [Cookie]

### Next Steps:
- [ ] Apply to [affiliate program]
- [ ] Request samples from [supplier]
- [ ] Add to [category] filter in valet
```

---

## 🏷️ Category Mapping

When adding products, I map to existing categories:
- `loungewear` — robes, pajamas, lounge sets
- `underwear` — boxers, briefs, undershirts
- `outerwear` — coats, jackets, puffers
- `footwear` — boots, slippers, clogs, sandals
- `eyewear` — sunglasses, readers, blue light
- `travel` — bags, organizers, accessories
- `wellness` — intimacy, relaxation, self-care
- `home` — blankets, candles, decor
- `grooming` — skincare, haircare, tools
- `accessories` — watches, wallets, belts
- `outdoor` — hot tubs, furniture, gear
- `fragrance` — cologne, room sprays

---

## 🎨 Vibe & Activity Tags

### Vibes (mood/aesthetic)
`cozy`, `luxe`, `adventure`, `minimal`, `playful`, `refined`, `sporty`, `relaxed`, `bold`, `classic`, `modern`, `heritage`, `sustainable`, `indulgent`

### Activities (use case)
`lounging`, `sleeping`, `travel`, `work-from-home`, `date-night`, `outdoor`, `poolside`, `spa-day`, `workout`, `everyday`, `special-occasion`, `gifting`

---

## 🚀 Quick Commands

| Command | Action |
|---------|--------|
| `Add: [URL]` | Fetch and add single product |
| `Research: [category]` | Full tier research |
| `Alternatives to: [URL]` | Find competitors |
| `White-label: [product]` | Sourcing options |
| `Affiliate check: [brand]` | Find affiliate program |
| `Update catalog` | Sync all active products |

---

## 📁 Files Modified

| File | Purpose |
|------|---------|
| `/toxico/data/catalog.json` | Product database |
| `/toxico/docs/SOURCING_ROADMAP.md` | Strategy & suppliers |
| `/toxico/server.py` | API endpoints |
| `/toxico/valet.html` | Frontend display |

---

*Last Updated: November 28, 2025*
