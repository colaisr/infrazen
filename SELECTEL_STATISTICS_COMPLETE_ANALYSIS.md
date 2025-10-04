# Selectel Statistics Analysis - Complete Report

**Date**: October 4, 2025  
**Analysis**: HAR file network trace from Selectel admin panel  
**Status**: ✅ STATISTICS API DISCOVERED AND TESTED

---

## Executive Summary

✅ **YES! Selectel provides CPU and memory usage statistics similar to Beget!**

The statistics are available through OpenStack's **Gnocchi metrics API** at:
```
https://ru-3.cloud.api.selcloud.ru/metric/v1/aggregates
```

The data format is **100% compatible** with Beget's format, so we can:
- ✅ Use the same storage structure (resource tags)
- ✅ Use the same Chart.js display code
- ✅ Show CPU and memory graphs for Selectel VMs

## API Endpoint Details

### Base Endpoint
```
URL: https://ru-3.cloud.api.selcloud.ru/metric/v1/aggregates
Method: POST
Auth: X-Auth-Token (IAM token from service user credentials)
Content-Type: application/json
```

### Query Parameters
```
details=false                          # Don't return detailed breakdown
granularity=300                        # 300 seconds (5 minutes) per point
start=2025-10-04T17:00:00.000Z        # Start time (ISO 8601 UTC)
stop=2025-10-04T18:00:00.000Z         # Stop time (ISO 8601 UTC)
```

### Request Bodies

#### CPU Statistics
```json
{
  "operations": "(max (metric cpu_util mean) (/ (clip_min (rateofchangesec (metric cpu_average mean)) 0) 10000000)))",
  "search": "id=801095a0-0d17-4e8a-a91a-0737f65dbddd",
  "resource_type": "generic"
}
```

**Explanation:**
- `operations`: Gnocchi DSL for metric aggregation
- `metric cpu_util mean`: CPU utilization percentage
- `search`: Filter by server ID
- `resource_type`: Generic OpenStack resource

#### Memory Statistics
```json
{
  "operations": "(metric memory.usage mean)",
  "search": "id=801095a0-0d17-4e8a-a91a-0737f65dbddd",
  "resource_type": "generic"
}
```

**Explanation:**
- `operations`: Simple mean aggregation
- `metric memory.usage mean`: Memory usage in MB
- Simpler than CPU (no complex calculations)

### Response Format

#### CPU Response Structure
```json
{
  "measures": {
    "aggregated": [
      ["2025-10-04T17:50:00+00:00", 300.0, 0.12],
      ["2025-10-04T17:55:00+00:00", 300.0, 0.11],
      ["2025-10-04T18:00:00+00:00", 300.0, 0.12],
      ...
    ]
  }
}
```

**Array Format**: `[timestamp, granularity_in_seconds, cpu_percentage]`

#### Memory Response Structure
```json
{
  "measures": {
    "801095a0-0d17-4e8a-a91a-0737f65dbddd": {
      "memory.usage": {
        "mean": [
          ["2025-10-04T17:50:00+00:00", 300.0, 236.91],
          ["2025-10-04T17:55:00+00:00", 300.0, 236.90],
          ["2025-10-04T18:00:00+00:00", 300.0, 236.91],
          ...
        ]
      }
    }
  }
}
```

**Array Format**: `[timestamp, granularity_in_seconds, memory_in_mb]`

## Data Processing Logic

### Step 1: Fetch Raw Data
```python
# Last 1 hour with 5-minute granularity
response = requests.post(
    "https://ru-3.cloud.api.selcloud.ru/metric/v1/aggregates"
    "?granularity=300&start={start}&stop={stop}",
    json={
        "operations": "(max (metric cpu_util mean) ...)",
        "search": f"id={server_id}",
        "resource_type": "generic"
    },
    headers={'X-Auth-Token': iam_token}
)
```

### Step 2: Extract Values
```python
data_points = response.json()['measures']['aggregated']
# data_points = [["2025-10-04T17:50:00+00:00", 300.0, 0.12], ...]

cpu_values = [point[2] for point in data_points if point[2] is not None]
# cpu_values = [0.12, 0.11, 0.12, ...]
```

### Step 3: Calculate Statistics (Beget Format)
```python
avg_cpu = sum(cpu_values) / len(cpu_values)
max_cpu = max(cpu_values)
min_cpu = min(cpu_values)
trend = max_cpu - min_cpu

# Determine performance tier
if avg_cpu < 20:
    performance_tier = 'low'
elif avg_cpu < 60:
    performance_tier = 'medium'
else:
    performance_tier = 'high'

statistics = {
    'avg_cpu_usage': avg_cpu,
    'max_cpu_usage': max_cpu,
    'min_cpu_usage': min_cpu,
    'trend': trend,
    'performance_tier': performance_tier,
    'data_points': len(cpu_values),
    'period': 'HOUR',
    'collection_timestamp': datetime.now().isoformat()
}
```

