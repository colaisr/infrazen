# Yandex Cloud Integration for InfraZen

## Overview

The Yandex Cloud integration provides comprehensive resource discovery and cost management for Yandex Cloud infrastructure, following the same architectural patterns as the Selectel and Beget integrations.

## Authentication Methods

Yandex Cloud requires IAM tokens for API access. You can obtain IAM tokens using one of two methods:

### Method 1: Service Account Key (RECOMMENDED)

This is the recommended method for automation and production use.

#### Step 1: Create a Service Account

1. Go to [Yandex Cloud Console](https://console.cloud.yandex.com/)
2. Navigate to your folder
3. Go to "Service accounts" in the left sidebar
4. Click "Create service account"
5. Give it a name (e.g., "infrazen-integration")
6. Assign roles:
   - `viewer` - for read access to resources
   - `billing.accounts.viewer` - for billing data access (if available)

#### Step 2: Create an Authorized Key

1. Open the service account
2. Go to the "Authorized keys" tab
3. Click "Create new key"
4. Select "Create authorized key for service account"
5. Download the JSON file - this is your `service_account_key`

#### Step 3: Configure in InfraZen

When adding Yandex Cloud as a provider in InfraZen, use the following credentials format:

```json
{
  "service_account_key": {
    "id": "your-key-id",
    "service_account_id": "your-service-account-id",
    "created_at": "2024-01-01T00:00:00Z",
    "key_algorithm": "RSA_2048",
    "public_key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----",
    "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
  },
  "cloud_id": "your-cloud-id",
  "folder_id": "your-default-folder-id"
}
```

Or paste the entire service account key JSON content directly in the credentials field.

### Method 2: OAuth Token (For User Accounts)

This method is suitable for development and testing.

#### Step 1: Get OAuth Token

1. Go to [OAuth Token Page](https://oauth.yandex.com/authorize?response_type=token&client_id=1a6990aa636648e9b2ef855fa7bec2fb)
2. Grant permissions
3. Copy the OAuth token from the URL

#### Step 2: Configure in InfraZen

```json
{
  "oauth_token": "your-oauth-token",
  "cloud_id": "your-cloud-id",
  "folder_id": "your-default-folder-id"
}
```

## Required Permissions

The service account or user account needs the following permissions:

- **Resource Discovery**:
  - `compute.viewer` - View VMs and disks
  - `vpc.viewer` - View networks and subnets
  - `resource-manager.viewer` - View folders and clouds

- **Billing** (optional, for cost data):
  - `billing.accounts.viewer` - View billing information

## Features

### ✅ Implemented

1. **IAM Token Authentication**
   - Service account key (JWT-based)
   - OAuth token support
   - Automatic token refresh

2. **Resource Discovery**
   - List all clouds and folders
   - Discover compute instances (VMs)
   - Discover disks (boot and secondary)
   - Discover networks and subnets
   - Multi-folder support

3. **Resource Details**
   - VM specifications (vCPUs, RAM, disk)
   - Network interfaces and IP addresses (internal and external)
   - Disk attachments and sizes
   - Availability zones
   - Resource status tracking

4. **Cost Estimation**
   - Estimated costs for VMs (based on vCPU, RAM, storage)
   - Estimated costs for standalone disks
   - Daily and monthly cost projections

5. **Sync Operations**
   - Full resource synchronization
   - Change detection (created, updated, unchanged)
   - Resource state tracking across syncs

### 🔄 Planned

1. **Billing API Integration**
   - Actual cost data from Yandex Cloud Billing API
   - Historical billing data
   - Cost breakdown by service

2. **Additional Resources**
   - Kubernetes clusters (Managed Service for Kubernetes)
   - Databases (Managed PostgreSQL, MySQL, MongoDB, etc.)
   - Object Storage (S3-compatible)
   - Load Balancers
   - Container Registry

3. **Performance Metrics**
   - CPU usage statistics
   - Memory usage statistics
   - Network I/O metrics

## API Endpoints

### Test Connection
```
POST /api/yandex/test/<provider_id>
```

Tests the connection to Yandex Cloud API and verifies credentials.

**Response:**
```json
{
  "success": true,
  "message": "Connection successful",
  "clouds_found": 1,
  "clouds": [
    {
      "id": "b1g...",
      "name": "My Cloud",
      "organizationId": "bpf..."
    }
  ]
}
```

### Sync Resources
```
POST /api/yandex/sync/<provider_id>
```

Synchronizes all resources from Yandex Cloud.

**Response:**
```json
{
  "success": true,
  "resources_synced": 15,
  "total_instances": 12,
  "total_disks": 3,
  "estimated_daily_cost": 450.50,
  "sync_snapshot_id": 123,
  "message": "Successfully synced 15 resources (estimated cost: 450.50 ₽/day)"
}
```

### List Folders
```
GET /api/yandex/folders/<provider_id>
```

Lists all folders in the connected cloud.

### List Clouds
```
GET /api/yandex/clouds/<provider_id>
```

Lists all accessible clouds.

## Architecture

The Yandex Cloud integration follows the same architectural pattern as other providers:

```
app/providers/yandex/
├── __init__.py       # Package initialization
├── client.py         # YandexClient - API communication layer
├── service.py        # YandexService - Business logic and sync
└── routes.py         # Flask routes (optional)
```

### YandexClient

Handles low-level API communication:
- IAM token generation and refresh
- API request execution
- Resource listing and details
- Error handling

### YandexService

Implements business logic:
- Resource synchronization
- Cost estimation
- Database operations
- Change detection

## Usage Example

### Adding Yandex Cloud Provider via UI

1. Navigate to "Connections" page
2. Click "Add Provider"
3. Select "Yandex Cloud"
4. Fill in credentials:
   - **Name**: "My Yandex Cloud"
   - **Provider Type**: yandex
   - **Credentials**: Paste your service account key JSON
   - **Account ID**: Your cloud ID (optional, will be auto-discovered)
5. Click "Test Connection"
6. Click "Save"
7. Click "Sync" to fetch resources

### Adding Yandex Cloud Provider via API

```python
import requests
import json

# Prepare credentials
credentials = {
    "service_account_key": {
        "id": "...",
        "service_account_id": "...",
        "private_key": "...",
        "public_key": "..."
    },
    "cloud_id": "b1g..."
}

# Create provider
response = requests.post(
    'http://localhost:5001/api/providers',
    json={
        'provider_name': 'My Yandex Cloud',
        'provider_type': 'yandex',
        'credentials': json.dumps(credentials),
        'auto_sync': True
    },
    headers={'Authorization': f'Bearer {your_auth_token}'}
)

provider_id = response.json()['id']

# Test connection
test_response = requests.post(
    f'http://localhost:5001/api/yandex/test/{provider_id}'
)

# Sync resources
sync_response = requests.post(
    f'http://localhost:5001/api/yandex/sync/{provider_id}'
)
```

## Cost Estimation Formula

Since Yandex Cloud Billing API requires special permissions, the integration includes cost estimation based on resource specifications:

### VM Costs (Daily)
```
daily_cost = (
    vcpus * 1.50 ₽/hour * 24 hours +
    ram_gb * 0.40 ₽/GB/hour * 24 hours +
    storage_gb * 0.0025 ₽/GB/hour * 24 hours
)
```

### Disk Costs (Daily)
```
# HDD
daily_cost = size_gb * 0.0015 ₽/GB/hour * 24 hours

# SSD
daily_cost = size_gb * 0.0050 ₽/GB/hour * 24 hours

# NVMe
daily_cost = size_gb * 0.0070 ₽/GB/hour * 24 hours
```

**Note**: These are conservative estimates. Replace with actual billing data when Billing API access is available.

## Troubleshooting

### Connection Test Fails

**Error**: "IAM token generation failed"

**Solution**: 
1. Verify service account key is valid JSON
2. Check that the service account exists and is not deleted
3. Ensure the service account has the required permissions

**Error**: "IAM token valid but API access failed"

**Solution**:
1. Verify the service account has `viewer` role
2. Check that the cloud/folder IDs are correct
3. Ensure the service account is in the correct organization

### No Resources Found

**Solution**:
1. Verify that you have resources in your folders
2. Check that folder_id is correct or remove it to auto-discover
3. Ensure the service account has access to the folders
4. Check firewall rules if running on-premises

### Costs Show as "Estimated"

This is expected behavior. The integration uses cost estimation formulas because:
1. Billing API requires special permissions
2. Some users may not have billing access
3. Provides immediate cost visibility during setup

To get actual costs:
1. Grant `billing.accounts.viewer` permission to service account
2. Enable Billing API access in Yandex Cloud Console
3. The integration will automatically use actual billing data when available

## Comparison with Other Providers

| Feature | Yandex Cloud | Selectel | Beget |
|---------|-------------|----------|-------|
| Authentication | IAM Tokens (JWT) | Dual (API Key + Service User) | API Key |
| Billing API | Requires permissions | Full access | Full access |
| Resource Discovery | Multi-cloud/folder | Multi-region/project | Single account |
| Cost Data | Estimated (actual if permissions granted) | Actual from billing | Actual from billing |
| VM Details | Full (CPU, RAM, disk, IP) | Full with OpenStack | Full with API |
| Multi-tenancy | Clouds → Folders | Projects | None |

## Security Considerations

1. **Service Account Key Storage**
   - Stored encrypted in database
   - Private key never logged or displayed
   - Rotated regularly (recommended every 90 days)

2. **Least Privilege**
   - Use `viewer` roles only
   - Don't grant write permissions
   - Separate service accounts per environment

3. **Token Management**
   - IAM tokens cached with expiration tracking
   - Automatic refresh before expiration
   - No manual token management required

## Future Enhancements

1. **Billing API Integration**
   - Full integration with Billing API when permissions available
   - Historical cost analysis
   - Budget alerts

2. **Additional Services**
   - Managed Kubernetes (MKS)
   - Managed Databases
   - Object Storage
   - Load Balancers
   - Container Registry

3. **Performance Monitoring**
   - Integration with Yandex Monitoring API
   - CPU/Memory usage graphs
   - Custom metrics support

4. **Recommendations**
   - Right-sizing recommendations
   - Idle resource detection
   - Cost optimization suggestions

## Links

- [Yandex Cloud Documentation](https://cloud.yandex.com/docs)
- [Yandex Cloud API Reference](https://cloud.yandex.com/docs/api-design-guide/)
- [IAM Authentication](https://cloud.yandex.com/docs/iam/concepts/authorization/)
- [Service Accounts](https://cloud.yandex.com/docs/iam/concepts/users/service-accounts)
- [Billing API](https://cloud.yandex.com/docs/billing/api-ref/)

## Support

For issues or questions about the Yandex Cloud integration:

1. Check this documentation first
2. Review logs in `server.log`
3. Enable debug logging: `LOG_LEVEL=DEBUG` in config.env
4. Contact support with:
   - Provider ID
   - Error message from logs
   - Connection test results (without credentials)

