# yc-it Connection - Deep Dive Analysis

## 📊 Connection Overview

**Connection Name:** yc-it  
**Provider ID:** 150  
**Provider Type:** Yandex Cloud  
**Account/Folder ID:** ajem3a0uhhooq9u4pvkd → b1gkosunk7kknbq1tubv (itlteam)  
**Last Sync:** 2025-10-27 20:07:42  
**Status:** ✅ Success  

**Cost Summary:**
- **Daily:** 3,787.20 RUB/day (~$42/day)
- **Monthly:** 113,616 RUB/month (~$1,262/month)

**Resources:**
- 17 Servers (VMs)
- 5 Orphan Volumes (standalone disks)

---

## 🔄 How Sync Works for yc-it

### Sync Approach: Resource Discovery (NOT Billing-First)

Unlike Selectel/Beget which use billing API as source of truth, Yandex Cloud uses **direct resource discovery** because:
- Billing API requires special permissions (`billing.accounts.viewer` role)
- Most service accounts only have `viewer` role on their folder
- Resource APIs (Compute, VPC) are more accessible

### Step-by-Step Sync Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: Authentication                                                 │
├─────────────────────────────────────────────────────────────────────────┤
│ 1. Load service account JSON key from database                         │
│ 2. Create JWT token signed with private key                            │
│ 3. Exchange JWT for IAM token (valid 12 hours)                         │
│    API: POST https://iam.api.cloud.yandex.net/iam/v1/tokens            │
│    Result: t1.9euelZqRj8a... (IAM token)                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: Discovery                                                      │
├─────────────────────────────────────────────────────────────────────────┤
│ Try Option A: List Clouds                                              │
│    API: GET https://resource-manager.api.cloud.yandex.net/.../clouds   │
│    Result for yc-it: 0 clouds (no cloud-level access)                  │
│                                                                         │
│ Fallback Option B: Get Service Account's Folder ✅                     │
│    API: GET https://iam.api.cloud.yandex.net/.../serviceAccounts/{id}  │
│    Result: folder_id = b1gkosunk7kknbq1tubv                            │
│                                                                         │
│    API: GET https://resource-manager.api.cloud.yandex.net/.../folders  │
│    Result: Folder "itlteam" in Cloud "b1goskl8180ifslar8gc"            │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: Fetch Resources from APIs                                     │
├─────────────────────────────────────────────────────────────────────────┤
│ 3.1 Get All Instances (VMs)                                            │
│     API: GET https://compute.api.cloud.yandex.net/compute/v1/instances │
│     Params: folderId=b1gkosunk7kknbq1tubv                              │
│     Result: 17 VMs                                                     │
│                                                                         │
│ 3.2 Get All Disks                                                      │
│     API: GET https://compute.api.cloud.yandex.net/compute/v1/disks     │
│     Params: folderId=b1gkosunk7kknbq1tubv                              │
│     Result: 29 disks (includes boot disks + orphans)                   │
│                                                                         │
│ 3.3 Get Networks (optional)                                            │
│     API: GET https://vpc.api.cloud.yandex.net/vpc/v1/networks          │
│                                                                         │
│ 3.4 Get Subnets (optional)                                             │
│     API: GET https://vpc.api.cloud.yandex.net/vpc/v1/subnets           │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: Parse & Transform Each VM                                     │
├─────────────────────────────────────────────────────────────────────────┤
│ For each instance in API response:                                     │
│                                                                         │
│ INPUT (Raw Yandex API JSON):                                           │
│ {                                                                       │
│   "id": "epd0glk7j64adfjh0a1u",                                        │
│   "name": "cl1etc88oikj3sh8mkro-ydas",                                 │
│   "status": "RUNNING",                                                 │
│   "zoneId": "ru-central1-b",                                           │
│   "platformId": "standard-v3",                                         │
│   "resources": {                                                        │
│     "cores": "4",                                                       │
│     "memory": "17179869184",  ← bytes                                  │
│     "coreFraction": "100"                                              │
│   },                                                                    │
│   "bootDisk": {                                                         │
│     "diskId": "epd5ak2nhlkvfq18i179"  ← NO SIZE HERE!                 │
│   },                                                                    │
│   "networkInterfaces": [{                                              │
│     "primaryV4Address": {                                              │
│       "address": "10.1.0.8",                                           │
│       "oneToOneNat": {           ← External IP if exists               │
│         "address": "84.252.138.234"                                    │
│       }                                                                 │
│     }                                                                   │
│   }]                                                                    │
│ }                                                                       │
│                                                                         │
│ TRANSFORMATION:                                                         │
│ 1. Extract resource_id = "epd0glk7j64adfjh0a1u"                        │
│ 2. Extract resource_name = "cl1etc88oikj3sh8mkro-ydas"                 │
│ 3. Parse vcpus = int(cores) = 4                                        │
│ 4. Parse ram_gb = memory / (1024³) = 16.0 GB                           │
│ 5. Status mapping: "RUNNING" → "RUNNING"                               │
│ 6. Region = zoneId = "ru-central1-b"                                   │
│                                                                         │
│ 7. Cross-reference disk size:                                          │
│    - bootDisk.diskId = "epd5ak2nhlkvfq18i179"                          │
│    - Look up in disks list → find disk with matching ID                │
│    - Get disk.size = "137438953472" bytes → 128 GB                     │
│    - total_storage_gb = 128.0                                          │
│                                                                         │
│ 8. Extract IPs:                                                         │
│    - internal: "10.1.0.8"                                              │
│    - external: "84.252.138.234" (if oneToOneNat exists)                │
│                                                                         │
│ 9. Calculate ESTIMATED cost:                                           │
│    Cost Formula:                                                        │
│      CPU:     4 cores × 1.50 ₽/hr × 24h    = 144.00 ₽/day             │
│      RAM:     16 GB × 0.40 ₽/GB/hr × 24h   = 153.60 ₽/day             │
│      Storage: 128 GB × 0.0025 ₽/GB/hr × 24h = 7.68 ₽/day              │
│      ────────────────────────────────────────────────                  │
│      TOTAL:                                  305.28 ₽/day              │
│                                                                         │
│ OUTPUT (InfraZen Resource):                                            │
│ {                                                                       │
│   "resource_type": "server",                                           │
│   "resource_id": "epd0glk7j64adfjh0a1u",                               │
│   "resource_name": "cl1etc88oikj3sh8mkro-ydas",                        │
│   "region": "ru-central1-b",                                           │
│   "status": "RUNNING",                                                 │
│   "service_name": "Compute Cloud",                                     │
│   "daily_cost": 305.28,                                                │
│   "effective_cost": 305.28,                                            │
│   "original_cost": 9158.40,  ← daily × 30                              │
│   "currency": "RUB",                                                   │
│   "external_ip": null,                                                 │
│   "provider_config": {  ← Full metadata stored as JSON                 │
│     "vcpus": 4,                                                         │
│     "ram_gb": 16.0,                                                     │
│     "total_storage_gb": 128.0,                                         │
│     "ip_addresses": ["10.1.0.8"],                                      │
│     "external_ip": null,                                               │
│     "instance": { ... original API response ... }                      │
│   }                                                                     │
│ }                                                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 5: Parse Orphan Disks                                            │
├─────────────────────────────────────────────────────────────────────────┤
│ For each disk where instanceIds = [] (not attached):                   │
│                                                                         │
│ INPUT (Raw Yandex API):                                                │
│ {                                                                       │
│   "id": "epdkg8v4dtq4jjpojvdp",                                        │
│   "name": "newgitdisk",                                                │
│   "typeId": "network-ssd",                                             │
│   "size": "549755813888",  ← 512 GB in bytes                           │
│   "zoneId": "ru-central1-b",                                           │
│   "status": "READY",                                                   │
│   "instanceIds": []  ← Empty = orphan                                  │
│ }                                                                       │
│                                                                         │
│ TRANSFORMATION:                                                         │
│ 1. size_gb = size / (1024³) = 512.0                                    │
│ 2. Determine cost based on disk type:                                  │
│    - network-ssd: 0.0050 ₽/GB/hr                                       │
│    - network-hdd: 0.0015 ₽/GB/hr                                       │
│    - network-nvme: 0.0070 ₽/GB/hr                                      │
│                                                                         │
│    Cost = 512 GB × 0.0050 ₽/GB/hr × 24h = 61.44 ₽/day                 │
│                                                                         │
│ OUTPUT:                                                                 │
│ {                                                                       │
│   "resource_type": "volume",                                           │
│   "resource_id": "epdkg8v4dtq4jjpojvdp",                               │
│   "resource_name": "newgitdisk",                                       │
│   "daily_cost": 61.44,                                                 │
│   "tags": ["is_orphan=true", "disk_type=network-ssd"]                 │
│ }                                                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 6: Collect CPU Statistics (Optional)                             │
├─────────────────────────────────────────────────────────────────────────┤
│ For each VM, query Yandex Monitoring API:                              │
│                                                                         │
│ API: POST https://monitoring.api.cloud.yandex.net/monitoring/v2/...    │
│ Request Body:                                                           │
│ {                                                                       │
│   "query": "cpu_usage{resource_id=\"epd0glk7j64adfjh0a1u\"}",         │
│   "fromTime": "2024-09-27T20:07:00Z",  ← 30 days ago                  │
│   "toTime": "2024-10-27T20:07:00Z",                                    │
│   "downsampling": {                                                     │
│     "gridAggregation": "AVG",                                          │
│     "maxPoints": 720  ← hourly for 30 days                             │
│   }                                                                     │
│ }                                                                       │
│                                                                         │
│ Response: Array of timestamps + CPU values                             │
│                                                                         │
│ Processing:                                                             │
│ 1. Aggregate hourly data into daily averages                           │
│ 2. Calculate: avg, max, min, trend                                     │
│ 3. Determine performance tier:                                         │
│    - < 20% = low                                                        │
│    - 20-60% = medium                                                    │
│    - > 60% = high                                                       │
│                                                                         │
│ Result stored in resource:                                             │
│   resource.add_tag('cpu_avg_usage', '12.78')                           │
│   resource.add_tag('cpu_max_usage', '61.59')                           │
│   resource.add_tag('cpu_performance_tier', 'low')                      │
│   resource.provider_config['usage_statistics'] = { ... }               │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ FINAL: Create Sync Snapshot Record                                     │
├─────────────────────────────────────────────────────────────────────────┤
│ SyncSnapshot {                                                          │
│   id: 8351,                                                             │
│   provider_id: 150,                                                     │
│   sync_type: "resource_discovery",                                     │
│   sync_status: "success",                                              │
│   total_resources_found: 22,                                           │
│   resources_created: 22,                                               │
│   resources_updated: 0,                                                │
│   sync_config: {                                                        │
│     "sync_method": "resource_discovery",                               │
│     "clouds_discovered": 0,                                            │
│     "folders_discovered": 1,                                           │
│     "total_instances": 17,                                             │
│     "total_disks": 5,                                                  │
│     "total_estimated_daily_cost": 3787.20                              │
│   }                                                                     │
│ }                                                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔑 Key Differences from Billing-First Approach

