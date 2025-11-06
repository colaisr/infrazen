# Selectel Account Information Analysis

**Date:** October 30, 2025  
**Purpose:** Comprehensive analysis of available Selectel account information via API

## Executive Summary

**Key Finding:** Selectel API provides **NO billing/financial data** via their public API. All billing information (balance, invoices, payments) is **only available through the web UI**, not programmatically.

## Comparison: Beget vs Selectel Account Information

### BEGET - Rich Financial API ✅💰

**Available via API:**
```json
{
  "account_id": "username",
  "customer_id": "12345",
  "balance": 1500.50,
  "currency": "RUB",
  "daily_rate": 68.1,
  "monthly_rate": 2044.2,
  "yearly_rate": 24000.00,
  "days_to_block": 22,
  "is_yearly_plan": false,
  "account_status": "active",
  "plan_name": "Premium"
}
```

**What we can display:**
- ✅ Current balance
- ✅ Daily spending rate
- ✅ Days until account block
- ✅ Plan type
- ✅ Account status

---

### SELECTEL - Infrastructure Only API ⚠️🏗️

**Available via API:**

#### 1. Basic Account Info (`/v3/accounts`)
```json
{
  "account": {
    "name": "478587",
    "enabled": true,
    "locked": false,
    "onboarding": false,
    "locks": []
  }
}
```

#### 2. Service Users (`/v3/users`)
```json
{
  "users": [
    {
      "name": "InfraZen",
      "id": "b9f534c98efc4a348f876870e1f331f7",
      "enabled": true
    }
  ]
}
```

#### 3. Projects (`/v3/projects`)
```json
{
  "projects": [
    {
      "id": "a21952ea620440838fb8a628d308e77a",
      "name": "third project",
      "enabled": true,
      "description": "",
      "url": "https://1572360.selvpc.ru"
    }
    // ... 2 more projects
  ]
}
```

#### 4. Capabilities & Restrictions (`/v3/capabilities`)

**Regions (13 total):**
- ru-1, ru-2, ru-3, ru-6, ru-7, ru-8, ru-9 (Russia)
- gis-1, gis-2 (GIS locations)
- uz-1, uz-2 (Uzbekistan - Tashkent)
- kz-1 (Kazakhstan - Almaty)
- ke-1 (Kenya - Nairobi)

**Account Restrictions:**
```json
{
  "flavor": {
    "max_vcpus": 8,
    "max_ram_mb": 65536,
    "max_root_gb": 512
  },
  "image": {
    "max_size_bytes": 1099511627776
  }
}
```

**Available Resource Types:** 49 different resource types including:
- Compute (CPUs, RAM, GPU types: A100, A5000, RTX4090, etc.)
- Storage (volumes, snapshots - basic/fast/universal)
- Network (floating IPs, subnets, load balancers)
- Databases (DBaaS)
- Kubernetes (MKS clusters)
- Container Registry

#### 5. Billing Info (`/v3/billing`)
```json
{
  "billing": {}
}
```
**Status:** ❌ EMPTY - No billing data available via API

---

## Billing Endpoint Investigation

### Endpoints Tested

All return **404 (Not Found):**
- ❌ `/v3/billing`
- ❌ `/v3/billing/balance`
- ❌ `/v3/billing/payments`
- ❌ `/v3/billing/invoices`
- ❌ `/v3/billing/estimate`
- ❌ `/v3/billing/consumption`
- ❌ `/v3/billing/history`
- ❌ `/v3/limits`
- ❌ `/v3/usage`
- ❌ `/v3/statistics`
- ❌ `/v3/account/balance`
- ❌ `/v3/account/limits`

All return **HTML (Web UI, not API):**
- ❌ `https://billing.selvpc.ru/api/v1/billing/balance`
- ❌ `https://billing.selvpc.ru/api/v1/billing/account`
- ❌ `https://my.selectel.ru/api/v3/billing/balance`

### OpenStack Keystone Service Catalog
- ✅ IAM token can be obtained
- ❌ Service catalog returns empty list (no billing service)

## What We CAN Display for Selectel

### Currently Available ✅

1. **Account Identity**
   - Account ID/Name: `478587`
   - Status: `enabled`, `locked`, `onboarding`
   - Lock status: `[]` (no locks)

2. **Service User**
   - Username: `InfraZen`
   - User ID: `b9f534c98efc4a348f876870e1f331f7`
   - Status: `enabled`

3. **Projects**
   - Total count: `3`
   - Project names: `third project`, `second project`, `My First Project`
   - Project URLs: Direct links to project dashboards
   - All projects: `enabled: true`

4. **Account Limits**
   - Max VM: 8 vCPUs, 64 GB RAM, 512 GB root disk
   - Max Image Size: 1 TB
   - Available regions: 13
   - Available resource types: 49

5. **Regional Coverage**
   - Russia: 7 regions
   - International: 6 regions (Uzbekistan, Kazakhstan, Kenya, GIS)

### NOT Available ❌

