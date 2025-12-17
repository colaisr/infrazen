# Cloud.ru Pricing API Research

## Overview

This document outlines the findings from analyzing the HAR file for Cloud.ru VM creation and Kubernetes cluster creation, and how to implement pricing fetching similar to other providers (Beget, Selectel, Yandex).

## Key Findings from HAR File

### 1. Price Calculation Endpoint

**Endpoint**: `POST /u-api/svp/svc/v1/projects/{project_id}/price-calculation`

**Base URL**: `https://console.cloud.ru`

**Request Body**:
```json
{
  "total_count": 1,
  "image_id": "474c9e98-760f-4e54-aaa9-70024814f2b0",
  "flavor_id": "22c9e630-2e31-4792-91d5-bc095386836d",
  "disks": [
    {
      "disk_type_id": "a859e3dc-6b14-42a8-9bcc-890fde0ba6d0",
      "size": 10
    }
  ]
}
```

**Response**:
```json
{
  "flavor": 454.9,
  "image": 0.0,
  "disks": 112.32,
  "floating_ips": 0.0,
  "nat_gateways": 0.0,
  "total_price_month": 567.22,
  "total_price_hour": 0.79
}
```

**Notes**:
- Requires `project_id` in URL path
- Returns monthly and hourly costs
- Breaks down costs by component (flavor, image, disks, floating_ips, nat_gateways)
- **Can calculate prices for multiple resource types**:
  - **VMs**: Via `flavor_id` → returns `flavor` cost
  - **Disks**: Via `disk_type_id` + `size` → returns `disks` cost
  - **Floating IPs**: If included in request → returns `floating_ips` cost
  - **NAT Gateways**: If included in request → returns `nat_gateways` cost
  - **Images**: Usually free (0.0)

### 2. Flavors Endpoint

**Endpoint**: `GET /u-api/svp/svc/v1/flavors`

**Query Parameters**:
- `project_id` (required)
- `limit` (default: 100)
- `offset` (for pagination)
- `type` (e.g., "general")
- `availability_zone_id` (optional)
- `oversubscription` (e.g., "1:3")

**Example**:
```
GET /u-api/svp/svc/v1/flavors?limit=100&project_id=0ae87bd4-4675-4d08-9103-387a87b3de40&type=general&offset=0
```

**Purpose**: Lists available VM flavors with specifications (CPU, RAM, disk)

**Response Structure**:
```json
{
  "items": [
    {
      "id": "04d3bff2-b078-483d-bcca-e6587770af39",
      "name": "gen-12-96",
      "description": "",
      "type": "general",
      "flavor_type": {
        "id": "df425f97-ced9-4f4b-9965-2a5a353fc91c",
        "name": "general-1",
        "display_name": "Общий 1:1",
        "cpu_type": "Intel Broadwell EP Xeon E5-2699",
        "oversubscription": "1:1"
      },
      "cpu": 12,
      "ram": 96,
      "gpu": 0,
      "oversubscription": "1:1",
      "availability_zones": [
        {
          "availability_zone_id": "7c99a597-8516-494f-a2c7-d7377048681e",
          "availability_zone_name": "ru.AZ-1",
          "enabled": true
        }
      ]
    }
  ],
  "offset": 0,
  "limit": 100,
  "total": 50
}
```

**Key Fields**:
- `id`: Flavor ID (used in price-calculation)
- `name`: Flavor name (e.g., "gen-12-96" = 12 CPU, 96 GB RAM)
- `cpu`: Number of CPU cores
- `ram`: RAM in GB
- `type`: Flavor type (e.g., "general")
- `flavor_type.oversubscription`: Oversubscription ratio (e.g., "1:1", "1:3")
- `availability_zones`: List of available zones (ru.AZ-1, ru.AZ-2, ru.AZ-3)

### 3. Flavor Parameters Endpoint

**Endpoint**: `GET /u-api/svp/svc/v1/params/flavor`

