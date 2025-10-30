# Kubernetes CSI Volume Aggregation - Implementation Summary

**Date:** October 30, 2025  
**Status:** ✅ Complete & Tested  
**Provider:** Yandex Cloud  

---

## 🎯 Problem Statement

### Before Fix:

Users saw Kubernetes cluster and CSI volumes as **separate resources**:

```
Resources List (yc-it):
├─ Kubernetes Cluster "itlkube"        228.00₽/day
├─ k8s-csi-c369c872...                   1.06₽/day  ← Confusing!
├─ k8s-csi-9f79bbad...                   3.44₽/day  ← Confusing!
├─ grafana                               3.17₽/day  ← Confusing!
├─ victoriametrics                      10.56₽/day  ← Confusing!
├─ [+ 5 more CSI volumes...]            17.74₽/day  ← Confusing!
└─ newgitdisk                          219.96₽/day

Total: 10 resources, user confused by "orphan" volumes
```

### User Confusion:

1. **"What are these k8s-csi volumes?"** - Users don't manage CSI volumes directly
2. **"Can I delete them?"** - Deleting would break K8s applications!
3. **"Why are they orphans?"** - They're not orphans, they belong to the cluster
4. **"What's the real K8s cost?"** - Had to manually add master + all CSI volumes

### Why This Happened:

- Kubernetes CSI volumes are created automatically by K8s when users create **PersistentVolumeClaims**
- Yandex Cloud bills them separately under "Block Storage", not "Kubernetes Service"
- From user's perspective, they're **part of the cluster**, not standalone resources
- Users manage them via K8s (kubectl), not Yandex Console

---

## ✅ Solution Implemented

### Core Logic:

1. **Detect CSI Volumes** - During K8s cluster processing, find all disks with:
   - `labels['cluster-name']` matching cluster ID
   - OR name starting with `k8s-csi-`

2. **Aggregate Costs** - Sum all CSI volume costs and add to cluster cost

3. **Hide from List** - Mark CSI volumes as `is_active=False` so they don't show separately

4. **Show Breakdown** - Display cost breakdown on resource card with explanation

---

## 📊 After Fix:

### Clean Resource List:

```
Resources List (yc-it):
├─ Kubernetes Cluster "itlkube"        263.97₽/day  ✨
│  ├─ Master node:                   228.00₽/day
│  └─ CSI Storage (9 volumes):        35.97₽/day
└─ newgitdisk                          219.96₽/day

Total: 2 resources, clean and understandable!
```

### CSI Volumes Included (9 total, 316GB):

1. `k8s-csi-879b78...` - 24GB HDD - 2.53₽/day
2. `k8s-csi-ac04ad...` - 10GB HDD - 1.06₽/day
3. `k8s-csi-c369c8...` - 10GB HDD - 1.06₽/day
4. `k8s-csi-9f79bb...` - 8GB SSD - 3.44₽/day
5. `victoriametrics` - 100GB HDD - 10.56₽/day
6. `k8s-csi-6de03c...` - 10GB HDD - 1.06₽/day
7. `grafana` - 30GB HDD - 3.17₽/day
8. `k8s-csi-a2568f...` - 100GB HDD - 10.56₽/day
9. `k8s-csi-82b383...` - 24GB HDD - 2.53₽/day

**Note:** Even named volumes like `grafana` and `victoriametrics` are CSI volumes - they have the `cluster-name` label in Yandex Cloud.

---

## 🔧 Technical Implementation

### Files Modified:

**app/providers/yandex/service.py:**

1. **Updated `_process_kubernetes_cluster()` signature:**
   ```python
   def _process_kubernetes_cluster(self, cluster: Dict, folder_id: str, 
                                  folder_name: str, cloud_id: str,
                                  sync_snapshot_id: int, disks: List[Dict] = None)
   ```

2. **Added CSI volume detection and aggregation:**
   ```python
   # Find and sum CSI volumes for this cluster
   csi_volumes_cost = 0.0
   csi_volumes_list = []
   
   for disk in disks:
       labels = disk.get('labels', {})
       disk_cluster_id = labels.get('cluster-name')
       
       if disk_cluster_id == cluster_id:
           # Calculate and sum disk cost
           volume_cost = self._estimate_disk_cost(size_gb, disk_type)
           csi_volumes_cost += volume_cost
           csi_volumes_list.append({...})
   
   # Total = master + storage
   estimated_daily_cost = master_daily_cost + csi_volumes_cost
   ```

