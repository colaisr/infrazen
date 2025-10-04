# Selectel Integration Findings & Recommendations

## Executive Summary

The current Selectel integration retrieves **basic resource information** but treats **VMs and volumes as separate resources**, which doesn't match the Selectel admin panel view where volumes are shown as part of the VM. This analysis provides a complete flow to retrieve properly combined VM resources.

## Current Issues

1. **Separate Resources**: VMs and their attached volumes are stored as separate resources in the database
2. **Basic Information**: Limited VM details (missing vCPUs, RAM, storage, IPs)
3. **Irrelevant Resources**: Shows volumes separately when they should be part of VM resources

## Expected Behavior (Matching Selectel Admin Panel)

Based on the Selectel admin panel screenshot:
- **2 VMs** (Doreen and Tilly)
- Each VM shows:
  - **Name**: Server name
  - **vCPUs**: 1 vCPU each
  - **RAM**: 1 GB (1024 MB) each
  - **Storage**: 5 GB each (from attached volumes)
  - **IP Address**: Private IP (192.168.0.2 and 192.168.0.188)
  - **Status**: ACTIVE
  - **Region**: ru-3b (Saint Petersburg)
  - **Flavor**: SL1.1-1024 (Standard Line)

## Complete API Flow Analysis

### Step-by-Step Process

#### 1. Get Account Information
```
URL: https://api.selectel.ru/vpc/resell/v2/accounts
Headers: X-Token: {api_key}
Response: {"account": {"name": "478587", "enabled": true, ...}}
```

#### 2. Get Projects List
```
URL: https://api.selectel.ru/vpc/resell/v2/projects
Headers: X-Token: {api_key}
Response: {"projects": [{"id": "48643015...", "name": "My First Project", ...}]}
```

#### 3. Generate IAM Token (Project-Scoped)
```
URL: https://cloud.api.selcloud.ru/identity/v3/auth/tokens
Method: POST
Body: {
  "auth": {
    "identity": {
      "methods": ["password"],
      "password": {
        "user": {
          "name": "InfraZen",  // service_username
          "domain": {"name": "478587"},  // account_id
          "password": "***"  // service_password
        }
      }
    },
    "scope": {
      "project": {
        "id": "48643015...",  // project_id from step 2
        "domain": {"name": "478587"}
      }
    }
  }
}
Response Headers: X-Subject-Token: {iam_token}
```

#### 4. Get Servers (VMs) with Full Details
```
URL: https://ru-3.cloud.api.selcloud.ru/compute/v2.1/servers/detail
Headers: 
  X-Auth-Token: {iam_token}
  Openstack-Api-Version: compute latest
Response: {
  "servers": [
    {
      "id": "801095a0-...",
      "name": "Doreen",
      "status": "ACTIVE",
      "flavor": {"vcpus": 1, "ram": 1024, ...},
      "addresses": {"net": [{"addr": "192.168.0.2"}]},
      "os-extended-volumes:volumes_attached": [{
        "id": "814bb06f-...",
        "delete_on_termination": false
      }],
      ...
    },
    ...
  ]
}
```

#### 5. Get Volumes (Block Storage)
```
URL: https://ru-3.cloud.api.selcloud.ru/volume/v3/{project_id}/volumes/detail
Headers: 
  X-Auth-Token: {iam_token}
  Openstack-Api-Version: volume latest
Response: {
  "volumes": [
    {
      "id": "814bb06f-...",
      "name": "disk-for-Doreen-#1",
      "size": 5,
      "status": "in-use",
      "attachments": [{
        "server_id": "801095a0-...",
        "device": "/dev/sda"
      }],
      ...
    },
    ...
  ]
}
```

#### 6. Get Network Ports (Network Interfaces)
```
URL: https://ru-3.cloud.api.selcloud.ru/network/v2.0/ports
Headers:
  X-Auth-Token: {iam_token}
  Openstack-Api-Version: network latest
Response: {
  "ports": [
    {
      "id": "fd32f666-...",
      "device_id": "801095a0-...",  // Links to server
      "device_owner": "compute:ru-3b",
      "fixed_ips": [{"ip_address": "192.168.0.2"}],
      "mac_address": "fa:16:3e:96:89:fc",
      ...
    },
    ...
  ]
}
```

#### 7. Combine Data
```python
# Map volumes to servers by attachment
volume_by_server = {
    "801095a0-...": [
        {
            "id": "814bb06f-...",
            "name": "disk-for-Doreen-#1",
            "size_gb": 5,
            "device": "/dev/sda",
            "bootable": true
        }
    ]
}

# Map ports to servers by device_id
port_by_server = {
    "801095a0-...": [
        {
            "id": "fd32f666-...",
            "ip_addresses": ["192.168.0.2"],
            "mac_address": "fa:16:3e:96:89:fc"
        }
    ]
}

# Create complete VM resource
complete_vm = {
    "id": "801095a0-...",
    "name": "Doreen",
    "type": "server",
    "status": "ACTIVE",
    "region": "ru-3b",
    "vcpus": 1,
    "ram_mb": 1024,
    "flavor_name": "SL1.1-1024",
    "ip_addresses": ["192.168.0.2"],
    "total_storage_gb": 5,
    "attached_volumes": [...],
    "network_interfaces": [...]
}
```

