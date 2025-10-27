# Yandex Cloud Billing API - What We Can Actually Get

**Investigation Date:** 2025-10-27  
**Connection:** yc (ID: 117)  
**Billing Account:** dn2mqqf5ahht646mov3m (account-219)  

---

## ✅ What the Billing API PROVIDES:

### 1. Billing Account Information
```
GET /billing/v1/billingAccounts/{billing_account_id}
```

**Response:**
```json
{
  "id": "dn2mqqf5ahht646mov3m",
  "name": "account-219",
  "active": true,
  "createdAt": "2025-10-25T15:01:25Z",
  "countryCode": "RU",
  "currency": "RUB",
  "balance": "0"
}
```

**What you get:**
- ✅ Account ID
- ✅ Account name
- ✅ Active status
- ✅ Currency (RUB, USD, etc.)
- ✅ Country
- ✅ Current balance
- ✅ Creation date

**What you DON'T get:**
- ❌ Total spending
- ❌ Monthly costs
- ❌ Daily costs
- ❌ Cost breakdown

---

### 2. List All Billing Accounts
```
GET /billing/v1/billingAccounts
```

**Response:**
```json
{
  "billingAccounts": [
    {
      "id": "...",
      "name": "...",
      ...
    }
  ]
}
```

**What you get:**
- ✅ All accessible billing accounts
- ✅ Same info as #1 for each account

---

### 3. SKU Pricing Catalog
```
GET /billing/v1/skus?pageSize=1000
```

**Response:**
```json
{
  "skus": [
    {
      "id": "dn201l4ki383a9per2i7",
      "name": "BareMetal. Server type HA-i302-S-10G with 6 month rental period",
      "serviceId": "dn2jfbheag6vvls7oplt",
      "pricingVersions": [
        {
          "type": "STREET_PRICE",
          "pricingExpressions": [
            {
              "rates": [
                {
                  "startPricingQuantity": "0",
                  "unitPrice": "123.45",
                  "currency": "RUB"
                }
              ]
            }
          ],
          "effectiveTime": "2024-01-01T00:00:00Z"
        }
      ]
    }
  ],
  "nextPageToken": "..."
}
```

**What you get:**
- ✅ Complete pricing catalog for ALL Yandex services
- ✅ SKU IDs and names
- ✅ Service IDs
- ✅ Pricing rates per unit
- ✅ Currency
- ✅ Effective dates
- ✅ Paginated (can fetch all SKUs)

**Useful for:**
- 💡 Building a pricing calculator
- 💡 More accurate cost estimates
- 💡 Matching resource types to prices

---

## ❌ What the Billing API DOES NOT PROVIDE:

All of these endpoints return **404 Not Found**:

```
❌ /billing/v1/billingAccounts/{id}/usage           - No usage data
❌ /billing/v1/billingAccounts/{id}/consumption     - No consumption data
❌ /billing/v1/billingAccounts/{id}/costs           - No cost data
❌ /billing/v1/billingAccounts/{id}/spending        - No spending data
❌ /billing/v1/billingAccounts/{id}/invoices        - No invoices
❌ /billing/v1/billingAccounts/{id}/statements      - No statements
❌ /billing/v1/billingAccounts/{id}/export          - No export API
❌ /billing/v1/billingAccounts/{id}/exports         - No exports list
❌ /billing/v1/billingAccounts/{id}/serviceUsage    - No service usage
❌ /billing/v1/billingAccounts/{id}/skuUsage        - No SKU usage
❌ /billing/v1/billingAccounts/{id}/budgets         - No budgets
❌ /billing/v1/billingAccounts/{id}/bindedClouds    - No cloud bindings
❌ /billing/v1/billingAccounts/{id}/services        - No services list
❌ /billing/v1/billingAccounts/{id}/skus            - No SKU usage
❌ /billing/v1/billingAccounts/{id}/customer        - No customer info
```

**You CANNOT get:**
- ❌ Per-resource costs
- ❌ Historical spending data
- ❌ Cost breakdown by service
- ❌ Cost breakdown by resource
- ❌ Daily/monthly totals
- ❌ Usage metrics
- ❌ Invoices
- ❌ Billing statements
- ❌ Export data via API

---

## 🔍 Comparison with Other Providers

### Selectel (Billing-First):
```
✅ GET /billing/v1/costs?hours=2
   Returns: ALL resources with actual costs from billing
   
✅ Per-resource costs available
✅ Actual billed amounts
✅ Can detect zombie resources (still being charged but deleted)
```