**Query Parameters**:
- `project_id` (required)
- `param_type` (e.g., "flavor-type", "oversubscription")
- `availability_zone_id` (optional)

**Purpose**: Get flavor configuration options (types, oversubscription ratios)

### 5. Kubernetes Pricing Endpoint (Different from VM Pricing!)

**Endpoint**: `POST /u-api/mk8s/v2/billing/calculate-price-ext`

**Base URL**: `https://console.cloud.ru`

**Request Body**:
```json
{
  "master": {
    "count": 1,
    "flavorId": "82d31572-23e0-4937-a6af-45ddae64ba87"
  },
  "projectId": "0ae87bd4-4675-4d08-9103-387a87b3de40",
  "nodePoolPrices": [],  // Optional: node pool configurations
  "volumePrices": []    // Optional: volume configurations
}
```

**Response**:
```json
{
  "masterPrice": {
    "resourceCode": "master.2.4_10",
    "resourceCount": 1,
    "price": {
      "streetPriceWithVatPerHour": 4.4551,
      "discountPerHour": 0,
      "privatePriceWithVatPerHour": 4.4551
    },
    "totalStreetPriceWithVatPerHour": 4.4551,
    "totalPrivatePriceWithVatPerHour": 4.4551
  },
  "nodePoolPrices": [],
  "volumePrices": [],
  "totalStreetPriceWithVatPerHour": 4.4551,
  "totalPrivatePriceWithVatPerHour": 4.4551
}
```

**Key Differences from VM Pricing**:
- Uses **different API path**: `/mk8s/v2/billing/` instead of `/svp/svc/v1/`
- Returns **hourly prices with VAT** (not monthly)
- Includes `resourceCode` (e.g., "master.2.4_10" = 2 CPU, 4 GB RAM, 10 GB disk)
- Supports **node pools** and **volumes** pricing
- Returns prices in **RUB with VAT** (`streetPriceWithVatPerHour`, `privatePriceWithVatPerHour`)

**Notes**:
- Kubernetes uses **different flavor IDs** than regular VMs
- Need to fetch Kubernetes-specific flavors (likely from `/mk8s/v2/` endpoints)
- Can calculate prices for master nodes, worker nodes (node pools), and volumes

### 4. Disk Types Endpoint

**Endpoint**: `GET /u-api/svp/svc/v1/disk-types`

**Query Parameters**:
- `project_id` (required)
- `availability_zone_id` (optional)

**Response Structure**:
```json
[
  {
    "id": "a859e3dc-6b14-42a8-9bcc-890fde0ba6d0",
    "name": "SSD",
    "display_name": "SDS",
    "min_size": 1,
    "max_size": 16384,
    "free_tier": false,
    "speed_limits": [
      {
        "size": 1,
        "limit_rate": 5000,
        "limit_bw": 64
      }
    ],
    "availability_zones": [...]
  }
]
```

**Purpose**: Lists available disk types with size limits and speed specifications

## How Other Providers Work

### Beget
- Uses **configurator API** (`/v1/vps/configurator/info`)
- Builds pricing grid by querying different CPU/RAM/Disk combinations
- Returns standardized format with `cpu_cores`, `ram_gb`, `storage_gb`, `hourly_cost`, `monthly_cost`

### Selectel
- Uses **billing API** (`/v2/billing/vpc/prices`)
- Fetches unit prices for resources (compute_cores, volume_gb, etc.)
- Builds grid pricing by combining unit prices
- Returns standardized format

### Yandex
- Uses **SKU pricing API** (`/billing/v1/skus`)
- Fetches all SKUs, then individual SKU details
- Extracts pricing from `pricingVersions` and `pricingExpressions`
- Returns standardized format

## What Can We Fetch?

### Answer: Multiple Resource Types via Price Calculation API

The `price-calculation` endpoint can return prices for **multiple resource types**, but requires different request configurations:

