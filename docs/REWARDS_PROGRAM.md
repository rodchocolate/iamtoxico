# iamtoxico Rewards Program

## 🎁 Program Structure

### Earning Formula
```
Reward = lesser of ($5 OR 20% of profit)
```

| Product Price | Est. Profit | 20% of Profit | Reward Earned |
|---------------|-------------|---------------|---------------|
| $50 (affiliate 8%) | $4 | $0.80 | **$0.80** |
| $100 (affiliate 8%) | $8 | $1.60 | **$1.60** |
| $200 (affiliate 10%) | $20 | $4.00 | **$4.00** |
| $500 (affiliate 10%) | $50 | $10.00 | **$5.00** (capped) |
| $85 (owned 70%) | $60 | $12.00 | **$5.00** (capped) |

### Payout Thresholds

| Trigger | Amount | Notes |
|---------|--------|-------|
| **First Release** | $50 balance OR 10 items | Whichever comes first |
| **Subsequent Releases** | Every $100 | Automatic at threshold |
| **Arbitrary Release** | Owner discretion | Event-based (NYE, holidays, etc.) |

### Example: NYE Special
```
Normal threshold: $100
NYE Override: Raise to $200
Effect: Users accumulate more, bigger "gift" feel on Jan 1
```

---

## 💰 Profit Reality Check

### Affiliate Commission Rates (Typical)

| Network/Brand | Commission | Cookie | Signup Difficulty |
|---------------|------------|--------|-------------------|
| **Amazon Associates** | 1-4% (varies by category) | 24 hours | Easy, instant |
| **Rakuten** | 3-12% (brand dependent) | 30 days | Medium, approval needed |
| **ShareASale** | 5-15% | 30-90 days | Medium |
| **CJ Affiliate** | 5-15% | 30 days | Medium |
| **Impact** | 5-20% | Varies | Medium |
| **Direct Brand Programs** | 8-20% | Varies | Hard, relationship-based |

### By Product Category (Realistic)

| Category | Typical Commission | Your Catalog Est. |
|----------|-------------------|-------------------|
| **Luxury Fashion** (Ferragamo, Gucci) | 5-8% via Rakuten | $40-75 per $850 sale |
| **Athletic** (Nike, Adidas) | 5-7% | $6-15 per $100-200 sale |
| **Footwear General** | 6-10% | $8-20 per $100-200 sale |
| **Home/Lifestyle** | 4-8% | $4-16 per $100-200 sale |
| **Amazon Products** | 1-4% | $1-6 per $50-150 sale |
| **Owned Products** | 65-80% margin | $45-65 per $85 sale |

### Honest Assessment

| Aspect | Reality |
|--------|---------|
| **Your 8-10% estimates** | ✅ Achievable for mid-tier brands via Rakuten/ShareASale |
| **Amazon rates** | ⚠️ Lower than estimated (1-4%, not 6-8%) |
| **Luxury brand rates** | ✅ Often 5-10% but harder approval |
| **Cookie duration** | ⚠️ Many are 24h-7d, not 30d |
| **Owned product margins** | ✅ 70% is realistic for white-label |

---

## 🚀 Affiliate Launch Timeline

### Week 1: Instant Launch (Amazon)
```
Day 1: Apply to Amazon Associates
Day 1-2: Approved (usually instant for US)
Day 2: Update all Amazon product URLs with affiliate tags
```
**Products Ready**: ~20 (budget tier items)

### Week 2-3: Major Networks
```
Apply to:
- Rakuten (covers: Nike, Ferragamo, UGG, Birkenstock, Cole Haan, etc.)
- ShareASale (covers: Allbirds, misc brands)
- CJ Affiliate (covers: Brooks, ASICS, various)
- Impact (covers: Adidas, Lululemon)

Approval time: 3-7 days typical
```
**Products Ready**: ~100+ once approved

