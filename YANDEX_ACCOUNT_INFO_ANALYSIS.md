# Yandex Cloud Account Information Analysis

**Date:** October 30, 2025  
**Purpose:** Comprehensive analysis of available Yandex Cloud account information via API

## Executive Summary

**Key Finding:** Yandex Cloud provides **excellent organizational/infrastructure data** but **NO billing/financial data** via their public API. Like Selectel, all billing information is only available through the web console.

## What We Found (via API)

### 1. Organization Information ✅

```json
{
  "id": "bpf24f7co4nlgheig7o0",
  "name": "itlteam",
  "title": "I-Techlabs",
  "description": "ООО \"АЙ-ТЕКЛАБС\"",
  "createdAt": "2022-03-02T09:49:41.836737Z"
}
```

**Endpoint:** `https://organization-manager.api.cloud.yandex.net/organization-manager/v1/organizations`

**Available:**
- ✅ Organization name (display name)
- ✅ Legal entity name (company registration)
- ✅ Organization ID
- ✅ Creation date

### 2. Folder Information ✅

```json
{
  "id": "b1gkosunk7kknbq1tubv",
  "cloudId": "b1goskl8180ifslar8gc",
  "name": "itlteam",
  "status": "ACTIVE",
  "createdAt": "2022-03-02T11:52:32Z"
}
```

**Endpoint:** `https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders/{folder_id}`

**Available:**
- ✅ Folder name
- ✅ Parent cloud ID
- ✅ Status (ACTIVE/ARCHIVED)
- ✅ Creation date

### 3. Service Accounts ✅

**Endpoint:** `https://iam.api.cloud.yandex.net/iam/v1/serviceAccounts?folderId={folder_id}`

**Statistics:**
- Total service accounts: **49**
- Recently authenticated: **35** (active usage)
- Current service account: **infrazen** ("анализ затрат")

**Sample accounts:**
- `unukprod` - bucket access (last auth: 2025-10-30)
- `kubesvc` - Kubernetes (last auth: 2025-10-30)
- `terraform` - Terraform state (last auth: 2025-10-30)
- `infrazen` - Cost analysis (last auth: 2025-10-30)

### 4. Managed Services ✅

**Endpoint:** Various managed service APIs

**Counts:**
- Kubernetes clusters: **1**
- PostgreSQL clusters: **2**
- Kafka clusters: **1**
- **Total:** 4 managed service clusters

### 5. Availability Zones ✅

**Endpoint:** `https://compute.api.cloud.yandex.net/compute/v1/zones`

```json
{
  "zones": [
    {"id": "ru-central1-a", "status": "UP"},
    {"id": "ru-central1-b", "status": "UP"},
    {"id": "ru-central1-c", "status": "DOWN"},
    {"id": "ru-central1-d", "status": "UP"}
  ]
}
```

- Total zones: **4**
- Active zones: **3** (UP status)
- Down zones: **1** (ru-central1-c)

### 6. Resources (from sync) ✅

- Total resources synced: **65**
- Resource types: VMs, disks, snapshots, load balancers, managed clusters, etc.
- Calculated daily cost: **115.7 ₽/день**

## What We DON'T Have Access To ❌

### 1. Billing Data (Web Console Only)

**Endpoint tried:** `https://billing.api.cloud.yandex.net/billing/v1/billingAccounts`  
**Response:** `{}` (empty)

**Not available:**
- ❌ Account balance
- ❌ Daily/monthly spending rate from billing
- ❌ Payment history
- ❌ Invoices
- ❌ Credits or grants
- ❌ Committed use discounts
- ❌ Days until credit exhaustion

### 2. Cloud-Level Details (Permission Denied)

**Endpoint tried:** `https://resource-manager.api.cloud.yandex.net/resource-manager/v1/clouds/{cloud_id}`  
**Response:** `403 Permission Denied`

**Reason:** Service account has **folder-level** access, not cloud-level access

**Not available:**
- ❌ Cloud name
- ❌ Cloud metadata
- ❌ Cloud-wide quotas
- ❌ Cloud labels

## Comparison: Beget vs Selectel vs Yandex

| Data Category | Beget | Selectel | Yandex |
|--------------|-------|----------|---------|
| **Financial** |
| Balance API | ✅ Yes | ❌ No | ❌ No |
| Billing Rates API | ✅ Yes | ❌ No | ❌ No |
| Days to Block | ✅ Yes | ❌ No | ❌ No |
| **Organizational** |
| Legal Entity | ❌ No | ❌ No | ✅ Yes |
| Organization Name | ❌ No | ❌ No | ✅ Yes |
| Projects/Folders | ❌ No | ✅ 3 | ✅ 1 |
| Service Accounts | ❌ No | ✅ 1 | ✅ 49 |
| Managed Services | ❌ No | ❌ No | ✅ 4 clusters |
| Regions/Zones | ❌ No | ✅ 13 | ✅ 4 |
| **Calculated** |
| Resource Count | ✅ 7 | ✅ 4 | ✅ 65 |
| Daily Cost | ✅ 68.1 ₽ | ✅ 60.5 ₽ | ✅ 115.7 ₽ |