1. **VM Pricing** (servers):
   - Use `flavor_id` in request
   - Returns `flavor` cost component
   - Can combine with disks for total VM cost

2. **Disk/Volume Pricing**:
   - Use `disk_type_id` + `size` in request
   - Returns `disks` cost component
   - Can fetch standalone disk pricing by omitting `flavor_id`

3. **Floating IP Pricing**:
   - Include floating IPs in request (need to find how)
   - Returns `floating_ips` cost component

4. **NAT Gateway Pricing**:
   - Include NAT gateways in request (need to find how)
   - Returns `nat_gateways` cost component

**Note**: Unlike Selectel's billing API which returns all unit prices at once, Cloud.ru requires **individual price calculations** for each configuration.

### 5. Kubernetes Pricing (Uses Different Endpoint!)

**Kubernetes Pricing Endpoint**: `POST /u-api/mk8s/v2/billing/calculate-price-ext`

**Kubernetes Flavors Endpoint**: `GET /u-api/mk8s-bff/v1/productConfiguration?projectId={project_id}`

**Key Differences from VM Pricing**:
- **Different API path**: Uses `/mk8s/v2/billing/` instead of `/svp/svc/v1/`
- **Different flavor source**: Kubernetes flavors come from `productConfiguration` endpoint
- **Different pricing format**: Returns hourly prices with VAT (not monthly)
- **Resource codes**: Includes `resourceCode` (e.g., "master.2.4_10" = 2 CPU, 4 GB RAM, 10 GB disk)
- **Supports node pools**: Can calculate prices for worker node pools separately

**Kubernetes Flavor Structure**:
```json
{
  "flavorId": "e1ca8700-ad11-4fc2-bdd3-1a95e2ae7052",
  "name": "gen-16-128",
  "cpu": 16,
  "ram": 128,
  "oversubscription": "1:1",
  "gpu": 0,
  "purpose": "FLAVOR_PURPOSE_DATAPLANE",
  "zones": ["ru.AZ-1", "ru.AZ-2", "ru.AZ-3"]
}
```

**Summary**: Cloud.ru uses **MULTIPLE different pricing endpoints**:

### ✅ Confirmed Pricing Endpoints (6):
1. **VM/Compute pricing**: `/u-api/svp/svc/v1/projects/{project_id}/price-calculation`
2. **Kubernetes pricing**: `/u-api/mk8s/v2/billing/calculate-price-ext`
3. **Load Balancer pricing**: `GET /u-api/svp/v2/nlb/calculate-price`
4. **Database pricing** (PostgreSQL, Redis, MySQL, Kafka, etc.): `POST /u-api/paas-bff/api/v1/price-calculator/sku-list`
   - **Note**: All managed databases use the same endpoint with different SKU codes:
     - PostgreSQL: `paas_postgres.{resource}#{tier}#{platform}`
     - Redis: `paas_redis.{resource}#{tier}#{platform}` ✅ Confirmed
     - MySQL: `paas_mysql.{resource}#{tier}#{platform}` (likely)
     - Kafka: `paas_kafka.{resource}#{tier}#{platform}` (likely)
5. **Container Registry pricing**: `GET /u-api/container-registry/v1/api/v3/{project_id}/tariffs/`
6. **S3 Object Storage pricing**: ❌ **No pricing endpoint** - Usage-based, use billing API + static unit prices

### ❌ No Pricing Endpoints Found:
7. **Container Apps pricing**: ❌ **No pricing endpoint found** - Instance-types endpoint exists but contains no pricing data

### 8. Managed Spark Pricing (Under Investigation)

**Status**: ⚠️ **Pricing endpoint exists but returns 400 error**

**Findings from HAR Analysis**:
- HAR file captured: `spark.har`
- Pricing endpoint attempted: `POST /u-api/bff-console/v1/price-calculator/sku-list`
- **Result**: 400 Bad Request (likely wrong parameters or SKU codes)
- Spark flavors endpoint: `GET /u-api/dataplatform/api/v1/{project_id}/flavors`