### Step 4: Store in Resource Tags (Same as Beget)
```python
resource.add_tag('cpu_avg_usage', str(statistics['avg_cpu_usage']))
resource.add_tag('cpu_max_usage', str(statistics['max_cpu_usage']))
resource.add_tag('cpu_min_usage', str(statistics['min_cpu_usage']))
resource.add_tag('cpu_performance_tier', statistics['performance_tier'])
resource.add_tag('cpu_data_points', str(statistics['data_points']))
```

## Test Results

### Doreen (Selectel Server)
```
Specifications:
  - vCPUs: 1
  - RAM: 1024 MB
  - Flavor: SL1.1-1024

CPU Statistics (Last Hour):
  - Average: 0.12%
  - Maximum: 0.12%
  - Minimum: 0.11%
  - Performance Tier: LOW
  - Data Points: 11

Memory Statistics (Last Hour):
  - Average: 236.91 MB (23.14%)
  - Maximum: 236.91 MB
  - Minimum: 236.90 MB
  - Memory Tier: LOW
  - Data Points: 11
```

### Tilly (Selectel Server)
```
Specifications:
  - vCPUs: 1
  - RAM: 1024 MB
  - Flavor: SL1.1-1024

CPU Statistics (Last Hour):
  - Average: 0.15%
  - Maximum: 0.18%
  - Minimum: 0.13%
  - Performance Tier: LOW
  - Data Points: 12

Memory Statistics (Last Hour):
  - Average: 249.02 MB (24.32%)
  - Maximum: 249.03 MB
  - Minimum: 249.00 MB
  - Memory Tier: LOW
  - Data Points: 13
```

## Comparison: Beget vs Selectel

### Beget Implementation
```python
# Endpoint: /v1/vps/statistic/cpu/{vps_id}
beget_stats = {
    "avg_cpu_usage": 7.66,
    "max_cpu_usage": 14.86,
    "min_cpu_usage": 3.21,
    "trend": 11.65,
    "performance_tier": "low",
    "data_points": 108,
    "period": "HOUR"
}
```

### Selectel Implementation (After Processing)
```python
# Endpoint: /metric/v1/aggregates (POST)
selectel_stats = {
    "avg_cpu_usage": 0.12,
    "max_cpu_usage": 0.12,
    "min_cpu_usage": 0.11,
    "trend": 0.02,
    "performance_tier": "low",
    "data_points": 11,
    "period": "HOUR"
}
```

### Compatibility: ✅ 100%

**Same Fields**, **Same Units**, **Same Storage**, **Same Display**!

## Granularity Options

### Option 1: 5-Minute Granularity (Recommended)
```
granularity=300
Data points per hour: 12
API response time: Fast
Sufficient for FinOps monitoring
```

### Option 2: 1-Minute Granularity (Like Beget)
```
granularity=60
Data points per hour: 60
API response time: Slower
More detailed, matches Beget exactly
```

**Recommendation**: Start with 300-second (5-minute) granularity for efficiency.

## Implementation Checklist

- [ ] Add `get_server_cpu_statistics()` to `SelectelClient`
- [ ] Add `get_server_memory_statistics()` to `SelectelClient`
- [ ] Add `get_all_server_statistics()` to `SelectelClient`
- [ ] Integrate statistics fetching into `SelectelService.sync_resources()`
- [ ] Process and store statistics in resource tags
- [ ] Store raw data in snapshot metadata
- [ ] Test sync operation
- [ ] Verify Chart.js graphs display correctly

## Code Files Created for Testing

1. ✅ `analyze_selectel_statistics.py` - HAR file analysis
2. ✅ `test_selectel_statistics_api.py` - API testing
3. ✅ `implement_selectel_statistics.py` - Beget-format conversion
4. ✅ `SELECTEL_STATISTICS_FINDINGS.md` - Detailed documentation

## Summary

🎯 **DISCOVERY COMPLETE!**

Selectel provides CPU and memory statistics through the Gnocchi metrics API. The data can be:
- Retrieved during sync (like Beget)
- Converted to Beget-compatible format
- Stored in the same resource tags
- Displayed using the same Chart.js code

**The infrastructure is ready - just needs to be integrated into the sync process!** 🚀

---

**Next**: Implement statistics methods in SelectelClient and integrate into sync process.

