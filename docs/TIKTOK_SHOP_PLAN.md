# TikTok Shop plan for iamtoxico

Researched 2026-07-18. Goal: sell on TikTok with one-tap Apple Pay in-app
checkout, driven by influencers and/or our own media.

## What works today

- TikTok Shop US is live with in-app checkout. **Apple Pay is supported**
  (plus cards, PayPal, Google Pay, Klarna) — one-tap purchase without leaving
  TikTok.
- Two supported integration routes for our stack:
  1. **TikTok sales channel in Shopify** — catalog/inventory/order sync;
     TikTok orders appear in Shopify admin and Printify fulfills them like any
     other order. Shopify stays the source of truth.
  2. **Printify's direct TikTok Shop integration** — publish from the Printify
     catalog straight to TikTok Shop, with order routing to the fastest print
     provider.

## The constraint that shapes everything

TikTok Shop US fulfillment policy: **ship within 2 business days, deliver
within 6 business days**. Violations accrue points; repeated violations can
close the shop.

Our signature line is all-over-print cut-and-sew (AOP hoodies bp592, joggers
bp591, shorts bp1078, puffer bp934) and the backpack (bp1066, ArtsAdd —
produces in China). These cannot reliably meet a 6-day US delivery window and
are effectively **not TikTok-eligible**. Printify has a "TikTok eligible only"
catalog filter; the eligible set is mostly fast US-printed DTG basics.

**Consequence:** the TikTok line is an adjacent product set — US-printed DTG
hoodies/tees carrying the designs as front prints + the pocket text — not the
AOP garments. AOP stays on iamtoxico.com; TikTok gets fast-ship versions.
The existing fan-out machinery (scripts/fanout_previews.py pattern) can
generate previews on candidate eligible blueprints for review.

## Registration (Jason-only steps)

- Register as TikTok Shop US seller: individual (US ID + last-4 SSN + proof of
  address + bank account) or business (EIN + registration docs). Names on ID /
  bank / registration must match. Approval typically 24–48 h.
- Link/choose the TikTok account for the shop.

## Fees and influencer mechanics

- TikTok referral fee: ~6% per order.
- **Affiliate (built-in):**
  - *Open collaboration* — set a public commission rate (typical 10–15%, US
    average ~13%); any eligible creator can pick up products and post.
  - *Targeted collaboration* — invite specific creators at negotiated rates
    (typically 18–50%); much higher conversion.
  - TikTok handles tracking; creators paid ~15 days post-delivery.
- All-in cost stack (referral + affiliate + processing + COGS + returns)
  commonly lands at 35–45% of revenue — margin math per eligible blueprint
  before setting rates.
- Own media: the linked TikTok account tags products in videos/LIVEs with the
  same one-tap checkout. Later Hermes build: drop email → TikTok post.

## Execution checklist

1. [ ] Jason: register seller account (individual vs business decision).
2. [ ] Jason: link TikTok account.
3. [ ] Pick 2–3 TikTok-eligible blueprints (Printify catalog "TikTok eligible
       only" filter); fan out designs as previews for approval.
4. [ ] Install/configure the TikTok channel in Shopify; sync ONLY a curated
       TikTok collection (eligible products), not the AOP catalog.
5. [ ] Set handling time (1–2 business days) and confirm provider SLAs.
6. [ ] Margin math per product; set open-collab affiliate rate (~15% start).
7. [ ] First own-media posts + identify targeted-collab creators.

## Sources

- https://influencermarketinghub.com/shopify-x-tiktok-shop-ops/
- https://help.shopify.com/en/manual/online-sales-channels/tiktok/setup
- https://help.printify.com/hc/en-us/articles/24771076571153-TikTok-Shop-Fulfillment-Policy-Update
- https://help.printify.com/hc/en-us/articles/21840567074961-Which-products-are-suitable-for-TikTok-Shop-US
- https://printify.com/blog/printify-x-tiktok-shop/
- https://seller-us.tiktok.com/university/essay?knowledge_id=4186564050224897&lang=en
- https://canopymanagement.com/tiktok-shop-eligibility-what-you-need-to-get-started/
- https://www.dashboardly.io/post/tiktok-shop-affiliate-commissions-2026-payouts-clawbacks-profit-math