**Possible Reasons for 400 Error**:
1. Wrong `product_instance_id` for Spark
2. Wrong SKU code pattern (Spark might use different pattern than databases)
3. Spark might use a different pricing endpoint
4. Need to check Spark-specific pricing endpoint

**Next Steps**:
- Check if Spark uses `/u-api/dataplatform/api/v1/` pricing endpoint
- Verify correct `product_instance_id` for Spark
- Check if Spark SKU codes follow different pattern

### 6. Load Balancer Pricing Endpoint

**Endpoint**: `GET /u-api/svp/v2/nlb/calculate-price`

**Base URL**: `https://console.cloud.ru`

**Query Parameters**:
- `productInstanceId` (required): Load balancer product instance ID
- `availabilityZoneCount` (required): Number of availability zones (e.g., 3)
- `withExternalAddress` (required): Boolean (true/false) - whether to include external IP

**Response**:
```json
{
  "pricePerHour": {
    "total": 4.944,
    "replicas": 4.74,
    "externalAddress": 0.204
  },
  "pricePerDay": {
    "total": 118.656,
    "replicas": 113.76,
    "externalAddress": 4.896
  },
  "pricePerMonth": {
    "total": 3559.68,
    "replicas": 3412.8,
    "externalAddress": 146.88
  },
  "replicaCount": 6,
  "replicaPrice": 0.79,
  "externalAddressPrice": 0.204,
  "incomingTrafficPrice": 0.0584,
  "outgoingTrafficPrice": 0.0584
}
```

**Key Fields**:
- Returns hourly, daily, and monthly prices
- Breaks down by component: replicas, external address, traffic
- Includes unit prices: `replicaPrice`, `externalAddressPrice`, `incomingTrafficPrice`, `outgoingTrafficPrice`
- `replicaCount`: Number of load balancer replicas

**Notes**:
- Requires `productInstanceId` - need to fetch available load balancer product instances first
- Pricing varies by availability zone count
- External address is optional (adds cost)
- Traffic pricing is per GB (incoming/outgoing)

### 7. S3 Object Storage Pricing (No API Endpoint Found)

**Status**: ❌ **No pricing endpoint discovered**

**Findings from HAR Analysis**:
- HAR file captured: `menue.har` (S3 storage page)
- S3-specific endpoints found:
  - `GET /u-api/s3e-controller/v2/access/api-configuration`
  - `GET /u-api/s3e-controller/v2/projects/{project_id}`
- **No pricing calculation endpoints** found in HAR file

**Pricing Information Source**: Documentation-based
- Documentation: `https://cloud.ru/docs/s3e/ug/topics/pricing`
- Pricing appears to be **static unit prices**, not dynamically calculated

**Pricing Structure** (from documentation):
- **Storage Classes**:
  - Standard: 1.809 ₽/GB/month (15 GB free tier)
  - Cold: 0.963 ₽/GB/month
  - Ice: 0.4815 ₽/GB/month
  - Single-Zone: 1.116 ₽/GB/month
- **Outgoing Traffic**: 1.035 ₽/GB (10 TB free tier)
- **API Operations**:
  - GET/HEAD: 0.0324 ₽/1,000 operations (1M free)
  - POST/PUT: 0.108 ₽/1,000 operations (100K free)

**Implementation Strategy**:
Since there's no pricing API endpoint, we can:
1. **Use static pricing** from documentation (unit prices)
2. **Calculate costs** based on usage:
   - Storage: `(storage_gb - free_tier) * price_per_gb`
   - Traffic: `(traffic_gb - free_tier) * price_per_gb`
   - Operations: `(operations - free_tier) / 1000 * price_per_1k`
3. **Get usage data** from billing API (consumption records)
4. **Build pricing records** with standardized format

**Note**: S3 pricing is **usage-based** and calculated from actual consumption, not from a "create bucket" action. The pricing endpoint might only be available:
- After bucket creation
- In billing/consumption API
- Via a different service endpoint we haven't discovered