1. **Financial Data** (Web UI Only)
   - ❌ Account balance
   - ❌ Daily/Monthly spending rate
   - ❌ Days to account block
   - ❌ Payment history
   - ❌ Invoices
   - ❌ Cost estimates

2. **Billing History**
   - ❌ Historical spending trends
   - ❌ Payment dates
   - ❌ Invoice amounts

3. **Account Health Metrics**
   - ❌ Spending velocity
   - ❌ Budget alerts
   - ❌ Credit status

## Recommended Account Info to Store

Based on available API data, we should store:

### Minimal (Current) ✅
```json
{
  "account_id": "478587",
  "enabled": true,
  "locked": false,
  "onboarding": false
}
```

### Enhanced (Recommended) 💡
```json
{
  "account": {
    "id": "478587",
    "enabled": true,
    "locked": false,
    "onboarding": false,
    "locks": []
  },
  "service_user": {
    "name": "InfraZen",
    "id": "b9f534c98efc4a348f876870e1f331f7",
    "enabled": true
  },
  "projects": {
    "total_count": 3,
    "enabled_count": 3,
    "projects": [
      {
        "id": "a21952ea620440838fb8a628d308e77a",
        "name": "third project",
        "enabled": true,
        "url": "https://1572360.selvpc.ru"
      }
      // ... other projects
    ]
  },
  "account_limits": {
    "max_vcpus": 8,
    "max_ram_gb": 64,
    "max_root_disk_gb": 512,
    "max_image_size_gb": 1024
  },
  "regional_coverage": {
    "total_regions": 13,
    "russia_regions": 7,
    "international_regions": 6,
    "available_zones": 29
  },
  "resource_types_available": 49
}
```

## Calculated Financial Metrics

Since Selectel doesn't provide billing API, we must **calculate** financial data from synced resources:

### What We Can Calculate ✅

1. **Current Spending (from resources)**
   ```python
   daily_cost = sum(resource.daily_cost for resource in active_resources)
   monthly_cost = daily_cost * 30
   ```

2. **Resource Distribution**
   - Total VMs, volumes, load balancers
   - Cost per resource type
   - Cost per project

3. **Projected Monthly Spend**
   - Based on current active resources
   - Trend analysis from historical syncs

### What We CANNOT Calculate ❌

1. **Account Balance** - Web UI only
2. **Days to Block** - Web UI only
3. **Payment History** - Web UI only
4. **Actual Invoiced Amount** - May differ from resource sum

## UI Display Recommendations

### Account Info Card - BEGET Style
```
📊 Account Information
━━━━━━━━━━━━━━━━━━━━━━
Balance: 1,500.50 ₽
Daily Rate: 68.1 ₽/day
Days Remaining: 22 days
Account: beget_username
Plan: Premium
```

### Account Info Card - SELECTEL Style (Proposed)
```
📊 Account Information
━━━━━━━━━━━━━━━━━━━━━━
Account: 478587
Service User: InfraZen
Projects: 3 active
Max VM: 8 vCPUs / 64 GB RAM
Regions: 13 available
━━━━━━━━━━━━━━━━━━━━━━
💡 Note: Balance info available in web UI only
🔗 Open billing page →
```

**OR** (Resource-based):
```
📊 Account Information
━━━━━━━━━━━━━━━━━━━━━━
Account: 478587 (enabled)
Service User: InfraZen
Projects: 3 active
━━━━━━━━━━━━━━━━━━━━━━
Current Spending (calculated):
  Daily: 60.5 ₽/day
  Monthly: 1,814.4 ₽/month
  Based on 4 active resources
━━━━━━━━━━━━━━━━━━━━━━
💰 For balance, visit Selectel billing →
```

## Alternative: Web Scraping Billing Data

If we need actual balance data, we'd have to:

1. **Use Selenium/Playwright** to login and scrape `my.selectel.ru/billing`
2. **Parse the HTML** to extract balance
3. **Store in cache** with TTL (1 hour)
4. **Risks:**
   - Fragile (breaks when UI changes)
   - Requires browser automation
   - Slower performance
   - May violate ToS

**Recommendation:** ❌ **NOT worth it** - calculated spending from resources is sufficient for FinOps

## Conclusion

### What to Store in `provider_metadata`

```python
{
  "account_info": {
    "account_id": "478587",
    "account_name": "478587",
    "enabled": true,
    "locked": false,
    "onboarding": false
  },
  "service_user": {
    "name": "InfraZen",
    "id": "b9f534c98efc4a348f876870e1f331f7",
    "enabled": true
  },
  "projects_summary": {
    "total_count": 3,
    "enabled_count": 3,
    "project_names": ["third project", "second project", "My First Project"]
  },
  "account_limits": {
    "max_vcpus": 8,
    "max_ram_gb": 64,
    "max_root_disk_gb": 512
  },
  "regional_coverage": {
    "total_regions": 13,
    "total_zones": 29
  },
  "last_updated": "2025-10-30T18:41:40Z"
}
```

### Display Strategy

