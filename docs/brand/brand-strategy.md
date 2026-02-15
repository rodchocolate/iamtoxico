# Brand Strategy

- Brand: iamtoxico
- Positioning: casual-lounge street minimalism; comfort-first with edge.
- Voice: lowercase, dry wit, confident, laconic.
- Vibe words: minimal, comfy, restrained, toxic-green accent.
- Taglines (draft): "comfortable with contradictions", "soft but not sweet", "toxic in lowercase".

Identity
- Wordmark: lowercase sans, subtle ink trap. Create SVG + favicon.
- Colors: Monochrome core (#111, #f4f4f4) + accent toxic green (#39FF14 test) tuned for accessibility.
- Type: Inter or Space Grotesk for web; match theme system fonts where possible.

Assets
- Ensure all print files are sRGB, transparent background for DTG.
- Master art: 4500x5400 px; export 300dpi for suppliers that require it.

---

## MelodicLabs Interface Integration

iamtoxico.com runs on the MelodicLabs "Shopping Valet" framework — an AI chat interface that serves curated content + commerce in a 7-card mobile layout.

### Card Mix Strategy (7 cards mobile)
| Slot | Type | Example Content |
|------|------|-----------------|
| 1 | Content | Curated playlist / vibe video |
| 2 | Content | Brand mood reel / behind-the-scenes |
| 3 | **Offer** | Current drop (underwear capsule) |
| 4 | Content | Lifestyle inspo / fit check UGC |
| 5 | **Offer** | Best seller / core product |
| 6 | Content | Artist collab / music video |
| 7 | **Offer** | Affiliate or ad slot (ed pills, wellness, etc.) |

### Mobile Controls
| Button | Action |
|--------|--------|
| 🔄 Refresh | New set of 7 cards |
| **?** | Opens preferences modal |

### Preferences Modal (? button)
Small modal/drawer for refining AI suggestions without cluttering the main UI.

**Input:** Free text field  
**Examples:**
- "no country music"
- "more 90s vibes"
- "skip workout gear"
- "only show underwear"

**Behavior:**
- Stores exclusions/preferences in sessionStorage
- Appends to AI prompt on next refresh
- Persists across session, clears on close
- Optional: show active filters as dismissible chips

**UI Sketch:**
```
┌─────────────────────────────┐
│  Refine Your Feed       ✕  │
├─────────────────────────────┤
│  [ no country music    ]    │
│                             │
│  Active filters:            │
│  [✕ no rap] [✕ only L size] │
│                             │
│  [ Apply ]  [ Clear All ]   │
└─────────────────────────────┘
```

**Implementation Notes (for iamtoxico prototype):**
- Build in `/toxico/` first, don't touch live MelodicLabs
- Reuse existing modal pattern from Builder Modal
- Store in `sessionStorage.getItem('userPrefs')`
- Inject into AI prompt: `"User preferences: ${prefs}"`

### Content Sources
- **Self-made**: Brand videos, product loops, waistband detail macros
- **Curated**: Vibe-matched playlists, music videos, lifestyle content
- **AI-suggested**: Songs/videos that fit "toxic in lowercase" aesthetic

### Monetization Layers
1. **Direct sales** — Own products in offer slots
2. **Affiliate** — Lifestyle/wellness products (ed pills, supplements, etc.)
3. **Ad space** — Sell slot 7 across toxico or sister sites (ass.life, nectarlovebox, etc.)

### Cross-Site Potential
Same 7-card framework deploys across domains:
- iamtoxico.com — loungewear + edge
- ass.life — adult/provocative vertical
- nectarlovebox.* — intimacy/romance angle
- communitydick.* — male wellness/lifestyle

Shared ad inventory = network effect for slot 7 monetization.

---

Open Questions
- Accent color final pick.
- Logo placement rules.
- Packaging stickers? Thank-you card?
- Slot 7 ad rate card / affiliate program selection.
