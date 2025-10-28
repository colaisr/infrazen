# Yandex Cloud Complete Cost Tracking - Implementation Plan

## 🎯 Goal: Achieve 95%+ Cost Accuracy

**Current Status:**
- **yc (small):** 99.97% accuracy ✅ (verified)
- **yc-it (large):** 79.68% accuracy ⚠️ (can improve to 95%+)

**Target:** 95%+ accuracy on all Yandex connections

---

## 📊 Current Gap Analysis (Oct 27, yc-it)

| Category | Our Estimate | Real Bill | Gap | Impact |
|----------|--------------|-----------|-----|--------|
| **Compute Cloud** | 3,651.63 ₽ | 4,381.70 ₽ | **-730.07 ₽** | **13.5%** |
| **Kubernetes** | 228.00 ₽ | 228.10 ₽ | -0.10 ₽ | 0.0% ✅ |
| **PostgreSQL** | 424.68 ₽ | 329.36 ₽ | +95.32 ₽ | 1.8% |
| **Missing Services** | 0.00 ₽ | 463.11 ₽ | **-463.11 ₽** | **8.6%** |
| **TOTAL** | 4,304.31 ₽ | 5,402.27 ₽ | -1,097.96 ₽ | 20.3% |

---

## 🔥 Priority 1: Compute Cloud Gap (-730₽)

### 1.1 Snapshots 📸 **+478.98₽** (11% of Compute!)

**Status:** ✅ API endpoints added (`list_snapshots`)  
**Discovery:** Found 10 snapshots, 4,264 GB total  
**Cost:** 478.98₽/day (0.1123₽/GB/day)

**Implementation Steps:**

```python
# 1. Add to client.py - DONE ✅
def list_snapshots(folder_id) -> List[Dict]:
    url = f'{compute_url}/snapshots'
    # Returns: snapshots with id, name, storageSize, status

# 2. Add to service.py - TODO
def _process_snapshot_resource(snapshot, folder_id, ...):
    size_gb = int(snapshot.get('storageSize', 0)) / (1024**3)
    daily_cost = size_gb * 0.1123  # ₽/GB/day
    
    # Create resource with type='snapshot'
    # Tag with source_disk_id if available

# 3. Integrate into sync_resources()
snapshots = client.list_snapshots(folder_id)
for snapshot in snapshots:
    resource = self._process_snapshot_resource(snapshot, ...)
    synced_resources.append(resource)
```

**Testing:**
- Expected: 10 snapshot resources
- Expected cost: ~479₽/day
- Verification: Compare with real bill

**Accuracy Impact:** 79.68% → **88.5%** (+9%)

---

### 1.2 Custom Images 🖼️ **+126.02₽** (3% of Compute)

**Status:** ✅ API endpoints added (`list_images`)  
**Discovery:** Found 4 images, 912 GB total  
**Cost:** 126.02₽/day (0.1382₽/GB/day)

**Implementation Steps:**

```python
# 1. Add to client.py - DONE ✅
def list_images(folder_id) -> List[Dict]:
    url = f'{compute_url}/images'
    # Returns: images with id, name, storageSize, status

# 2. Add to service.py - TODO
def _process_image_resource(image, folder_id, ...):
    size_gb = int(image.get('storageSize', 0)) / (1024**3)
    daily_cost = size_gb * 0.1382  # ₽/GB/day
    
    # Create resource with type='image'

# 3. Integrate into sync_resources()
images = client.list_images(folder_id)
for image in images:
    resource = self._process_image_resource(image, ...)
    synced_resources.append(resource)
```

**Accuracy Impact:** 88.5% → **90.8%** (+2.3%)

---

### 1.3 Reserved IPs (Unused) 🔌 **+40.18₽**

**Status:** ✅ API endpoint exists (`list_addresses`)  
**Discovery:** Need to check for `used: false` addresses  
**Cost:** 40.18₽ for unused reserved IPs

**Implementation Steps:**

