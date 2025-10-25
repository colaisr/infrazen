# Yandex Cloud Monitoring API - Research Results

## 🔍 **Research Summary** (October 2025)

Tested Yandex Cloud Monitoring API with your production account (`fv4q6scfocfakj434b3t`).

## ✅ **What's Available**

### CPU Metrics ✅ WORKING
- **`cpu_usage`**: CPU usage percentage
- **`cpu_utilization`**: CPU utilization percentage (per CPU core)
- **Data**: ✅ 4 data points (7-day history), Avg: 0.11%, Max: 0.15%
- **Status**: ✅ Ready to implement

### Network Metrics ✅ WORKING
- **`network_received_bytes`**: Incoming network traffic
- **`network_sent_bytes`**: Outgoing network traffic
- **`network_received_packets`**: Incoming packets
- **`network_sent_packets`**: Outgoing packets
- **Status**: ✅ Available but not critical for FinOps

### Disk I/O Metrics ⚠️ PARTIAL
- **`disk.read_bytes`**: Disk read throughput
- **`disk.write_bytes`**: Disk write throughput
- **`disk.read_ops`**: Disk read operations
- **`disk.write_ops`**: Disk write operations
- **Status**: ⚠️ Metrics exist but no data returned (VM might be too new or not generating I/O)

### Memory Metrics ❌ NOT AVAILABLE
- **`memory_utilization`**: NOT FOUND
- **`memory_usage`**: NOT FOUND
- **`ram_usage`**: NOT FOUND
- **Status**: ❌ Yandex Cloud doesn't expose memory metrics by default

### Disk Usage (Capacity) ❌ NOT AVAILABLE
- **`disk_used_bytes`**: NOT FOUND
- **`disk_usage_percent`**: NOT FOUND
- **Status**: ❌ Not available via Monitoring API

## 📊 **Comparison with Selectel**

| Metric | Selectel (OpenStack) | Yandex Cloud |
|--------|----------------------|--------------|
| **CPU Usage** | ✅ cpu_util (avgerage) | ✅ cpu_usage, cpu_utilization |
| **Memory Usage** | ✅ Available via OpenStack | ❌ NOT available |
| **Disk Used** | ✅ Available via OpenStack | ❌ NOT available |
| **Disk I/O** | ✅ disk_read/write_bytes | ⚠️ Exists but no data |
| **Network** | ✅ Available | ✅ Available |

## 🎯 **What You Can Get from Yandex**

### ✅ **Available for Implementation**

**CPU Usage** (Like Selectel):
- Metric: `cpu_usage`
- Values: Percentage (0-100%)
- History: 7+ days available
- Granularity: Configurable via `downsampling.maxPoints`
- Display: Line graph showing CPU % over time

**Example Data**:
```
Time Range: 7 days
Points: 4
Average CPU: 0.11%
Max CPU: 0.15%
Min CPU: 0.06%
```

### ❌ **NOT Available from Yandex**