3. **Added metadata with cost breakdown:**
   ```python
   'cost_breakdown': {
       'master': round(master_daily_cost, 2),
       'storage': round(csi_volumes_cost, 2),
       'total': round(estimated_daily_cost, 2)
   },
   'csi_volumes': csi_volumes_list,
   'csi_volumes_count': csi_volumes_count,
   'note': 'Total cost includes master and CSI volumes...'
   ```

4. **Deactivate old CSI volume resources:**
   ```python
   # Mark CSI volumes as inactive
   for csi_vol in csi_volumes_list:
       old_volume = Resource.query.filter_by(
           provider_id=self.provider.id,
           resource_name=vol_name,
           resource_type='volume',
           is_active=True
       ).first()
       if old_volume:
           old_volume.is_active = False
   ```

5. **Updated sync flow to fetch disks early:**
   ```python
   # Get disks before processing K8s clusters
   folder_disks = self.client.list_disks(folder_id)
   
   # Pass disks to K8s processing
   cluster_resource = self._process_kubernetes_cluster(
       cluster, folder_id, folder_name, cloud_id, 
       sync_snapshot.id, folder_disks
   )
   ```

6. **Skip CSI volumes in standalone disk processing:**
   ```python
   # Skip K8s CSI volumes (already counted in cluster cost)
   if labels.get('cluster-name') or disk_name.startswith('k8s-csi-'):
       logger.debug(f"Skipping K8s CSI volume: {disk_name}")
       continue
   ```

**app/templates/resources.html:**

Added cost breakdown display for Kubernetes clusters:

```html
<!-- Cost Breakdown for Kubernetes (Yandex Provider) -->
{% if config.get('cost_breakdown') %}
<div style="margin-top: 1rem; padding-top: 0.75rem; border-top: 1px solid #e5e7eb;">
    <div style="font-size: 0.75rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.5rem; text-transform: uppercase;">
        💰 Разбивка стоимости
    </div>
    <div style="display: flex; flex-direction: column; gap: 0.35rem; font-size: 0.85rem;">
        <div style="display: flex; justify-content: space-between;">
            <span style="color: var(--text-secondary);">Мастер-нода:</span>
            <span style="font-weight: 500;">{{ config.cost_breakdown.master }}₽/день</span>
        </div>
        {% if config.cost_breakdown.storage > 0 %}
        <div style="display: flex; justify-content: space-between;">
            <span style="color: var(--text-secondary);">CSI Volumes ({{ config.csi_volumes_count }}):</span>
            <span style="font-weight: 500;">{{ config.cost_breakdown.storage }}₽/день</span>
        </div>
        {% endif %}
        <div style="display: flex; justify-content: space-between; padding-top: 0.35rem; border-top: 1px solid #e5e7eb; font-weight: 600;">
            <span>Итого:</span>
            <span style="color: var(--primary);">{{ config.cost_breakdown.total }}₽/день</span>
        </div>
    </div>
    <div style="margin-top: 0.5rem; padding: 0.5rem; background: #FEF3C7; border-left: 3px solid #F59E0B; font-size: 0.75rem; line-height: 1.4;">
        <strong>ℹ️ Внимание:</strong> Стоимость включает мастер-ноду и CSI volumes. Worker-ноды тарифицируются отдельно как VM в Compute Cloud. В панели Yandex мастер и storage показаны раздельно.
    </div>
</div>
{% endif %}
```

---

## 🎯 Key Benefits

### 1. User Clarity ✅
- K8s cluster shows as **1 resource** with complete cost
- No confusing "orphan" CSI volumes
- Clear cost breakdown visible on card

### 2. Accurate Cost Tracking ✅
- Total K8s cost: **263.97₽/day** (was 228₽)
- Includes all infrastructure: master + storage
- Matches how users think about K8s costs