```python
# 1. Enhance existing list_addresses() usage
addresses = client.list_addresses(folder_id)

for addr in addresses:
    is_used = addr.get('used', True)
    
    if not is_used:
        # This is a reserved but unused IP - costs money!
        # Create resource with type='reserved_ip'
        # Cost: 0.1920 ₽/hour = 4.61 ₽/day per IP
        
        # From HAR: 40.18₽ suggests ~9 unused IPs
```

**Testing:**
- Check how many reserved addresses have `used: false`
- Multiply by 4.61₽/day
- Should equal ~40₽

**Accuracy Impact:** 90.8% → **91.5%** (+0.7%)

---

### 1.4 Load Balancer IPs 🔌 **+12.44₽**

**Status:** ⚠️ Needs implementation  
**SKU:** `network.public_fips.lb` (different from regular IPs!)  
**Cost:** 12.44₽ (suggests 2 LB IPs)

**Implementation:** Track separately from regular public IPs

**Accuracy Impact:** 91.5% → **91.7%** (+0.2%)

---

### 1.5 NAT Gateway 🌐 **+9.33₽**

**Status:** ✅ API endpoint exists (`list_gateways`)  
**Issue:** Currently returns 0 gateways, but HAR shows 9.33₽  
**SKU:** `vpc.gateway.shared_egress_gateway.v1`

**Investigation Needed:**
- Why does `list_gateways()` return 0?
- Different API endpoint?
- Shared gateway vs dedicated gateway?

**Accuracy Impact:** 91.7% → **91.9%** (+0.2%)

---

### 1.6 Other Compute Items (+63₽)

Minor items that add up. Likely:
- Disk operations/IOPS
- Network transfer within zones
- Reserved resources
- Rounding differences

**Action:** Accept as margin of error (1.4%)

---

## 🟡 Priority 2: PostgreSQL Overestimate (+95₽)

**Issue:** We estimate 424.68₽ but real is 329.36₽ (29% over)

**Real SKU Breakdown (from HAR):**
- CPU (100%): 169.00₽
- RAM: 91.24₽
- Network HDD storage: 69.12₽
- **Total: 329.36₽**

**Our Calculation Analysis Needed:**

```python
# Current estimation in _estimate_database_cluster_cost()
# Need to verify:
# 1. Are we using correct vCPU count?
# 2. Are we using correct RAM amount?
# 3. Are we using correct storage size/type?
# 4. Are we adding unnecessary overhead?

# Action: Print actual vs estimated for PG clusters
pg_clusters = [list PostgreSQL clusters]
for cluster in pg_clusters:
    print(f"vCPUs: {cluster.total_vcpus}")
    print(f"RAM: {cluster.total_ram_gb} GB")
    print(f"Storage: {cluster.total_storage_gb} GB")
    print(f"Estimated: {cluster.daily_cost}")
```

**Testing Steps:**
1. Get actual PG cluster configurations from API
2. Calculate using SKU prices: CPU × 169₽/day per vCPU, RAM × 91.24₽/day per GB
3. Compare with current estimate
4. Adjust calculation method

**Accuracy Impact:** 91.9% → **93.7%** (+1.8%)

---

## 🔥 Priority 3: Missing Services (-463₽)

### 3.1 Kafka Clusters 📨 **+198.14₽** (Biggest missing service!)

**Status:** ❌ Not implemented  
**API:** `https://dataproc.api.cloud.yandex.net/managed-kafka/v1` (similar to PostgreSQL/MySQL)

**Real SKU Breakdown (from HAR):**
- Kafka CPU (100%): 87.09₽
- Kafka RAM: 93.31₽
- Kafka HDD storage: 11.52₽
- Kafka Public IP: 6.22₽
- **Total: 198.14₽**

**Implementation Steps:**

```python
# 1. Add to client.py
def list_kafka_clusters(folder_id) -> List[Dict]:
    url = f'{kafka_url}/clusters'
    params = {'folderId': folder_id}
    response = requests.get(url, headers=headers, params=params)
    return response.json().get('clusters', [])

def get_kafka_cluster_hosts(cluster_id) -> List[Dict]:
    url = f'{kafka_url}/clusters/{cluster_id}/hosts'
    response = requests.get(url, headers=headers)
    return response.json().get('hosts', [])

# 2. Add to service.py
def _process_kafka_cluster(cluster, folder_id, ...):
    # Similar to PostgreSQL/MySQL processing
    # Calculate: vCPUs, RAM, storage
    # Use SKU-based pricing for Kafka
    
# 3. Integrate into sync
kafka_clusters = client.list_kafka_clusters(folder_id)
for cluster in kafka_clusters:
    hosts = client.get_kafka_cluster_hosts(cluster['id'])
    resource = self._process_kafka_cluster(cluster, hosts, ...)
```

