# Yandex Cloud Hidden Billing API Discovery

**Date:** 2025-10-27  
**Source:** HAR file analysis (center.yandex.cloud.har)  
**Investigation:** How Yandex Console gets consumption/billing data  

---

## 🎯 Key Discovery

**Yandex Cloud Console uses an UNDOCUMENTED internal Gateway API to fetch billing data:**

```
POST https://center.yandex.cloud/gateway/root/billing/getServiceUsage
```

This endpoint returns **ACTUAL consumption costs** - NOT estimates!

---

## 📊 API Endpoints Found (Internal Gateway)

### 1. Get Service Usage (Consumption Data) ⭐
```
POST https://center.yandex.cloud/gateway/root/billing/getServiceUsage
```

**Request:**
```json
{
  "accountId": "dn2mqqf5ahht646mov3m",
  "startDate": "2025-10-26",
  "endDate": "2025-10-26",
  "aggregationPeriod": "day",
  "labels": {},
  "skuIds": [],
  "cloudIds": [],
  "folderIds": []
}
```

**Response:**
```json
{
  "usageReport": {
    "entitiesData": {
      "dn21qssbrdtcaus362kp": {
        "entityCost": 6.2208,
        "entityCredit": -6.2208,
        "entityExpense": 0,
        "meta": {
          "description": "Virtual Private Cloud",
          "name": "cloud_network"
        },
        "periodic": [
          {
            "cost": 6.2208,
            "credit": -6.2208,
            "expense": 0,
            "period": "2025-10-26"
          }
        ]
      },
      "dn22pas77ftg9h3f2djj": {
        "entityCost": 86.097593285,
        "entityCredit": -86.097593285,
        "entityExpense": 0,
        "meta": {
          "description": "Compute Cloud",
          "name": "compute"
        },
        "periodic": [
          {
            "cost": 86.097593285,
            "credit": -86.097593285,
            "expense": 0,
            "period": "2025-10-26"
          }
        ]
      }
    },
    "totalCost": 92.318393285,
    "totalCredit": -92.318393285,
    "totalExpense": 0
  }
}
```

**What you get:**
- ✅ **Actual costs per service** (Compute Cloud: 86.10₽, VPC: 6.22₽)
- ✅ **Credits/discounts applied**
- ✅ **Net expense** (cost - credit)
- ✅ **Daily breakdown** by period
- ✅ **Total costs**
- ✅ **Service metadata** (name, description)

**This is EXACTLY what we need!**

---

### 2. Get Account Info
```
POST https://center.yandex.cloud/gateway/root/billing/getAccount
```

**Request:**
```json
{
  "accountId": "dn2mqqf5ahht646mov3m",
  "view": "full"
}
```

**Response:** Full billing account details (balance, payment type, status, etc.)

---

### 3. List Billable Entities (Cloud Bindings)
```
POST https://center.yandex.cloud/gateway/root/billing/batchListBillableEntities
```

**Request:**
```json
{
  "billingAccountId": "dn2mqqf5ahht646mov3m",
  "serviceInstanceType": "cloud",
  "pageSize": 3000
}
```

**Response:** Which clouds are linked to billing account

---

### 4. Get Usage Metadata
```
POST https://center.yandex.cloud/gateway/root/billing/getUsageMeta
```

**Request:**
```json
{
  "accountId": "dn2mqqf5ahht646mov3m"
}
```

**Response:** Available services and usage metadata

---

### 5. Get Folder Usage Metadata
```
POST https://center.yandex.cloud/gateway/root/billing/getFolderUsageMeta
```

**Request:**
```json
{
  "accountId": "dn2mqqf5ahht646mov3m",
  "cloudId": "b1gd6sjehrrhbak26cl5",
  "pageSize": 500
}
```

**Response:** List of folders with usage data

---

## 🔒 Authentication Requirements

### ❌ Problem: Can't Use Service Account IAM Token

When trying to call the Gateway API with IAM token:
```bash
Authorization: Bearer {iam_token}
```

**Result:** `401 Unauthorized` with error:
```json
{"code": "NEED_RESET"}
```

### ✅ What the Browser Uses:

**Required Headers:**
```
x-csrf-token: ac4fc5381d8d3ca960971654bc81bf88bf71a38f:1761588305
Cookie: Session_id=...;yandexuid=...;...
```

**Authentication Method:**
- Browser session cookies (user-based, not service account)
- CSRF tokens
- Same-origin requests

**Conclusion:** This API is **NOT designed for programmatic access**. It's an internal frontend API.

---

## 🔍 Comparison: Public API vs Gateway API

| Feature | Public Billing API | Internal Gateway API |
|---------|-------------------|---------------------|
| **Base URL** | `billing.api.cloud.yandex.net` | `center.yandex.cloud/gateway` |
| **Authentication** | ✅ IAM token (service account) | ❌ Browser session cookies |
| **Documented** | ✅ Yes | ❌ No (internal only) |
| **Per-service costs** | ❌ No | ✅ Yes! |
| **Usage data** | ❌ No | ✅ Yes! |
| **Historical data** | ❌ No | ✅ Yes! |
| **Discounts/credits** | ❌ No | ✅ Yes! |
| **Programmatic access** | ✅ Yes | ❌ No (browser only) |

---

## 💡 Why This Matters

### What We Learned:

1. **Cost data DOES exist** in Yandex Cloud - it's not impossible to get!
2. **Yandex Console accesses it** through an internal Gateway API
3. **The data includes:**
   - Per-service costs (exactly what we need!)
   - Daily breakdowns
   - Credits and discounts
   - Net expenses

### The Problem:

The Gateway API **requires browser-based authentication** (cookies + CSRF):
- ❌ Can't use service account IAM tokens
- ❌ Not documented publicly
- ❌ Designed for web UI, not API access

---

## 🎯 Possible Solutions

### Option A: Stick with Estimated Costs ✅ (Current)

**Pros:**
- ✅ Works immediately
- ✅ No authentication issues
- ✅ Reasonably accurate (based on public pricing)

**Cons:**
- ❌ Not actual billing data
- ❌ Missing credits/discounts
- ❌ Can't detect unexpected charges

**Status:** **Recommended for now**

---

### Option B: Selenium/Headless Browser Scraping

Use Selenium to:
1. Log in to Yandex Console (user credentials)
2. Navigate to billing page
3. Extract data from DOM/XHR calls
4. Parse and store

**Pros:**
- ✅ Can access the real data
- ✅ Works with current authentication

**Cons:**
- ❌ Requires user credentials (not service account)
- ❌ Breaks if UI changes
- ❌ Slow and resource-intensive
- ❌ Against ToS?

**Status:** **Not recommended** (fragile, requires user creds)

---

### Option C: Yandex Query + Object Storage Export

Setup billing export:
1. Console → Billing → Export Settings
2. Export to Object Storage bucket
3. Parse CSV files

**Pros:**
- ✅ Official Yandex-supported method
- ✅ Actual billing data
- ✅ Complete history

**Cons:**
- ❌ Requires manual setup per user
- ❌ Delayed (exports daily/weekly)
- ❌ Need to parse CSV files
- ❌ Not real-time

**Status:** **Good for advanced users**

---

### Option D: Wait for Yandex to Add Public API

Yandex might add usage/cost endpoints to public API in the future.

**Pros:**
- ✅ Would be official and supported

**Cons:**
- ❌ No timeline
- ❌ May never happen

**Status:** **Not actionable**

---

## 📋 What Yandex SHOULD Do

Based on this investigation, Yandex Cloud should:

1. **Add usage data to public Billing API:**
   ```
   GET /billing/v1/billingAccounts/{id}/usage?startDate=...&endDate=...
   ```

2. **Document the endpoints** that already exist

3. **Support service account authentication** for billing data

4. **Follow AWS/GCP/Azure patterns** for cost reporting APIs

---

## 🎯 Current Recommendation for InfraZen

**Continue using estimated costs** because:

1. ✅ Gateway API requires browser auth (can't use service accounts)
2. ✅ Public API doesn't expose cost data
3. ✅ Estimates are good enough for FinOps decisions
4. ✅ No better alternative without manual setup

**Consider in the future:**
- Allow users to setup Object Storage export (Option C)
- Update documentation to explain Yandex limitations
- Monitor for Yandex API updates

---

## 📊 Data Sample from HAR File

**Date:** October 26, 2025
**Billing Account:** dn2mqqf5ahht646mov3m (account-219)

**Services with Costs:**
| Service | Cost | Credit | Net Expense |
|---------|------|--------|-------------|
| Compute Cloud | 86.10 ₽ | -86.10 ₽ | 0.00 ₽ |
| Virtual Private Cloud | 6.22 ₽ | -6.22 ₽ | 0.00 ₽ |
| Cloud DNS | 0.00 ₽ | 0.00 ₽ | 0.00 ₽ |
| **TOTAL** | **92.32 ₽** | **-92.32 ₽** | **0.00 ₽** |

*Note: 100% credit applied (likely promotional or grant balance)*

---

## 🔧 Technical Details

**Full HAR Analysis:**
- Total HTTP requests captured: 140
- Billing-related API calls: 30
- Key endpoint discovered: `getServiceUsage`

**Request Flow:**
1. Page load → `GET /billing/accounts/{id}/detail`
2. Get account info → `POST /gateway/root/billing/getAccount`
3. Get linked clouds → `POST /gateway/root/billing/batchListBillableEntities`
4. Get usage metadata → `POST /gateway/root/billing/getUsageMeta`
5. **Get consumption data** → `POST /gateway/root/billing/getServiceUsage` ⭐
6. Render charts and tables

---

## 📚 References

- **HAR File:** `haar/center.yandex.cloud.har`
- **Screenshots:** Billing console showing 92.32₽ consumption
- **Billing Account:** dn2mqqf5ahht646mov3m
- **Date Range:** 2025-10-26 to 2025-10-26

---

## ✅ Conclusion

**What We Found:**
- ✅ Yandex HAS cost/usage data available
- ✅ Console accesses it via internal Gateway API
- ✅ Data includes per-service costs, credits, daily breakdowns

**Why We Can't Use It:**
- ❌ Gateway API requires browser authentication
- ❌ Service account IAM tokens don't work
- ❌ Not documented or intended for programmatic access

**What To Do:**
- ✅ Continue with estimated costs (current approach)
- ✅ Document this limitation for users
- ⚠️ Consider Object Storage export for advanced users
- 🔮 Monitor Yandex API updates for future improvements

**The investigation confirms:** Our current approach (estimated costs) is the **ONLY practical option** for service account-based integrations with Yandex Cloud.



