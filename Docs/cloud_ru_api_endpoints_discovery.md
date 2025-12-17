# Cloud.ru API Endpoints Discovery

## Overview

This document catalogs all `/u-api/` endpoints discovered from HAR files, organized by service type.

## Key Discovery Endpoints

### Product Discovery

**Endpoint**: `GET /u-api/bff-console/v1/project/{project_id}/aggregated-available-products`

**Purpose**: Lists all available products/services (98 products found)

**Response Structure**:
```json
{
  "products": [
    {
      "int_name": "product_internal_name",
      "name": "Product Display Name",
      "status": "active",
      "id": "product_id"
    }
  ]
}
```

**Use Cases**:
- Discover all available services
- Find product IDs for pricing calculations
- Check service availability

**Alternative Endpoints**:
- `GET /u-api/bff-console/v1/agreements/{agreement_id}/available-products` - Products by agreement
- `GET /u-api/bff-console/v1/projects/{project_id}/product-instances` - Existing product instances

## Service Categories

### 1. SVP (Compute/VMs/Network Load Balancer)

**Base Path**: `/u-api/svp/`

**Endpoints**:
- `GET /u-api/svp/svc/v1/subnets` - List subnets
- `GET /u-api/svp/v2/nlb/availability-zones` - Load balancer availability zones
- `GET /u-api/svp/v2/nlb/calculate-price` - Load balancer pricing
- `GET /u-api/svp/vpc/v1/vpcs` - List VPCs

**Pricing**: ✅ Load balancer pricing endpoint found

### 2. MK8S (Managed Kubernetes)

**Base Path**: `/u-api/mk8s/`

**Endpoints**:
- `GET /u-api/mk8s-bff/v1/productConfiguration` - Kubernetes product configuration (flavors, zones, disk types)
- `POST /u-api/mk8s/v2/billing/calculate-price-ext` - Kubernetes pricing
- `GET /u-api/mk8s/v2/quotas/project/{project_id}` - Kubernetes quotas

**Pricing**: ✅ Kubernetes pricing endpoint found

### 3. PAAS-BFF (Platform as a Service - Databases)

**Base Path**: `/u-api/paas-bff/api/v1/`

**Endpoints**:
- `GET /u-api/paas-bff/api/v1/availability-zones` - Database availability zones
- `GET /u-api/paas-bff/api/v1/disks/postgres` - PostgreSQL disk configurations
- `GET /u-api/paas-bff/api/v1/flavors` - Database flavors
- `GET /u-api/paas-bff/api/v1/postgres/versions` - PostgreSQL versions
- `GET /u-api/paas-bff/api/v1/postgres/version/{version_id}/locales` - Version locales
- `GET /u-api/paas-bff/api/v1/postgres/version/{version_id}/options` - Version options
- `POST /u-api/paas-bff/api/v1/price-calculator/sku-list` - Database pricing (SKU-based)
- `GET /u-api/paas-bff/api/v1/product-activations/{project_id}` - Product activations
- `GET /u-api/paas-bff/api/v1/task/list` - Task list

**Pricing**: ✅ Database pricing endpoint found (SKU-based)

**Supported Databases**: PostgreSQL, MySQL, Redis, MongoDB, Kafka (based on SKU patterns)

### 4. BFF-CONSOLE (Console Backend)

**Base Path**: `/u-api/bff-console/`

**Key Endpoints**:
- `GET /u-api/bff-console/v1/project/{project_id}/aggregated-available-products` - All available products
- `GET /u-api/bff-console/v1/projects/{project_id}/product-instances` - Product instances
- `GET /u-api/bff-console/v1/agreements/{agreement_id}/available-products` - Products by agreement
- `GET /u-api/bff-console/v1/agreements/{agreement_id}/product-instances` - Product instances by agreement
- `GET /u-api/bff-console/v2/agreements/{agreement_id}/balance` - Account balance
- `GET /u-api/bff-console/v1/projects/{project_id}/service-accounts` - Service accounts

**Use Cases**:
- Product discovery
- Account management
- Service account management

### 5. SCKM (Secrets/Keys Management)

**Base Path**: `/u-api/sckm/`

**Endpoints**:
- `GET /u-api/sckm/v1/keys` - List keys

**Pricing**: ❓ Unknown (likely free or usage-based)

### 6. VPC (Virtual Private Cloud)

**Base Path**: `/u-api/svp/vpc/`

**Endpoints**:
- `GET /u-api/svp/vpc/v1/vpcs` - List VPCs

**Pricing**: ❓ Unknown (likely included in network pricing)

## Additional Services Found (Need HAR Files for Pricing)

From the product discovery endpoint, these services exist but pricing endpoints weren't captured:

1. **Object Storage (S3)** - `S3E` product
   - Product Name: "Evolution Object Storage"
   - Status: `PRODUCT_STATUS_ACTIVE`
   - Need HAR file from S3 bucket creation or pricing page
   - Expected endpoint: `/u-api/s3e/` or `/u-api/storage/` or similar

2. **Container Registry** - `ARTIFACT_REGISTRY` product
   - Product Name: "Evolution Artifact Registry"
   - Status: `PRODUCT_STATUS_ACTIVE`
   - Need HAR file from registry creation
   - Expected endpoint: `/u-api/artifact-registry/` or `/u-api/registry/` or similar

3. **Backup Services** - `AGENT_BACKUP` product
   - Product Name: "Evolution Agent Backup"
   - Status: `PRODUCT_STATUS_ACTIVE`
   - Need HAR file from backup setup
   - Expected endpoint: `/u-api/agent-backup/` or `/u-api/backup/` or similar

4. **Monitoring** - `MONAAS` product
   - Product Name: "Cloud Monitoring"
   - Status: `PRODUCT_STATUS_ACTIVE`
   - Need HAR file from monitoring setup
   - Expected endpoint: `/u-api/monaas/` or `/u-api/monitoring/` or similar

5. **Logging** - `LOGGING_AS_A_SERVICE` product
   - Product Name: "Logging"
   - Status: `PRODUCT_STATUS_ACTIVE`
   - Need HAR file from logging setup
   - Expected endpoint: `/u-api/logging/` or `/u-api/logging-as-a-service/` or similar

6. **CDN** - `CDN` product
   - Product Name: "CDN"
   - Status: `PRODUCT_STATUS_ACTIVE`
   - Need HAR file from CDN setup
   - Expected endpoint: `/u-api/cdn/` or `/u-api/content-delivery/` or similar

7. **Container Apps** - `SERVERLESS_CONTAINER` product
   - Product Name: "Evolution Container Apps"
   - Status: `PRODUCT_STATUS_ACTIVE`
   - Need HAR file from container app creation
   - Expected endpoint: `/u-api/serverless-container/` or `/u-api/container-apps/` or similar

## Pricing Endpoints Summary

| Service | Endpoint | Method | Status |
|---------|----------|--------|--------|
| VMs/Compute | `/u-api/svp/svc/v1/projects/{project_id}/price-calculation` | POST | ✅ Found |
| Kubernetes | `/u-api/mk8s/v2/billing/calculate-price-ext` | POST | ✅ Found |
| Load Balancer | `/u-api/svp/v2/nlb/calculate-price` | GET | ✅ Found |
| Databases | `/u-api/paas-bff/api/v1/price-calculator/sku-list` | POST | ✅ Found |
| Object Storage (S3E) | Unknown | - | ❌ Need HAR (Product: S3E) |
| Container Registry (ARTIFACT_REGISTRY) | Unknown | - | ❌ Need HAR (Product: ARTIFACT_REGISTRY) |
| Backup (AGENT_BACKUP) | Unknown | - | ❌ Need HAR (Product: AGENT_BACKUP) |
| Monitoring (MONAAS) | Unknown | - | ❌ Need HAR (Product: MONAAS) |
| Logging (LOGGING_AS_A_SERVICE) | Unknown | - | ❌ Need HAR (Product: LOGGING_AS_A_SERVICE) |
| CDN | Unknown | - | ❌ Need HAR (Product: CDN) |
| Container Apps (SERVERLESS_CONTAINER) | Unknown | - | ❌ Need HAR (Product: SERVERLESS_CONTAINER) |

## Product Discovery Strategy

To find product instances for pricing:

1. **For Load Balancers**:
   - Use `GET /u-api/bff-console/v1/projects/{project_id}/product-instances`
   - Filter by `int_name` containing "nlb" or "load"
   - Extract `productInstanceId` from response

2. **For Databases**:
   - Use `GET /u-api/paas-bff/api/v1/product-activations/{project_id}`
   - Or filter `product-instances` by database types (postgres, mysql, redis, etc.)
   - Extract `product_instance_id` from response

3. **For Other Services**:
   - Use `GET /u-api/bff-console/v1/project/{project_id}/aggregated-available-products`
   - Filter by `int_name` matching service type
   - Use product ID to find pricing endpoints

## Next Steps

1. ✅ Document all discovered endpoints
2. ⏳ Implement product discovery methods
3. ⏳ Implement pricing methods for found services
4. ⏳ Request HAR files for missing services (S3, Registry, Backup, Monitoring, CDN)
5. ⏳ Test product instance discovery
6. ⏳ Test pricing calculations for all services