## Recommended Display for Yandex

### Simplified Version (Focused on FinOps)

```
📊 Информация об аккаунте
━━━━━━━━━━━━━━━━━━━━━━
Организация: I-Techlabs
  ООО "АЙ-ТЕКЛАБС"
━━━━━━━━━━━━━━━━━━━━━━
Folder: itlteam (активен)
Сервис-аккаунт: infrazen
━━━━━━━━━━━━━━━━━━━━━━
Управляемые сервисы: 4
  • Kubernetes: 1
  • PostgreSQL: 2
  • Kafka: 1
━━━━━━━━━━━━━━━━━━━━━━
Billing: 115.7 ₽/день
Прогноз месяц: 3,470.1 ₽/месяц
Ресурсов: 65
━━━━━━━━━━━━━━━━━━━━━━
🔗 Баланс и расходы →
```

### Detailed Version (If Space Permits)

```
📊 Информация об аккаунте
━━━━━━━━━━━━━━━━━━━━━━
Организация: I-Techlabs
  ООО "АЙ-ТЕКЛАБС"
  ID: bpf24f7co...
━━━━━━━━━━━━━━━━━━━━━━
Folder: itlteam
Cloud: b1goskl8180ifslar8gc
Статус: ACTIVE
━━━━━━━━━━━━━━━━━━━━━━
Сервис-аккаунт: infrazen
  Описание: анализ затрат
  Последняя авторизация: 30.10.2025
  Всего аккаунтов в folder: 49
━━━━━━━━━━━━━━━━━━━━━━
Управляемые сервисы:
  • Kubernetes: 1 кластер
  • PostgreSQL: 2 кластера
  • Kafka: 1 кластер
━━━━━━━━━━━━━━━━━━━━━━
Зоны доступности: 3 из 4 активны
  ✅ ru-central1-a
  ✅ ru-central1-b
  ❌ ru-central1-c (DOWN)
  ✅ ru-central1-d
━━━━━━━━━━━━━━━━━━━━━━
Billing: 115.7 ₽/день
Прогноз месяц: 3,470.1 ₽/месяц
Ресурсов: 65
━━━━━━━━━━━━━━━━━━━━━━
🔗 Баланс и расходы →
```

## What to Store in `provider_metadata`

### Recommended Structure

```python
{
  "account_info": {
    "organization": {
      "id": "bpf24f7co4nlgheig7o0",
      "name": "itlteam",
      "title": "I-Techlabs",
      "description": "ООО \"АЙ-ТЕКЛАБС\"",
      "created_at": "2022-03-02T09:49:41.836737Z"
    },
    "folder": {
      "id": "b1gkosunk7kknbq1tubv",
      "name": "itlteam",
      "cloud_id": "b1goskl8180ifslar8gc",
      "status": "ACTIVE",
      "created_at": "2022-03-02T11:52:32Z"
    },
    "service_account": {
      "name": "infrazen",
      "id": "ajem3a0uhhooq9u4pvkd",
      "description": "анализ затрат",
      "last_authenticated_at": "2025-10-30T16:40:00Z"
    },
    "service_accounts_summary": {
      "total_count": 49,
      "recently_used_count": 35
    },
    "managed_services": {
      "kubernetes_clusters": 1,
      "postgresql_clusters": 2,
      "kafka_clusters": 1,
      "total_clusters": 4
    },
    "zones": {
      "total": 4,
      "active": 3,
      "down": 1,
      "active_zones": ["ru-central1-a", "ru-central1-b", "ru-central1-d"]
    }
  }
}
```

## API Endpoints Reference

### ✅ Working Endpoints

| Endpoint | Data Returned | Useful For |
|----------|---------------|-----------|
| `/organization-manager/v1/organizations` | Organization list | Legal entity, company name |
| `/resource-manager/v1/folders/{id}` | Folder details | Folder name, cloud ID, status |
| `/iam/v1/serviceAccounts?folderId={id}` | Service accounts | IAM complexity, active accounts |
| `/compute/v1/zones` | Availability zones | Regional availability |
| Managed services APIs | Clusters | K8s, PostgreSQL, Kafka counts |

### ❌ Not Available

| Endpoint | Status | Data |
|----------|--------|------|
| `/billing/v1/billingAccounts` | 200 but `{}` | No billing data |
| `/resource-manager/v1/clouds/{id}` | 403 | Permission denied |
| `/billing/v1/balance` | N/A | Doesn't exist |
| `/billing/v1/invoices` | N/A | Doesn't exist |

## Key Differences from Beget & Selectel

### Beget
- ✅ **Rich billing** API (balance, rates, days to block)
- ❌ No organizational structure (single account)
- ❌ No managed services

### Selectel
- ❌ No billing API
- ✅ **Multi-project** structure (3 projects)
- ✅ International regions (13 regions)
- ❌ No organization entity

### Yandex Cloud
- ❌ No billing API
- ✅ **Organization entity** (legal name!)
- ✅ **Rich managed services** (K8s, PostgreSQL, Kafka)
- ✅ Large-scale infrastructure (49 service accounts, 65 resources)

## Unique Yandex Features

### 1. Organization-Level Identity 🏢

