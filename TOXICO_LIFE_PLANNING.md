# Toxico Life — Affiliate & Reseller Planning

**Last updated:** 2026-04-11

## Vision

**"toxico life"** is a third page on iamtoxico.com that extends the brand beyond our Printify originals into a curated lifestyle world. It showcases affiliate products, reseller partnerships, and creative collaborations — giving depth to the brand and positioning toxico as a tastemaker, not just a clothing label.

## Page Architecture

| Page | Purpose | Access |
|---|---|---|
| `index.html` | Public storefront — Printify originals (live shop) | Public |
| `preview.html` | Internal staging grid — all products, renaming reference | Password-protected / personal use |
| `toxico-life.html` | Curated lifestyle — affiliates, resellers, collabs | Public |

### Preview Page Notes
- Password-protected for internal reference only
- Grid layout: 3 across desktop, 2 across mobile
- Product identification on mobile: **row X + L/R** (left or right in the row)
- Makes renaming and staging decisions much easier

---

## Reseller / Wholesale Targets

### Dakine
- **Type:** Reseller / wholesale account
- **Category:** Outdoor lifestyle — backpacks, luggage, surf/snow accessories
- **Fit:** Strong crossover with toxico active aesthetic. Bags + accessories complement our apparel line without competing.
- **Action:** Research dealer/reseller program, minimum orders, territory requirements.
- **Status:** Prospect

### JanSport
- **Type:** Reseller / wholesale account
- **Category:** Bags, backpacks, lifestyle accessories
- **Fit:** Heritage brand with affordable price points that complement premium toxico originals. Good entry point for accessories.
- **Action:** Find wholesale/dealer application process. Look for authorized reseller programs.
- **Status:** Prospect

---

## Affiliate Programs

### Amazon Associates
- **Type:** Affiliate (commission-based)
- **Category:** Multi-category — luxury loungewear, activewear, lifestyle goods
- **Commission:** 4–8% on qualifying purchases
- **Integration:** Curated picks displayed on toxico life page. Items added to `data/catalog.json` with `source: "affiliate"`.
- **Tooling:** `shopify-app/add_amazon_items.py` for catalog integration. Valet API serves affiliate items alongside originals.
- **Status:** Active program — curation ongoing

### Other Affiliate Opportunities
- Explore additional affiliate networks (ShareASale, CJ, Rakuten) for brands that align with the toxico aesthetic
- Focus on: premium loungewear, streetwear accessories, fitness/active lifestyle

### Prosumer Audio / HiFi
- **Type:** Affiliate / editorial resale
- **Category:** Turntables, speakers, boutique audio, synths, studio objects
- **Fit:** Strong overlap with the toxico tastemaker angle. High-ticket gear adds aspirational value and aligns with the MelodicLabs ecosystem.
- **Priority Channels:** Reverb, Audiogon, US Audio Mart, Sweetwater Gear Exchange, Discogs hardware
- **Action:** Start with portable listening, desktop speakers, turntables, and visually distinctive instruments that can live inside toxico life editorials.
- **Status:** Prospect

---

## Adult / Alternative Lifestyle

### Hung Adult Products
- **Type:** Reseller / wholesale
- **Category:** Adult lifestyle products
- **Fit:** Edgy brand positioning — toxico already leans into provocative naming and aesthetic
- **Action:** Research wholesale program, minimum orders, age-gate requirements for toxico-life page
- **Status:** Prospect

### Tack Down
- **Type:** Affiliate / cross-promotion
- **Category:** Streetwear / accessories
- **Action:** Explore commission-based partnership, co-marketing
- **Status:** Prospect

### Kink Mob
- **Type:** Affiliate / cross-promotion
- **Category:** Alternative lifestyle brand
- **Action:** Research affiliate program, co-marketing opportunities
- **Status:** Prospect

---

## Performance / Motorsport

### K1 RaceGear
- **Type:** Affiliate / curated outbound
- **Category:** Motorsport apparel, rain gear, utility outerwear
- **Fit:** Technical, confrontational, and slightly anti-fashion in a way that works well with the toxico aesthetic.
- **Seed Item:** [K1 RaceGear 1-Piece Rain Suit](https://www.k1racegear.com/products/k1-racegear-1-piece-rain-suit?variant=41381540752)
- **Action:** Test as an editorial product card first. If performance/motorsport gets traction, expand into gloves, race bags, and paddock utility gear.
- **Status:** Research

---

## Luxury & Aspirational

### Luxury Car Broker
- **Type:** Referral / affiliate
- **Category:** Luxury automotive
- **Fit:** Aspirational lifestyle play — positions toxico alongside high-end taste. Even if conversion is rare, it elevates brand perception.
- **Action:** Identify luxury car brokers/dealers with referral programs. Look for concierge-style partnerships.
- **Status:** Idea / research phase

### Art & Design Objects
- **Type:** Affiliate / editorial outbound
- **Category:** Editions, collectible objects, framed works, furniture-adjacent design
- **Fit:** Lets toxico life move beyond clothing into a complete environment. This is where "taste" becomes visible instead of just wearable.
- **Action:** Prioritize partners that support affiliate or referral links. Where no program exists, still curate outbound editorial cards and treat monetization as secondary.
- **Status:** Research

---

## Creative Collaborations

### Papa Mesk — Graphic Design
- **Role:** Graphic design collaborator
- **Scope:** Product artwork, print designs, brand visuals
- **Link:** [Papa Mesk](https://papamesk.com)
- **Notes:** Key creative partner for expanding the toxico design library. Collaboration on prints for harem pants, hoodies, and toxico life visual identity.

---

## Implementation Notes

### Catalog Schema (Affiliate Items)
```json
{
  "id": "amzn-{slug}",
  "title": "Product Name",
  "price": 99.99,
  "image": "https://...",
  "category": "lounge|activewear|accessories|adult|automotive",
  "tags": ["tag1", "tag2"],
  "source": "affiliate",
  "affiliate": {
    "vendor": "amazon|dakine|jansport|reverb|audiogon|hung|k1racegear|other",
    "link": "https://...",
    "commission_rate": 0.04
  }
}
```

### Toxico Life Page Requirements
- Sections by lifestyle category (not just product type)
- Age-gate for adult section
- Clean editorial feel — more magazine than storefront
- Each partner/brand gets a mini feature card
- Amazon items pulled from catalog.json (same as valet mode)
- Mobile-first responsive layout

### Next Steps
1. Build `toxico-life.html` shell with section layout
2. Reach out to Dakine and JanSport for reseller applications
3. Build the first partner approval matrix: Dakine, JanSport, Hung Adult Products, K1 RaceGear, Reverb/Audiogon
4. Continue Amazon curation — focus on luxury loungewear
5. Add a prosumer audio / hi-fi section with initial editorial picks
6. Add an art / design objects section with non-apparel aspirational items
7. Connect with Papa Mesk on next design batch
8. Research luxury car broker referral programs
9. Add age-gate component for adult lifestyle section