### 8. Database Pricing Endpoint

**Endpoint**: `POST /u-api/paas-bff/api/v1/price-calculator/sku-list`

**Base URL**: `https://console.cloud.ru`

**Request Body**:
```json
{
  "product_instance_id": "9392c7c2-88fd-4127-a9bb-1bb97e2da786",
  "sku_list": [
    {
      "quantity": 1,
      "resource_spec_code": "paas_postgres.cpu#standard#evolution"
    },
    {
      "quantity": 4,
      "resource_spec_code": "paas_postgres.ram#standard#evolution"
    },
    {
      "quantity": 10,
      "resource_spec_code": "paas_postgres.storage#nvme#evolution"
    }
  ]
}
```

**Response**:
```json
{
  "sku_list": [
    {
      "quantity": 1,
      "price": {
        "value": 1.2225,
        "street_value": 1.2225,
        "source": "PRICE_SOURCE_AGREEMENT",
        "quantum": "QUANTUM_HOUR",
        "value_with_vat": 1.467
      },
      "total_price": 1.2225,
      "total_street_price": 1.2225,
      "sku_code": "S-PGRCRKESHRD1F000-HS0",
      "res_spec_code": "paas_postgres.cpu#standard#evolution",
      "display_name": "",
      "status": "SKU_STATUS_ACTIVE",
      "total_price_with_vat": 1.467
    }
  ]
}
```

**Key Fields**:
- `product_instance_id`: Database product instance ID (PostgreSQL, MySQL, Redis, etc.)
- `sku_list`: Array of SKU specifications with:
  - `quantity`: Number of units
  - `resource_spec_code`: SKU code format: `paas_{db_type}.{resource}#{tier}#{platform}`
    - Examples:
      - `paas_postgres.cpu#standard#evolution` - PostgreSQL CPU
      - `paas_postgres.ram#standard#evolution` - PostgreSQL RAM (in GB)
      - `paas_postgres.storage#nvme#evolution` - PostgreSQL storage (in GB)
- Response includes hourly prices with/without VAT
- `quantum`: Pricing unit (QUANTUM_HOUR for hourly)

**Database Flavors Endpoint**: `GET /u-api/paas-bff/api/v1/flavors?availability_zone_id={zone_id}`

**Notes**:
- Uses SKU-based pricing (similar to Yandex)
- Need to fetch available database product instances first
- SKU codes follow pattern: `paas_{db_type}.{resource}#{tier}#{platform}`
- Supports PostgreSQL, MySQL, Redis, MongoDB, Kafka, etc.
- Pricing is calculated per SKU (CPU, RAM, storage)
- Prices are hourly, need to convert to monthly (hourly * 730)

## Implementation Strategy for Cloud.ru

### Approach 1: Price Calculation API (Recommended)

**Pros**:
- Direct pricing from Cloud.ru
- Accurate costs for specific configurations
- Includes all components (flavor, disks, images)

**Cons**:
- Requires knowing flavor_id, image_id, disk_type_id
- Need to query all available flavors first
- May require multiple API calls per flavor

**Steps**:
1. **VM Pricing**:
   - Fetch all available flavors using `/flavors` endpoint
   - For each flavor, call `/price-calculation` with `flavor_id`
   - Extract CPU, RAM from flavor data
   - Normalize to standard format

2. **Disk/Volume Pricing**:
   - Fetch all disk types using `/disk-types` endpoint
   - For each disk type, call `/price-calculation` with `disk_type_id` and various sizes (e.g., 10GB, 50GB, 100GB, 500GB, 1TB)
   - Extract disk pricing per GB or per size tier
   - Normalize to standard format

3. **Kubernetes Pricing**:
   - Fetch Kubernetes flavors from `/mk8s-bff/v1/productConfiguration?projectId={project_id}`
   - For each flavor, call `/mk8s/v2/billing/calculate-price-ext` with `master.flavorId`
   - Extract CPU, RAM from flavor data
   - Convert hourly prices to monthly (hourly * 730 hours/month)
   - Normalize to standard format with `resource_type: 'kubernetes'`