## Comparison: Current vs Improved Implementation

### Current Implementation
```
Resources Retrieved:
- Account (1)
- Project (1)
- Server (2) - Basic info only
- Volume (2) - Separate resources
Total: 6 resources

Issues:
❌ Volumes shown as separate resources
❌ Missing VM details (vCPUs, RAM, IPs)
❌ No volume-to-VM relationship
❌ Doesn't match admin panel view
```

### Improved Implementation (Based on Beget)
```
Resources Retrieved:
- Account (1)
- Project (1)
- Server (2) - Complete info with attached volumes
Total: 4 resources

Benefits:
✅ Volumes integrated into VM resources
✅ Complete VM details (vCPUs, RAM, storage, IPs)
✅ Clear VM-to-volume relationships
✅ Matches admin panel view
✅ Similar to Beget implementation pattern
```

## Recommended Changes

### 1. Update SelectelClient (`app/providers/selectel/client.py`)

**Add new methods:**
```python
def get_combined_vm_resources(self) -> List[Dict[str, Any]]:
    """Get VM resources with attached volumes combined"""
    servers = self.get_openstack_servers()
    volumes = self.get_openstack_volumes()
    ports = self.get_openstack_ports()
    
    # Combine data (see implementation in test script)
    return complete_vms

def get_all_resources(self) -> Dict[str, Any]:
    """Get all resources including combined VMs"""
    return {
        'account': self.get_account_info(),
        'projects': self.get_projects(),
        'servers': self.get_combined_vm_resources(),  # Combined VMs
        'volumes': [],  # Empty - now part of servers
        'networks': []
    }
```

### 2. Update SelectelService (`app/providers/selectel/service.py`)

**Modify sync_resources method:**
```python
def sync_resources(self) -> Dict[str, Any]:
    # ... existing code ...
    
    # Process servers (VMs with attached volumes)
    if 'servers' in api_resources:
        for server_data in api_resources['servers']:
            server_resource = self._create_resource(
                resource_type='server',
                resource_id=server_data.get('id'),
                name=server_data.get('name'),
                metadata={
                    **server_data,
                    'vcpus': server_data.get('vcpus'),
                    'ram_mb': server_data.get('ram_mb'),
                    'total_storage_gb': server_data.get('total_storage_gb'),
                    'ip_addresses': server_data.get('ip_addresses'),
                    'attached_volumes': server_data.get('attached_volumes')
                },
                sync_snapshot_id=sync_snapshot.id,
                region=server_data.get('region', 'ru-3'),
                service_name='Compute'
            )
            synced_resources.append(server_resource)
    
    # Don't process volumes separately anymore
```

### 3. Expected Results After Changes

**Before:**
```
Resources in Database:
- 1 Account resource
- 1 Project resource
- 2 Server resources (basic)
- 2 Volume resources (separate)
Total: 6 resources
```

**After:**
```
Resources in Database:
- 1 Account resource
- 1 Project resource
- 2 Server resources (complete with volumes)
Total: 4 resources

Each Server Resource Contains:
- VM Details: name, status, vCPUs, RAM, flavor
- IP Addresses: all assigned IPs
- Attached Volumes: list of volumes with sizes, devices
- Network Interfaces: MAC addresses, IPs
- Total Storage: calculated from all attached volumes
```

## Test Scripts Created

1. **`explore_selectel_har.py`** - Analyzes HAR file to extract API calls
2. **`test_selectel_complete_flow.py`** - Tests complete 8-step flow
3. **`test_updated_selectel_client.py`** - Tests improved client implementation

## Files with Full Implementation

- **`test_updated_selectel_client.py`** contains the complete `UpdatedSelectelClient` class
- This class can be used as a reference to update the production code
- All methods are tested and working with real credentials

## Next Steps

1. Review the test scripts and verify the combined resource structure
2. Update `app/providers/selectel/client.py` with the new methods
3. Update `app/providers/selectel/service.py` to use combined resources
4. Test the sync operation with the updated code
5. Verify resources are displayed correctly in the UI

## Key Endpoints Reference

### Account Management
- **Base URL**: `https://api.selectel.ru/vpc/resell/v2`
- **Auth**: `X-Token: {api_key}`

### OpenStack Cloud Resources
- **Base URL**: `https://ru-3.cloud.api.selcloud.ru`
- **Auth**: `X-Auth-Token: {iam_token}`
- **Requires**: IAM token from service user credentials

### IAM Token Generation
- **URL**: `https://cloud.api.selcloud.ru/identity/v3/auth/tokens`
- **Method**: POST
- **Scope**: Must be project-scoped for resource access
- **Token Location**: Response header `X-Subject-Token`

## Comparison with Beget Implementation

The Beget provider has a similar pattern:
- Retrieves VPS servers with complete information
- Includes disk usage, IP addresses, software details
- Shows VPS as single resource (not VPS + separate disk)

The improved Selectel implementation follows the same pattern:
- Retrieves VM servers with complete information
- Includes storage, IP addresses, network interfaces
- Shows VM as single resource (not VM + separate volumes)

This consistency makes the user experience better across different providers.