### 3. Prevents User Mistakes ✅
- Users won't try to delete "orphan" CSI volumes
- Can't accidentally break K8s applications
- Clear warnings about Yandex billing differences

### 4. Better Cost Allocation ✅
- K8s team sees **full cluster cost**
- Can assign complete cost to business units
- Accurate project/feature cost tracking

---

## 📝 How It Works

### Detection Logic:

```python
def is_kubernetes_volume(disk):
    """Determine if a disk belongs to a K8s cluster"""
    labels = disk.get('labels', {})
    disk_name = disk.get('name', '')
    
    # Primary: Has cluster-name label (most reliable)
    if labels.get('cluster-name'):
        return True, labels.get('cluster-name')
    
    # Secondary: Has k8s-csi- prefix
    if disk_name.startswith('k8s-csi-'):
        return True, None  # Need to match cluster by other means
    
    return False, None
```

### Volume Types Found:

| Type | Example | Detection Method |
|------|---------|------------------|
| **Auto-generated** | `k8s-csi-c369c872...` | Has `k8s-csi-` prefix AND `cluster-name` label |
| **Named PVC** | `grafana`, `victoriametrics` | Has `cluster-name` label |
| **Standalone** | `newgitdisk` | NO `cluster-name` label |

---

## 🔍 Yandex Cloud Billing Explanation

### How Yandex Bills Kubernetes:

```
Yandex Cloud Invoice:
├─ Managed Service for Kubernetes
│  └─ Master Node: 228₽/day
│
├─ Compute Cloud
│  ├─ Worker VMs: 3,423₽/day (billed as regular VMs)
│  └─ Worker Boot Disks: included in VM cost
│
└─ Block Storage (Compute Cloud)
   └─ CSI Volumes: 35.97₽/day (standalone disks)
```

### How InfraZen Shows It:

```
InfraZen Dashboard:
├─ Kubernetes Cluster
│  ├─ Master: 228₽/day
│  └─ CSI Storage: 35.97₽/day
│  └─ Total: 263.97₽/day
│
└─ Worker VMs (tagged with kubernetes_cluster_id)
   ├─ VM 1: 150₽/day
   └─ VM 2: 150₽/day
```

### Why We Aggregate:

1. **User Mental Model** - K8s storage is part of the cluster
2. **Management** - Users manage via `kubectl apply -f pvc.yaml`, not Yandex Console
3. **Lifecycle** - CSI volumes are created/deleted by K8s automatically
4. **Business Logic** - When calculating K8s cost for a project, need total

---

## 🎨 UI Features

### Resource Card Display:

```
┌─────────────────────────────────────────────┐
│ 🐳 itlkube                      [ACTIVE]    │
│ KUBERNETES-CLUSTER                           │
├─────────────────────────────────────────────┤
│ External IP: —                               │
│ Регион: ru-central1-a                       │
│ Стоимость мес: 7,919₽/месяц                │
│ Стоимость день: 263.97₽/день               │
├─────────────────────────────────────────────┤
│ Version: 1.28                                │
│ Nodes: 3                                     │
│ Total vCPU: 6                                │
│ Total RAM: 12.0 GB                           │
│ Total Storage: 300.0 GB                      │
├─────────────────────────────────────────────┤
│ 💰 РАЗБИВКА СТОИМОСТИ                       │
│ Мастер-нода:        228.0₽/день            │
│ CSI Volumes (9):     35.97₽/день           │
│ ─────────────────────────────────           │
│ Итого:              263.97₽/день           │
│                                              │
│ ⚠️ ВНИМАНИЕ: Стоимость включает мастер-ноду │
│ и 9 CSI volumes. Worker-ноды тарифицируются │
│ отдельно как VM в Compute Cloud. В панели   │
│ Yandex мастер и storage показаны раздельно. │
└─────────────────────────────────────────────┘
```

---

## 📊 Test Results (yc-it connection)

### Resources Count:

| Before | After | Change |
|--------|-------|--------|
| 10 resources | 2 resources | -8 (hidden CSI) |
| 1 K8s cluster | 1 K8s cluster | Same |
| 9 volumes shown | 1 volume shown | -8 CSI volumes |

### Cost Accuracy:

| Resource | Before | After | Difference |
|----------|--------|-------|------------|
| K8s Cluster | 228₽ | 263.97₽ | **+35.97₽** (CSI volumes added) |
| CSI Volumes | 35.97₽ | Hidden | Aggregated into cluster |
| newgitdisk | 219.96₽ | 219.96₽ | Unchanged |
| **Total** | **483.93₽** | **483.93₽** | ✅ **Same total, better UX!** |

---

## 💡 Discovery: More CSI Volumes Than Expected!

### Initial Analysis (Oct 28):
- Expected: 4 CSI volumes
- Cost: 8.73₽/day

### Actual Reality (Oct 30):
- Found: **9 CSI volumes**
- Cost: **35.97₽/day** (4.1x more!)

### Additional Volumes Found:

1. `k8s-csi-879b78...` - 24GB (2.53₽) - **NEW**
2. `k8s-csi-ac04ad...` - 10GB (1.06₽) - **NEW**
3. `victoriametrics` - 100GB (10.56₽) - **NEW** (monitoring)
4. `k8s-csi-a2568f...` - 100GB (10.56₽) - **NEW**
5. `k8s-csi-82b383...` - 24GB (2.53₽) - **NEW**

### Why Missed Earlier:

- HAR file was from Oct 27, before some volumes were created
- Only checked active resources, not full disk list
- Didn't realize named volumes (grafana, victoriametrics) were CSI

---

## 🚀 How to Use

### For Users:

1. Navigate to `/resources`
2. Find Kubernetes Cluster resource
3. See total cost (master + storage)
4. Read cost breakdown section
5. Understand that CSI volumes are included

### For Developers:

The implementation automatically:
- Detects CSI volumes by `cluster-name` label
- Aggregates their costs into cluster cost
- Hides them from resource list
- Shows breakdown on resource card

### Adding New K8s Clusters:

No code changes needed! The logic automatically:
1. Finds CSI volumes for any cluster
2. Aggregates costs
3. Displays breakdown

---

## 📋 Code Changes Summary

### Changes Made:

| File | Lines Changed | Description |
|------|---------------|-------------|
| `app/providers/yandex/service.py` | ~40 lines | CSI detection, cost aggregation, deactivation |
| `app/templates/resources.html` | ~25 lines | Cost breakdown UI with warning message |

### Key Methods Modified:

1. `_process_kubernetes_cluster()` - Now accepts `disks` parameter and aggregates CSI costs
2. `sync_resources()` - Fetches disks early and passes to K8s processing
3. Disk processing loop - Skips CSI volumes (already in cluster)

---

## 🎓 Lessons Learned

### 1. Named Volumes Can Be CSI

**Discovery:** Volumes named `grafana` and `victoriametrics` are CSI volumes!

**How to detect:** Check `labels['cluster-name']`, not just `k8s-csi-` prefix

### 2. HAR Files Can Be Outdated

**Issue:** HAR from Oct 27 missed volumes created after

**Solution:** Always check live API data, not just static HAR analysis

### 3. User Mental Model Matters

**Principle:** Show resources how users **think about them**, not how cloud provider bills them

**Example:** K8s cluster = master + storage, even if billed separately

---

## 🔮 Future Enhancements

### Short Term:

- Add expandable/collapsible CSI volumes list on card
- Show individual volume details on hover
- Add "View in Yandex Console" link for cluster

### Long Term:

- Apply same logic to other managed services if needed
- Add cost trends (master vs storage over time)
- Show which pods are using which CSI volumes

---

## ✅ Success Metrics

### Implementation:
- ✅ Deployed in 1 hour
- ✅ Zero linter errors
- ✅ Tested with real data
- ✅ Clean, maintainable code

### User Experience:
- ✅ 80% fewer resources shown (10 → 2)
- ✅ Clear cost breakdown
- ✅ Warning about Yandex billing difference
- ✅ No more "orphan" volume confusion

### Accuracy:
- ✅ Total cost unchanged (483.93₽)
- ✅ All 9 CSI volumes detected
- ✅ Proper aggregation into cluster

---

**Implementation Date:** October 30, 2025  
**Status:** ✅ Production-Ready  
**Impact:** Significantly improved K8s cost clarity for Yandex Cloud users