4. **Load Balancer Pricing**:
   - Fetch available load balancer product instances (need to find endpoint)
   - For each product instance, call `/svp/v2/nlb/calculate-price` with different configurations:
     - Vary `availabilityZoneCount` (1, 2, 3)
     - Vary `withExternalAddress` (true/false)
   - Extract unit prices: `replicaPrice`, `externalAddressPrice`, `incomingTrafficPrice`, `outgoingTrafficPrice`
   - Normalize to standard format with `resource_type: 'load_balancer'`

5. **Database Pricing**:
   - Fetch available database product instances (PostgreSQL, MySQL, Redis, etc.)
   - Fetch database flavors from `/paas-bff/api/v1/flavors`
   - For each database type and flavor, build SKU list:
     - CPU: `paas_{db_type}.cpu#standard#evolution`
     - RAM: `paas_{db_type}.ram#standard#evolution`
     - Storage: `paas_{db_type}.storage#nvme#evolution` or `paas_{db_type}.storage#ssd#evolution`
   - Call `/paas-bff/api/v1/price-calculator/sku-list` with SKU list
   - Extract CPU, RAM, storage from SKU codes
   - Convert hourly prices to monthly (hourly * 730)
   - Normalize to standard format with `resource_type: 'database'`

6. **Network Pricing** (Floating IPs, NAT Gateways):
   - Can be extracted from VM price-calculation response (floating_ips, nat_gateways components)
   - Or check if there are separate pricing endpoints

7. **Combine all pricing records** into single list

### Approach 2: Billing API (Alternative)

**Pros**:
- May have unit prices similar to Selectel
- Could be more efficient

**Cons**:
- Need to verify if Cloud.ru billing API exposes unit prices
- May not have the same structure as Selectel

**Investigation Needed**:
- Check if `/v1/consumption` or billing endpoints expose unit prices
- Review Cloud.ru billing API documentation

## Standardized Pricing Format

All providers must return pricing data in this format:

```python
{
    'provider': 'cloud-ru',
    'resource_type': 'server',  # or 'volume', 'network', etc.
    'provider_sku': 'flavor-22c9e630-2e31-4792-91d5-bc095386836d',
    'region': 'ru-central1',  # or availability zone
    'cpu_cores': 2,
    'ram_gb': 4,
    'storage_gb': 20,
    'storage_type': 'SSD',
    'extended_specs': {
        'flavor_id': '22c9e630-2e31-4792-91d5-bc095386836d',
        'oversubscription': '1:3',
        'availability_zone_id': '7c99a597-8516-494f-a2c7-d7377048681e'
    },
    'hourly_cost': 0.79,
    'monthly_cost': 567.22,
    'currency': 'RUB',
    'source': 'price_calculation_api',
    'confidence_score': 0.95
}
```

## Implementation Plan

### Step 1: Create CloudRuPricingClient

**File**: `app/providers/cloud_ru/pricing.py`

**Methods**:
- `get_flavors(project_id: str) -> List[Dict]` - Fetch all available flavors
- `calculate_price(project_id: str, flavor_id: str, disk_config: List[Dict]) -> Dict` - Get price for specific config
- `get_all_vm_prices(project_id: str) -> List[Dict]` - Build complete pricing grid

### Step 2: Implement get_pricing_data() in Plugin

**File**: `app/providers/plugins/cloud_ru.py`