**For UI (connections page account info dropdown):**
- Show account ID, status, service user
- Show project count and names
- Show account limits
- Add link to Selectel billing web UI
- Calculate and show current spending from resources

**Skip:**
- Don't try to scrape billing balance
- Don't show empty billing fields
- Focus on infrastructure metrics instead

## API Endpoints Reference

### ✅ Working Endpoints

| Endpoint | Returns | Useful For |
|----------|---------|-----------|
| `GET /v3/accounts` | Account basic info | Account ID, status |
| `GET /v3/users` | Service users | API user info |
| `GET /v3/projects` | Projects list | Project count, URLs |
| `GET /v3/capabilities` | Regions, limits | Coverage, restrictions |
| `GET /v3/roles` | Roles | (Empty in our case) |

### ❌ Not Available

| Endpoint | Status | Notes |
|----------|--------|-------|
| `/v3/billing/*` | 404 | No billing API |
| `/v3/limits` | 404 | Use capabilities instead |
| `/v3/quotas` | 400 Deprecated | Use project-level |
| `billing.selvpc.ru/*` | HTML only | Web UI, not API |

### 🔍 OpenStack APIs (via IAM token)

Available but **limited usefulness** for account info:
- Keystone: Service catalog (empty for billing)
- Nova: Compute quotas (per-project)
- Cinder: Volume quotas (per-project)
- Neutron: Network quotas (per-project)

**Note:** OpenStack quotas are **limits**, not usage or billing data.

## Recommendations

### 1. Update `test_connection()` to Gather More Data ✅

Enhance connection test to collect:
- Account info
- Service user details
- Projects summary
- Account limits

### 2. Update `sync_resources()` to Store Account Metadata ✅

During sync, update `provider_metadata` with:
- Projects information
- Regional coverage
- Account limits
- Calculated spending (from resources)

### 3. UI Display Strategy 📊

**Account Info Dropdown Should Show:**
```
Account: 478587 (enabled)
Service User: InfraZen
━━━━━━━━━━━━━━━━━━━━
Projects: 3 active
  • third project
  • second project  
  • My First Project
━━━━━━━━━━━━━━━━━━━━
Account Limits:
  • Max VM: 8 vCPUs / 64 GB RAM
  • Max Disk: 512 GB
━━━━━━━━━━━━━━━━━━━━
Regions: 13 available
━━━━━━━━━━━━━━━━━━━━
💰 Current Spending:
  Daily: 60.5 ₽ (calculated)
  Monthly: 1,814.4 ₽ (projected)
  
🔗 View balance in Selectel UI →
```

### 4. Future Enhancement: Web Scraping (Optional) 🤔

**If balance is critical:**
- Implement browser automation (Selenium/Playwright)
- Scrape `my.selectel.ru/billing` page
- Extract balance, days remaining
- Cache for 1 hour
- **Trade-off:** Complexity vs. value

**Current Stance:** ❌ **Not recommended**
- Calculated spending from resources is sufficient
- Balance is less critical than spend rate
- Users can check balance in Selectel UI

## Next Steps

### Immediate (No Code Changes) ✅
- [x] Document available Selectel account information
- [x] Compare with Beget capabilities
- [x] Identify gaps

### Short Term (Simple Enhancement) 📝
- [ ] Update `test_connection()` to fetch projects
- [ ] Update `test_connection()` to fetch account limits
- [ ] Store enhanced metadata on connection add/edit
- [ ] Display projects and limits in account info dropdown

### Long Term (Advanced) 🚀
- [ ] Implement per-project cost breakdown
- [ ] Add regional cost analysis
- [ ] Show resource type distribution
- [ ] Optional: Billing scraper (if really needed)

## Selectel API Limitations

**Why no billing API?**
1. Selectel likely considers billing data sensitive
2. Billing managed through separate system (my.selectel.ru)
3. API focused on infrastructure management, not financial
4. Balance/invoices require web UI authentication

**This is NORMAL** - Many cloud providers separate:
- **Infrastructure APIs** (create VMs, manage resources)
- **Billing/Financial UIs** (view balance, pay invoices)

Examples:
- AWS: Billing data limited, need Cost Explorer API
- Azure: Separate billing portal
- GCP: Billing API exists but requires special permissions

## Conclusion

**What we have for Selectel:**
- ✅ Infrastructure info (projects, regions, limits)
- ✅ Resource-based cost calculations
- ❌ Direct balance/billing API

**This is sufficient for InfraZen FinOps because:**
1. We calculate spending from **actual resources** (more accurate)
2. We track **cost trends** from sync snapshots (historical data)
3. We provide **projected costs** from current usage
4. Balance info is **nice-to-have**, not **must-have** for optimization

**Beget advantage:**
- Richer account data makes UX slightly better
- Shows days to account block (helpful alert)

**But both providers:**
- ✅ Support full resource sync
- ✅ Provide cost data per resource
- ✅ Enable accurate FinOps analysis

The lack of billing API for Selectel is **not a blocker** for InfraZen's core value proposition.