**Accuracy Impact:** 93.7% → **97.3%** (+3.6%)

---

### 3.2 Container Registry 📦 **+75.94₽**

**Status:** ❌ Not implemented  
**API:** `https://container-registry.api.cloud.yandex.net/container-registry/v1`  
**SKU:** `cr.bucket.used_space.standard` (storage-based)

**Implementation:**

```python
# 1. Add to client.py
def list_registries(folder_id) -> List[Dict]:
    url = 'https://container-registry.api.cloud.yandex.net/container-registry/v1/registries'
    # Returns: registries with storage usage

# 2. Cost calculation
# 75.94₽/day suggests significant container image storage
# Pricing: ~0.1080₽/GB/day (from SKU data)
```

**Accuracy Impact:** 97.3% → **98.7%** (+1.4%)

---

### 3.3 Load Balancer ⚖️ **+40.44₽**

**Status:** ❌ Not implemented  
**API:** `https://load-balancer.api.cloud.yandex.net/load-balancer/v1`  
**SKU:** `nlb.balancer.active` (hourly charge per balancer)

**Real Breakdown:**
- Balancer active: 40.44₽ (1.685₽/hour × 24 = 40.44₽)
- LB Public IPs: 12.44₽ (already counted in VPC)

**Implementation:**

```python
def list_network_load_balancers(folder_id):
    url = f'{lb_url}/networkLoadBalancers'
    # Returns: load balancers with status, type

# Cost: 1.685₽/hour per active balancer
```

**Accuracy Impact:** 98.7% → **99.5%** (+0.8%)

---

### 3.4 VPC (Networking) 🌐 **+130.38₽**

**Components:**
- Public IPs (active): 68.43₽ - ✅ **Already tracking**
- Reserved IPs (unused): 40.18₽ - ⚠️ Need to implement
- LB Public IPs: 12.44₽ - ⚠️ Part of LB implementation
- NAT Gateway: 9.33₽ - ⚠️ Need to fix discovery

**Current Status:**
- We count active VM IPs ✅
- We need to count unused reserved IPs
- We need to find the NAT gateway

**Remaining VPC gap after fixes:** ~0₽

---

### 3.5 DNS ☁️ **+13.47₽**

**Status:** ❌ Not implemented  
**API:** `https://dns.api.cloud.yandex.net/dns/v1`  
**SKUs:**
- `dns.zones.v1`: 11.66₽ (zone hosting)
- `dns.requests.public.recursive.v1`: 0.61₽ (queries)
- `dns.requests.public.authoritative.v1`: 1.20₽ (queries)

**Implementation:**

```python
def list_dns_zones(folder_id):
    url = f'{dns_url}/zones'
    # Each zone costs ~11.66₽/day
```

**Accuracy Impact:** 99.5% → **99.75%** (+0.25%)

---

### 3.6 Key Management Service (KMS) 🔐 **+2.97₽**

**Status:** ❌ Not implemented  
**API:** `https://kms.api.cloud.yandex.net/kms/v1`  
**SKUs:**
- `kms.api.v1.encryptdecrypt`: 2.87₽ (API operations)
- `kms.storage.v1.software`: 0.10₽ (key storage)

**Low priority:** Only 0.05% of bill

**Accuracy Impact:** 99.75% → **99.80%** (+0.05%)

---

### 3.7 Object Storage (S3) ☁️ **+1.77₽**

**Status:** ❌ Not implemented  
**API:** `https://storage.yandexcloud.net` (S3-compatible)  
**SKU:** `storage.bucket.used_space.standard`

**Very low priority:** Only 0.03% of bill

**Accuracy Impact:** 99.80% → **99.83%** (+0.03%)

---