### Beget (Billing-First):
```
✅ GET /v1/billing
   Returns: Account balance and costs
   
✅ GET /v1/vps/{id}/billing
   Returns: Per-VPS costs
   
✅ Actual billed amounts per resource
```

### Yandex Cloud:
```
❌ No per-resource cost API
❌ No usage data API
❌ No billing breakdown API

✅ Only: Account info + Pricing catalog
```

---

## 💡 What This Means for InfraZen

### Current Approach (Estimated Costs):
```python
# From: app/providers/yandex/service.py

def _estimate_instance_cost(vcpus, ram_gb, storage_gb):
    cpu_cost = vcpus * 1.50 * 24          # ₽/day
    ram_cost = ram_gb * 0.40 * 24         # ₽/day  
    storage_cost = storage_gb * 0.0025 * 24  # ₽/day
    
    return cpu_cost + ram_cost + storage_cost
```

**Status:** ✅ **This is CORRECT and NECESSARY**

Yandex Cloud API does not provide per-resource costs, so calculation is the ONLY option.

---

## 🎯 Possible Improvements

### Option A: Use SKU Pricing Catalog (Better Estimates)
Instead of hardcoded rates, fetch actual SKU prices:

```python
# Fetch SKU catalog from /billing/v1/skus
# Match resource type to SKU
# Use actual current pricing
# Update estimates dynamically
```

**Pros:**
- ✅ More accurate than hardcoded rates
- ✅ Automatically updates when Yandex changes prices
- ✅ Can handle regional pricing differences

**Cons:**
- ⚠️ Still estimates, not actual billing
- ⚠️ Need to map resources to correct SKUs
- ⚠️ SKU catalog is large (requires caching)

### Option B: Billing Export to Object Storage
Yandex allows exporting billing data to S3-compatible storage:

```
Console → Billing → Export Settings
  → Enable export to Object Storage bucket
  → Parse CSV/JSON files manually
```

**Pros:**
- ✅ Actual billing data (not estimates)
- ✅ Complete cost breakdown
- ✅ Historical data

**Cons:**
- ❌ Requires manual setup per billing account
- ❌ Delayed (exports happen daily/weekly)
- ❌ Need to parse CSV files
- ❌ Requires Object Storage bucket + permissions

### Option C: Keep Current Estimates (Recommended)
**Why:**
- ✅ Works immediately
- ✅ No additional setup
- ✅ Good enough for FinOps decisions
- ✅ Consistent with other resource-discovery providers
- ✅ Easy to maintain

**Just mark costs as "ESTIMATED" in UI**

---

## 📊 Summary Table

| Data Type | Available? | Endpoint | Notes |
|-----------|-----------|----------|-------|
| **Billing account info** | ✅ Yes | `/billingAccounts/{id}` | Basic info only |
| **Account balance** | ✅ Yes | `/billingAccounts/{id}` | Current balance |
| **Pricing catalog (SKUs)** | ✅ Yes | `/skus` | All services |
| **Per-resource costs** | ❌ No | N/A | Not exposed |
| **Total spending** | ❌ No | N/A | Not exposed |
| **Usage metrics** | ❌ No | N/A | Not exposed |
| **Invoices** | ❌ No | N/A | Not exposed |
| **Cost breakdown** | ❌ No | N/A | Not exposed |
| **Historical data** | ❌ No | N/A | Not exposed |

---

## 🎯 Conclusion

**For yc-it connection (3,787.20 RUB/day):**

The costs shown are **ESTIMATED** because:
1. ✅ Yandex Billing API does not expose per-resource costs
2. ✅ This is a **limitation of Yandex Cloud**, not InfraZen
3. ✅ The estimation method is reasonable and necessary
4. ✅ Actual costs can only be obtained via:
   - Manual download from Yandex Console
   - Billing export to Object Storage (requires setup)
   - Invoice PDFs (manual)

**Recommendation:**
- Keep current estimated cost approach
- Add "ESTIMATED" badge in UI for Yandex resources
- Consider implementing SKU catalog for better accuracy (future enhancement)
- Document limitation clearly for users

---

## 📚 References

- **Yandex Cloud Billing API:** https://cloud.yandex.com/en/docs/billing/api-ref/
- **Yandex Cloud Pricing:** https://cloud.yandex.com/en/prices
- **Billing Export:** https://cloud.yandex.com/en/docs/billing/operations/get-folder-report