**Memory (RAM) Usage**:
- Yandex Cloud **does not expose** memory usage metrics by default
- Unlike OpenStack/Selectel which has this built-in
- Would require:
  - Custom monitoring agent inside VM
  - Unified Agent (Yandex's monitoring agent)
  - Or manual instrumentation

**Disk Usage (Used Space)**:
- Yandex Cloud **does not expose** disk capacity metrics
- Cannot get "15 GB used / 20 GB total" like Selectel
- Would require:
  - Unified Agent inside VM
  - Custom monitoring
  - Or SSH access to check `df -h`

## 🔧 **Implementation Options**

### Option 1: CPU Only (Quick Win) ⭐ RECOMMENDED

**What to implement**:
- ✅ CPU usage graphs (7-30 day history)
- ✅ Average/Max/Min CPU percentage
- ✅ Similar to Selectel's CPU display

**What users won't have**:
- ❌ Memory usage graphs
- ❌ Disk used/free metrics

**Effort**: Low (1-2 hours)
**Value**: Medium (shows VM activity, identifies idle VMs)

**Implementation**:
```python
# In YandexClient
def get_instance_cpu_statistics(self, instance_id: str, days: int = 30):
    """Get CPU usage for last N days"""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    url = f'{self.monitoring_url}/data/read'
    params = {'folderId': self.folder_id}
    
    body = {
        'query': f'cpu_usage{{resource_id=\"{instance_id}\"}}',
        'fromTime': start_time.isoformat() + 'Z',
        'toTime': end_time.isoformat() + 'Z',
        'downsampling': {
            'gridAggregation': 'AVG',
            'maxPoints': days * 24  # Hourly points
        }
    }
    
    headers = self._get_headers()
    response = requests.post(url, json=body, params=params, headers=headers)
    
    data = response.json()
    values = data['metrics'][0]['timeseries']['doubleValues']
    
    return {
        'avg_cpu_usage': sum(values) / len(values),
        'max_cpu_usage': max(values),
        'min_cpu_usage': min(values),
        'data_points': values  # For graphing
    }
```

### Option 2: CPU + Unified Agent (Complete Solution)

**What to implement**:
- ✅ CPU usage (from Monitoring API)
- ✅ Memory usage (from Unified Agent)
- ✅ Disk usage (from Unified Agent)

**Requirements**:
- User must install Yandex Unified Agent in VMs
- Agent sends custom metrics to Monitoring API
- InfraZen reads both default + custom metrics

**Effort**: High (requires user setup + documentation)
**Value**: High (full parity with Selectel)

**Not recommended** because it requires user action on every VM.

### Option 3: Hybrid Approach (Practical)

**What to implement**:
- ✅ CPU usage from Monitoring API
- ℹ️ Show "Memory/Disk usage unavailable" message
- ℹ️ Add "Install Unified Agent for full metrics" link

**Effort**: Low
**Value**: Medium (transparent about limitations)

## 💡 **My Recommendation**

### Implement **CPU Usage Only** (Option 1)

**Why**:
1. ✅ Works out-of-the-box (no user setup needed)
2. ✅ Identifies idle VMs for cost optimization
3. ✅ Shows VM activity patterns
4. ✅ Better than nothing (currently no metrics at all)
5. ❌ Memory/disk not available without agent (Yandex limitation)

**What it enables**:
- CPU-based rightsizing recommendations ("VM using <5% CPU → downsize")
- Idle VM detection
- Activity pattern visualization
- Cost optimization based on CPU usage

**What it won't do**:
- Memory-based recommendations (need agent)
- Disk cleanup suggestions (need agent)
- Full system health monitoring (need agent)

## 📋 **Implementation Plan for CPU Metrics**

### Step 1: Add Methods to YandexClient (30 min)

```python
def get_instance_cpu_statistics(self, instance_id: str, days: int = 30):
    """Get CPU usage statistics for an instance"""
    # Query cpu_usage metric
    # Return avg/max/min + data_points array
    
def get_all_instance_statistics(self, folder_id: str, days: int = 30):
    """Get CPU stats for all instances in folder"""
    instances = self.list_instances(folder_id)
    stats = {}
    for instance in instances:
        stats[instance['id']] = self.get_instance_cpu_statistics(instance['id'], days)
    return stats
```

### Step 2: Store in Database (15 min)

Use existing models:
- `ResourceMetric` - Individual metric points
- `ResourceUsageSummary` - Aggregated stats (avg/max/min)

Or add to resource tags:
- `cpu_avg_usage`: Average CPU %
- `cpu_max_usage`: Max CPU %
- `cpu_usage_30d`: JSON array of daily values

### Step 3: Display in UI (30 min)

Update `resources.html` to show CPU graph:
- Similar to Selectel's implementation
- Canvas.js or Chart.js for line graph
- Show for Yandex VMs (check provider_type)
- Add note: "Memory/Disk metrics require Unified Agent"

### Step 4: Sync Integration (15 min)

Add to `YandexService.sync_resources()`:
```python
# After syncing resources, fetch CPU stats
if collect_performance_stats:
    for vm in synced_vms:
        cpu_stats = client.get_instance_cpu_statistics(vm.resource_id, days=30)
        # Store in ResourceUsageSummary or tags
```

**Total Effort**: ~2 hours

## 📝 **Next Steps**

### Immediate (CPU Only):
1. Implement `get_instance_cpu_statistics()` in `YandexClient`
2. Add CPU stat fetching to `YandexService.sync_resources()`
3. Store CPU data in `ResourceUsageSummary` or tags
4. Update UI template to display CPU graph for Yandex VMs
5. Add note about memory/disk limitations

### Future (Full Metrics):
1. Document Unified Agent installation for users
2. Add custom metric queries for memory/disk
3. Detect if agent is installed (check for custom metrics)
4. Show full metrics if available, CPU-only if not

## 🎯 **Summary**

**What works now**: ✅ **CPU usage metrics**
- Available via Monitoring API
- No agent needed
- 7-30 day history
- Production-tested: 0.11% avg CPU (your VM is idle!)

**What doesn't work**: ❌ **Memory and Disk usage**
- Not exposed by Yandex Cloud by default
- Requires Unified Agent installation in VMs
- Not practical for out-of-the-box InfraZen experience

**Recommendation**: 
- ✅ Implement CPU metrics (like Selectel does)
- ℹ️ Show message: "Memory/Disk metrics require Yandex Unified Agent"
- 🔄 Future: Add agent detection + custom metric support

**This gives you 80% of Selectel's metrics functionality with 20% effort!** 🎯