## 📋 Implementation Roadmap

### Phase 1: Quick Wins (Compute Accuracy) 🔥

**Target:** 79.68% → 91%+ accuracy  
**Time Estimate:** 4-6 hours  
**Impact:** +605₽ captured

#### Task 1.1: Snapshot Discovery ✅ APIs Added
- [x] Add `list_snapshots()` to YandexClient
- [ ] Add `_process_snapshot_resource()` to YandexService
- [ ] Add snapshot SKU pricing (0.1123₽/GB/day)
- [ ] Integrate into `sync_resources()`
- [ ] Test on yc-it (expect 10 snapshots, 479₽)

**Code Changes:**
```python
# app/providers/yandex/service.py

def _process_snapshot_resource(self, snapshot, folder_id, ...):
    snapshot_id = snapshot['id']
    snapshot_name = snapshot.get('name', snapshot_id)
    size_bytes = int(snapshot.get('storageSize', 0))
    size_gb = size_bytes / (1024**3)
    status = snapshot.get('status', 'UNKNOWN')
    source_disk_id = snapshot.get('sourceDiskId')
    
    # Snapshot pricing: 0.1123₽/GB/day (from HAR analysis)
    daily_cost = size_gb * 0.1123
    
    metadata = {
        'snapshot': snapshot,
        'folder_id': folder_id,
        'size_gb': size_gb,
        'source_disk_id': source_disk_id,
        'created_at': snapshot.get('createdAt')
    }
    
    resource = self._create_resource(
        resource_type='snapshot',
        resource_id=snapshot_id,
        name=snapshot_name,
        metadata=metadata,
        sync_snapshot_id=sync_snapshot_id,
        region=folder_id,
        service_name='Compute Cloud'
    )
    
    if resource:
        resource.daily_cost = daily_cost
        resource.effective_cost = daily_cost
        resource.original_cost = daily_cost * 30
        resource.currency = 'RUB'
        resource.add_tag('source_disk_id', source_disk_id)
        resource.add_tag('cost_source', 'sku_based')
    
    return resource
```

#### Task 1.2: Image Discovery ✅ APIs Added
- [x] Add `list_images()` to YandexClient
- [ ] Add `_process_image_resource()` to YandexService
- [ ] Add image SKU pricing (0.1382₽/GB/day)
- [ ] Integrate into `sync_resources()`
- [ ] Test on yc-it (expect 4 images, 126₽)

**Similar implementation to snapshots**

#### Task 1.3: Reserved IPs (Unused)
- [x] `list_addresses()` already exists
- [ ] Modify to create resources for unused IPs
- [ ] Cost: 4.61₽/day per unused IP
- [ ] Test on yc-it (expect ~9 unused IPs, 40₽)

---

### Phase 2: PostgreSQL Fix 🐘

**Target:** Fix 95₽ overestimate  
**Time Estimate:** 1 hour  
**Impact:** Better accuracy on managed DB services

#### Task 2.1: Verify PostgreSQL Host Configurations

```python
# Get actual PG cluster specs
pg_clusters = client.list_postgresql_clusters(folder_id)
for cluster in pg_clusters:
    hosts = client.get_postgresql_cluster_hosts(cluster['id'])
    
    # Print actual specs vs our calculation
    for host in hosts:
        print(f"Host preset: {host.get('resources', {})}")
        print(f"Calculated vCPUs: ...")
        print(f"Calculated RAM: ...")
```

#### Task 2.2: Adjust Calculation
- Use actual resource presets from API
- Verify storage type (network-hdd vs network-ssd)
- Remove any overhead multipliers that don't match reality

---

### Phase 3: Kafka Clusters 📨

**Target:** Add Kafka discovery  
**Time Estimate:** 2-3 hours  
**Impact:** +198₽ captured

#### Task 3.1: Add Kafka API Client Methods