**Implementation**:
```python
def get_pricing_data(self) -> List[Dict[str, Any]]:
    try:
        # Get project_id from credentials or client
        project_id = self.client.project_id
        
        # Initialize pricing client
        pricing_client = CloudRuPricingClient(self.client)
        
        # Fetch VM pricing
        vm_prices = pricing_client.get_all_vm_prices(project_id)
        self.logger.info("Collected %d Cloud.ru VM pricing records", len(vm_prices))
        
        # Fetch Kubernetes pricing (uses different endpoint)
        k8s_prices = pricing_client.get_all_k8s_prices(project_id)
        self.logger.info("Collected %d Cloud.ru Kubernetes pricing records", len(k8s_prices))
        
        # Fetch Load Balancer pricing
        lb_prices = pricing_client.get_all_lb_prices(project_id)
        self.logger.info("Collected %d Cloud.ru Load Balancer pricing records", len(lb_prices))
        
        # Fetch Database pricing
        db_prices = pricing_client.get_all_db_prices(project_id)
        self.logger.info("Collected %d Cloud.ru Database pricing records", len(db_prices))
        
        # Fetch volume pricing (if available)
        # Fetch network pricing (if available)
        
        return vm_prices + k8s_prices + lb_prices + db_prices  # + volume_prices + network_prices
    except Exception as exc:
        self.logger.error("Failed to collect Cloud.ru pricing: %s", exc, exc_info=True)
        return []
```

### Step 3: Integration with PriceUpdateService

The `PriceUpdateService` will automatically:
1. Discover Cloud.ru plugin via `ProviderPluginManager`
2. Call `get_pricing_data()` method
3. Save pricing records to `provider_prices` table
4. Update sync status in `provider_catalog`

**No additional changes needed** - follows same pattern as Beget/Selectel.

## Authentication

The pricing client will use the same authentication as the main Cloud.ru client:
- Uses `access_token` from IAM API
- Token expires after 1 hour, auto-refreshed
- Headers: `Authorization: Bearer <access_token>`

## Next Steps

1. ✅ Research pricing endpoints (DONE - found VM and Kubernetes pricing endpoints)
   - ✅ VM pricing: `/u-api/svp/svc/v1/projects/{project_id}/price-calculation`
   - ✅ Kubernetes pricing: `/u-api/mk8s/v2/billing/calculate-price-ext`
   - ✅ Flavors endpoints: `/u-api/svp/svc/v1/flavors` and `/u-api/mk8s-bff/v1/productConfiguration`
2. ⏳ Create `CloudRuPricingClient` class
3. ⏳ Implement `get_all_vm_prices()` method
4. ⏳ Implement `get_all_k8s_prices()` method
5. ⏳ Implement `get_all_lb_prices()` method
6. ⏳ Implement `get_all_db_prices()` method
7. ⏳ Implement `get_pricing_data()` in plugin
8. ⏳ Test pricing sync via `PriceUpdateService`
9. ⏳ Verify pricing data in database

## Questions to Resolve

1. **Disk pricing**: ✅ Found `/disk-types` endpoint - can query available disk types
2. **Network pricing**: How to get floating IP and NAT gateway pricing? (May be included in price-calculation response)
3. **Image pricing**: ✅ Confirmed in HAR - images are 0.0 (free)
4. **Regional pricing**: Do prices vary by availability zone? (Need to test with different zones)
5. **Oversubscription**: How does oversubscription affect pricing? (Flavors have oversubscription field: "1:1", "1:3")
6. **Kubernetes node pools**: How to get pricing for worker node pools? (May need to include in calculate-price-ext request)
7. **Load Balancer product instances**: How to fetch available load balancer product instances? (Need to find endpoint)
8. **Database product instances**: How to fetch available database product instances? (Need to find endpoint)

## References

- HAR file: `Docs/har/console.cloud.ru.har`
- Cloud.ru API docs: `https://cloud.ru/docs/console_api/ug/topics/overview__reestr_api`
- Other provider implementations:
  - Beget: `app/providers/plugins/beget.py` (BegetPricingClient)
  - Selectel: `app/providers/plugins/selectel.py` (SelectelPricingClient, SelectelGridPricingClient)
  - Yandex: `app/providers/plugins/yandex.py` (get_pricing_data method)