### Week 3-4: Direct Brand Programs
```
Apply to individual brand programs:
- Nike Affiliate Program (separate from Rakuten)
- Adidas Creators (Impact)
- New Balance (direct)
- Hoka (direct)
- On Running (direct)
```
**Products Ready**: Remainder

### Quick Start Priority Order

| Priority | Brand/Network | Products Covered | Est. Approval |
|----------|---------------|------------------|---------------|
| 1 | Amazon | Budget tier, basics | 1-2 days |
| 2 | Rakuten | Ferragamo, Gucci, UGG, Nike, major brands | 5-7 days |
| 3 | ShareASale | Allbirds, misc | 3-5 days |
| 4 | Nike Direct | All Nike/Jordan | 7-14 days |
| 5 | Brand-specific | Various | 7-30 days |

---

## 📊 Revenue Projections (Honest)

### Scenario: 100 Monthly Visitors, 2% Conversion

| Metric | Conservative | Moderate | Optimistic |
|--------|--------------|----------|------------|
| Orders/month | 2 | 2 | 2 |
| Avg order value | $80 | $150 | $250 |
| Avg commission | 5% | 8% | 10% |
| **Monthly affiliate revenue** | $8 | $24 | $50 |
| Rewards liability (20%) | $1.60 | $4.80 | $10 |
| **Net to you** | $6.40 | $19.20 | $40 |

### Breakeven for Rewards Program
```
First payout trigger: $50 user balance
At 20% liability: You need $250 in profit to fund one $50 payout
At $24/month affiliate revenue: ~10 months to first user payout
```

### With Owned Products (Game Changer)

| Metric | Affiliate Only | With 20% Owned Sales |
|--------|----------------|----------------------|
| Orders/month | 2 | 2 (0.4 owned) |
| Revenue | $160 | $160 + $34 owned |
| Profit | $24 | $24 + $24 (owned) = $48 |
| Rewards liability | $4.80 | $9.60 |
| **Net to you** | $19.20 | $38.40 |

---

## ⚡ Action Items for Launch

### This Week
- [ ] Apply to Amazon Associates (today)
- [ ] Apply to Rakuten (today)
- [ ] Apply to ShareASale (today)
- [ ] Set up tracking pixel/link management

### Next Week
- [ ] Update catalog URLs with affiliate links as approved
- [ ] Apply to Nike, Adidas, NB direct programs
- [ ] Test tracking on 3-5 products

### Before NYE
- [ ] All major affiliates active
- [ ] Rewards program UI in valet
- [ ] Set NYE threshold to $200

---

## 🔧 Technical Implementation

### Rewards Tracking Schema
```json
{
  "user_id": "uuid",
  "balance": 0.00,
  "lifetime_earned": 0.00,
  "items_purchased": 0,
  "threshold_releases": [50, 100, 200, ...],
  "next_release_at": 50,
  "custom_hold_until": null,
  "transactions": [
    {
      "date": "2025-12-01",
      "order_id": "abc123",
      "product": "ferragamo-gancini-loafer",
      "sale_amount": 850,
      "profit": 68,
      "reward": 5.00,
      "type": "earn"
    }
  ]
}
```

### Release Logic
```python
def check_release(user):
    if user.custom_hold_until and datetime.now() < user.custom_hold_until:
        return False  # Owner override active
    
    if user.items_purchased >= 10 and user.balance >= 50:
        return True  # First release trigger
    
    if user.balance >= user.next_release_at:
        return True  # Standard threshold
    
    return False
```

---

## 📝 Summary

| Question | Answer |
|----------|--------|
| **How solid are profit numbers?** | Conservative 5-8% is realistic. Your 8-10% estimates work for mid-tier. Amazon is lower (1-4%). Owned products are where real margin lives. |
| **How quick to launch affiliates?** | Amazon: 1-2 days. Major networks: 5-7 days. Full catalog coverage: 2-3 weeks. |
| **Rewards program viable?** | Yes, but owned products needed to fund payouts sustainably. Pure affiliate = slow accumulation. |

---

*Last Updated: November 28, 2025*