### Yandex (Resource Discovery)
```
1. List resources from API
2. Calculate estimated costs based on specs
3. Optionally enrich with monitoring data
```

### Selectel/Beget (Billing-First)
```
1. Fetch billing data (source of truth)
2. Enrich with resource details from API
3. Billing API shows actual costs + zombie resources
```

---

## 📁 Code Locations

**Main Sync Logic:**  
`app/providers/yandex/service.py` → `sync_resources()` (lines 71-291)

**API Client:**  
`app/providers/yandex/client.py`
- `_get_iam_token()` - Authentication
- `list_clouds()` - Cloud discovery
- `list_folders()` - Folder discovery  
- `list_instances()` - Fetch VMs
- `list_disks()` - Fetch disks
- `get_instance_cpu_statistics()` - CPU metrics

**Resource Transformation:**  
`app/providers/yandex/service.py`
- `_process_instance_resource()` (lines 293-455)
- `_process_disk_resource()` (lines 461-540)
- `_estimate_instance_cost()` (lines 542-568)

---

## 💡 Important Notes

1. **No Billing API Access**  
   The yc-it service account only has `viewer` role on folder, not billing access.  
   All costs shown are **ESTIMATES** based on standard Yandex pricing.

2. **Disk Size Cross-Reference Required**  
   The instances API doesn't include disk sizes - must query disks API separately and match by `diskId`.

3. **CPU Stats Optional**  
   Monitoring API requires additional query per VM. Can be disabled in provider settings.

4. **Folder-Level Access Only**  
   Service account can't see clouds, only its assigned folder (itlteam).

5. **Cost Accuracy**  
   Estimated costs use average pricing:
   - vCPU: 1.50 ₽/hour
   - RAM: 0.40 ₽/GB/hour
   - Storage: 0.0015-0.0070 ₽/GB/hour (depends on type)
   
   Real costs may vary based on:
   - Platform (Intel vs AMD)
   - Preemptible vs regular
   - Reserved capacity discounts
   - Network egress costs
   - Snapshot costs

---

## 🎯 Summary

**yc-it** connection demonstrates Yandex Cloud's **resource-centric** sync approach where:
- Resources are discovered via Compute/VPC APIs
- Costs are estimated algorithmically (not from billing)
- Enrichment happens through separate API calls (monitoring)
- Works with minimal permissions (folder-level `viewer` role)

This differs from Selectel/Beget where billing API is the source of truth and shows actual costs + any orphaned/zombie resources still being charged.