Yandex is the **only provider** that gives us:
- Legal entity name: `ООО "АЙ-ТЕКЛАБС"`
- Organization display name: `I-Techlabs`

This is valuable for:
- Enterprise customers
- Multi-organization scenarios
- Legal/compliance reporting

### 2. Managed Services Visibility 🎯

Shows cluster counts for:
- Kubernetes (managed K8s clusters)
- PostgreSQL (managed databases)
- Kafka (managed message queues)

This helps identify:
- Infrastructure complexity
- Service dependencies
- Cost drivers (managed services are expensive!)

### 3. IAM Complexity Indicator 👥

**49 service accounts** indicates:
- Large-scale infrastructure
- Complex access patterns
- Multiple projects/applications

Useful for:
- Security audits
- Access governance
- Understanding infrastructure maturity

## Limitations

### Service Account Scope

The service account used by InfraZen has **folder-level** access:
- ✅ Can read folder resources
- ✅ Can list service accounts in folder
- ✅ Can access managed services
- ❌ **Cannot** access cloud-level details (403 Permission Denied)
- ❌ **Cannot** access billing accounts

This is **by design** - least privilege principle.

### No Billing API

Like Selectel, Yandex Cloud billing is **web console only**:
- Balance checking requires browser login
- Payment history not via API
- Invoice downloads manual

## Recommended Implementation

### Store in `provider_metadata`

```python
{
  "account_info": {
    "organization": {
      "name": "I-Techlabs",
      "legal_name": "ООО \"АЙ-ТЕКЛАБС\"",
      "id": "bpf24f7co4nlgheig7o0"
    },
    "folder": {
      "name": "itlteam",
      "cloud_id": "b1goskl8180ifslar8gc",
      "status": "ACTIVE"
    },
    "service_account": {
      "name": "infrazen",
      "description": "анализ затрат",
      "last_auth": "2025-10-30T16:40:00Z"
    },
    "managed_services": {
      "kubernetes": 1,
      "postgresql": 2,
      "kafka": 1
    },
    "zones": {
      "total": 4,
      "active": 3
    }
  }
}
```

### Display in UI

**Recommended (Clean & FinOps-focused):**

```
📊 Информация об аккаунте
━━━━━━━━━━━━━━━━━━━━━━
Организация: I-Techlabs
  ООО "АЙ-ТЕКЛАБС"
━━━━━━━━━━━━━━━━━━━━━━
Folder: itlteam (активен)
Сервис-аккаунт: infrazen
━━━━━━━━━━━━━━━━━━━━━━
Управляемые сервисы: 4
  • Kubernetes: 1
  • PostgreSQL: 2
  • Kafka: 1
━━━━━━━━━━━━━━━━━━━━━━
Billing: 115.7 ₽/день
Прогноз месяц: 3,470.1 ₽/месяц
Ресурсов: 65
━━━━━━━━━━━━━━━━━━━━━━
🔗 Баланс и расходы →
```

**Optional additions (if space allows):**
- Zone status (3 of 4 active)
- Total service accounts (49)
- Cloud ID

## Billing Link

Based on Selectel pattern, the link should go to:
```
https://console.cloud.yandex.ru/billing
```

Or more specific:
```
https://console.cloud.yandex.ru/folders/{folder_id}/billing
```

## Implementation Priority

### Must Have ✅
1. Organization name and legal entity
2. Folder name and status
3. Service account name
4. Managed services counts
5. Calculated billing (from resources)
6. Link to Yandex console billing

### Nice to Have 💡
1. Total service accounts count
2. Active zones vs total
3. Cloud ID (for reference)

### Skip ❌
1. Service account list (too detailed)
2. Zone names (not FinOps relevant)
3. Flavor limits (not applicable to Yandex)

## Unique Value Propositions

### Yandex Stands Out With:

1. **Enterprise Context** - Organization legal name helps identify which company's infrastructure
2. **Managed Services** - Shows platform maturity (using managed PostgreSQL/Kafka vs self-hosted)
3. **Scale Indicator** - 49 service accounts + 65 resources = serious infrastructure

### For FinOps Users:

- **Organization name** helps with:
  - Multi-tenant scenarios
  - Legal/compliance reporting
  - Cost center allocation

- **Managed services** helps understand:
  - Why costs are high (managed services cost more)
  - Infrastructure sophistication
  - Operational overhead (managed = less ops work)

## Next Steps

1. ✅ **Document findings** (this file)
2. ⏭️ **Implement in sync** - collect data during sync
3. ⏭️ **Update template** - display in account info dropdown
4. ⏭️ **Test** - verify data populates correctly

## Conclusion

**Yandex Cloud provides:**
- ✅ Best organizational/identity data (legal entity!)
- ✅ Rich infrastructure metrics (managed services, zones)
- ✅ Large-scale infrastructure visibility
- ❌ No billing API (like Selectel)

**This is sufficient for InfraZen** because:
- We calculate spending from actual resources
- Organizational context adds enterprise value
- Managed services help explain costs
- Link to console provides access to billing UI

The lack of billing API is **not a blocker** - we have excellent infrastructure data and can calculate all financial metrics from synced resources.