```python
# app/providers/yandex/client.py

def list_kafka_clusters(self, folder_id: str = None):
    """List Kafka clusters in folder"""
    url = 'https://dataproc.api.cloud.yandex.net/managed-kafka/v1/clusters'
    params = {'folderId': folder_id}
    response = requests.get(url, headers=headers, params=params)
    return response.json().get('clusters', [])

def get_kafka_cluster_hosts(self, cluster_id: str):
    """Get hosts for a Kafka cluster"""
    url = f'https://dataproc.api.cloud.yandex.net/managed-kafka/v1/clusters/{cluster_id}/hosts'
    response = requests.get(url, headers=headers)
    return response.json().get('hosts', [])
```

#### Task 3.2: Process Kafka Clusters

```python
# app/providers/yandex/service.py

def _process_kafka_cluster(self, cluster, hosts, ...):
    # Similar to PostgreSQL processing
    # Calculate total vCPUs, RAM, storage from hosts
    # Use Kafka-specific SKU pricing
    
    # From HAR: Kafka uses different presets than PostgreSQL
```

#### Task 3.3: Integrate into Sync
- Add to managed services query phase
- Process alongside PostgreSQL/MySQL
- Tag appropriately

---

### Phase 4: Load Balancers & Container Registry

**Time Estimate:** 3-4 hours  
**Impact:** +116₽

#### Task 4.1: Network Load Balancers

```python
def list_network_load_balancers(folder_id):
    url = 'https://load-balancer.api.cloud.yandex.net/load-balancer/v1/networkLoadBalancers'
    # Returns: balancers with listeners, target groups
    
    # Cost: 1.685₽/hour per active balancer
```

#### Task 4.2: Container Registry

```python
def list_container_registries(folder_id):
    url = 'https://container-registry.api.cloud.yandex.net/container-registry/v1/registries'
    # Returns: registries with storage usage
    
    # Cost: Based on storage used (cr.bucket.used_space.standard)
```

---

### Phase 5: Polish (DNS, KMS, S3)

**Time Estimate:** 2-3 hours  
**Impact:** +18₽ (minor)  
**Priority:** Low - only if aiming for 99.9%+ accuracy

---

## 📈 Expected Accuracy Progression

| Phase | Work | Time | Accuracy | Cumulative Improvement |
|-------|------|------|----------|------------------------|
| **Current** | - | - | 79.68% | - |
| **Phase 1** | Snapshots + Images | 4-6h | **91%+** | +11% ✅ |
| **Phase 2** | PostgreSQL fix | 1h | **94%** | +3% |
| **Phase 3** | Kafka | 2-3h | **97%** | +3% |
| **Phase 4** | LB + Registry | 3-4h | **99%** | +2% |
| **Phase 5** | DNS, KMS, S3 | 2-3h | **99.5%+** | +0.5% |

**Total Implementation Time:** 12-17 hours  
**Final Accuracy Target:** **99%+**

---

## 🛠️ Technical Implementation Notes

### Resource Type Additions

```python
# New resource types to add:
- 'snapshot'          # Disk snapshots
- 'image'             # Custom VM images
- 'reserved_ip'       # Unused public IPs
- 'kafka-cluster'     # Managed Kafka
- 'load_balancer'     # Network Load Balancer
- 'container_registry' # Container Registry
- 'dns_zone'          # DNS zones
- 'nat_gateway'       # NAT gateways
```

### SKU Mapping Additions

```python
# app/providers/yandex/sku_pricing.py

KNOWN_SKUS = {
    # ... existing SKUs ...
    
    # Snapshots & Images
    'compute.snapshot': '<sku_id>',  # 0.1123₽/GB/day
    'compute.image': '<sku_id>',     # 0.1382₽/GB/day
    
    # Kafka
    'mdb.cluster.kafka.v2.cpu.c100': '<sku_id>',
    'mdb.cluster.kafka.v2.ram': '<sku_id>',
    'mdb.cluster.network-hdd.kafka': '<sku_id>',
    
    # Load Balancer
    'nlb.balancer.active': '<sku_id>',  # 1.685₽/hour
    
    # Container Registry
    'cr.bucket.used_space.standard': '<sku_id>',
    
    # DNS
    'dns.zones.v1': '<sku_id>',
}
```

---

## 🧪 Testing Strategy

### Test on yc-it Connection

After each phase, verify:

```python
from app import create_app
from app.core.models.provider import CloudProvider
from app.providers.yandex.service import YandexService

# Sync
service = YandexService(yc_it)
result = service.sync_resources()

# Calculate total
resources = Resource.query.filter_by(provider_id=yc_it.id, is_active=True).all()
total_daily = sum(r.daily_cost or 0 for r in resources)

# Compare
real_bill = 5402.27
accuracy = (1 - abs(total_daily - real_bill) / real_bill) * 100

print(f"Accuracy: {accuracy:.2f}%")
print(f"Gap: {abs(total_daily - real_bill):.2f} ₽")
```

### Verification Checklist

After implementation:
- [ ] yc connection still 99.97% accurate
- [ ] yc-it accuracy improved to 95%+
- [ ] All resource types display correctly in UI
- [ ] Costs match HAR file SKU breakdown
- [ ] No performance degradation (sync time < 60s)

---

## 📁 Files to Modify

1. **app/providers/yandex/client.py**
   - ✅ `list_snapshots()` - Added
   - ✅ `list_images()` - Added
   - ⚠️ `list_addresses()` enhancement
   - ⚠️ `list_gateways()` fix
   - ❌ `list_kafka_clusters()`
   - ❌ `get_kafka_cluster_hosts()`
   - ❌ `list_network_load_balancers()`
   - ❌ `list_container_registries()`
   - ❌ `list_dns_zones()`

2. **app/providers/yandex/service.py**
   - ❌ `_process_snapshot_resource()`
   - ❌ `_process_image_resource()`
   - ❌ `_process_kafka_cluster()`
   - ❌ Update `sync_resources()` to call all new methods

3. **app/providers/yandex/sku_pricing.py**
   - ❌ Add snapshot/image SKU mappings
   - ❌ Add Kafka SKU mappings
   - ❌ Add LB, Registry, DNS SKU mappings

4. **app/providers/yandex/pricing.py**
   - ❌ Add fallback prices for new services

5. **app/templates/resources.html** (optional)
   - ❌ Add display cards for new resource types
   - ❌ Icons for snapshots, images, Kafka, etc.

---

## 🎯 Recommended Next Steps

### Immediate (Next Session):
1. ✅ Implement snapshot resource processing
2. ✅ Implement image resource processing  
3. ✅ Fix reserved IP detection
4. ✅ Test on yc-it → expect 91%+ accuracy

### Short Term (Within Week):
5. ⚠️ Fix PostgreSQL overestimate
6. ⚠️ Add Kafka cluster discovery
7. ⚠️ Test → expect 97% accuracy

### Medium Term (As Needed):
8. 🟢 Add Load Balancer discovery
9. 🟢 Add Container Registry
10. 🟢 Polish (DNS, KMS, S3)

---

## 📊 Success Metrics

**Minimum Viable Product (MVP):**
- ✅ 95% accuracy on yc-it
- ✅ All major services tracked (Compute, K8s, PostgreSQL, Kafka)
- ✅ Snapshots and images included

**Stretch Goal:**
- ✅ 99% accuracy
- ✅ All services tracked
- ✅ Per-resource cost attribution perfect

**Current Progress:**
- ✅ SKU-based pricing implemented
- ✅ 99.97% accuracy on simple environments
- ✅ Snapshots/Images APIs ready
- ⏳ Need to process and integrate

---

## 📚 References

- HAR Files:
  - `haar/center.yandex.cloud.har` - Service-level billing
  - `haar/by_products.har` - **SKU-level usage** (goldmine!)
  
- Yandex APIs:
  - Compute: `compute.api.cloud.yandex.net/compute/v1`
  - Kafka: `dataproc.api.cloud.yandex.net/managed-kafka/v1`
  - Load Balancer: `load-balancer.api.cloud.yandex.net/load-balancer/v1`
  - Container Registry: `container-registry.api.cloud.yandex.net/container-registry/v1`
  - DNS: `dns.api.cloud.yandex.net/dns/v1`
  - KMS: `kms.api.cloud.yandex.net/kms/v1`

---

**Status:** Implementation plan complete ✅  
**Next Action:** Start with Phase 1 (Snapshots + Images)  
**Expected Result:** 91%+ accuracy after 4-6 hours of work

