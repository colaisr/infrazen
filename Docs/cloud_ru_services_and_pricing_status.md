# Cloud.ru Services and Pricing Status

## How We Know What Services Cloud.ru Offers

### Source: HAR File Analysis

We discovered the list of **98 products/services** from analyzing HAR files captured when using the Cloud.ru console.

**Endpoint**: `GET /u-api/bff-console/v1/project/{project_id}/aggregated-available-products`

**Response**: JSON containing an array of 98 products, each with:
- `int_name`: Internal product identifier (e.g., "S3E", "CDN", "MONAAS")
- `name`: Display name (e.g., "Evolution Object Storage", "CDN", "Cloud Monitoring")
- `status`: Product status (e.g., "PRODUCT_STATUS_ACTIVE")

**HAR Files Used**:
- `Docs/har/db.har` - Contains the product list response
- `Docs/har/load_balancers.har` - Also contains the product list

### Why We Can't Access It Programmatically

When we tried to call this endpoint from our script, we got:
- **403 Forbidden (RBAC: access denied)**
- The service account doesn't have permission to access this endpoint
- It requires higher-level permissions (likely admin/console access)

## Services List (98 Products)

From the HAR file analysis, Cloud.ru offers these services (sample):

1. **S3E** - Evolution Object Storage (S3)
2. **ARTIFACT_REGISTRY** - Evolution Artifact Registry (Container Registry)
3. **CDN** - CDN
4. **MONAAS** - Cloud Monitoring
5. **LOGGING_AS_A_SERVICE** - Logging
6. **AGENT_BACKUP** - Evolution Agent Backup
7. **SERVERLESS_CONTAINER** - Evolution Container Apps
8. **EIV** - Evolution Compute (VMs)
9. **MK8S** - Evolution Managed Kubernetes
10. **NLB** - Evolution Load Balancer
11. **DBAAS_POSTGRESQL** - Evolution Managed PostgreSQL
12. **PAAS_REDIS** - Evolution Managed Redis
13. **PAAS_KAFKA** - Evolution Managed Kafka
14. ... and 85 more services

**Full list**: See `Docs/cloud_ru_api_endpoints_discovery.md` for complete catalog.

## Do We Need Pricing Endpoints for All Services?

### Short Answer: **No, only for services that have costs**

### Services We Should Price

We should implement pricing for services that:
1. **Have significant costs** (not free/included)
2. **Are commonly used** (VMs, databases, storage, etc.)
3. **Have variable pricing** (usage-based, not fixed)

### Priority List

#### ✅ **High Priority** (Have Pricing Endpoints)
1. **EIV** (VMs/Compute) - ✅ Endpoint found
2. **MK8S** (Kubernetes) - ✅ Endpoint found
3. **NLB** (Load Balancers) - ✅ Endpoint found
4. **DBAAS_POSTGRESQL** (Databases) - ✅ Endpoint found

#### 🔴 **High Priority** (Need Pricing Endpoints)
5. **S3E** (Object Storage) - ❌ Need HAR file
6. **ARTIFACT_REGISTRY** (Container Registry) - ❌ Need HAR file
7. **CDN** - ❌ Need HAR file
8. **MONAAS** (Monitoring) - ❌ Need HAR file (may be free/low cost)
9. **LOGGING_AS_A_SERVICE** (Logging) - ❌ Need HAR file (may be free/low cost)
10. **AGENT_BACKUP** (Backup) - ❌ Need HAR file

#### 🟡 **Medium Priority** (Optional)
- **SERVERLESS_CONTAINER** (Container Apps) - May use same pricing as VMs
- **PAAS_REDIS** (Redis) - May use same pricing endpoint as PostgreSQL
- **PAAS_KAFKA** (Kafka) - May use same pricing endpoint as PostgreSQL

#### 🟢 **Low Priority** (Likely Free/Included)
- UI/Admin services (IAM, Account Registration, etc.)
- Documentation services
- Support services
- Migration tools (one-time use)

## How to Get Pricing Endpoints

### Method 1: HAR File Analysis (Recommended)

1. **User captures HAR file** when:
   - Creating a new service instance
   - Viewing pricing/configuration page
   - Changing service settings

2. **We analyze HAR file** to find:
   - Pricing calculation endpoints
   - Configuration endpoints
   - Request/response structures

3. **We implement** pricing client methods

**Example**: We got pricing endpoints for VMs, Kubernetes, Load Balancers, and Databases from HAR files.

### Method 2: API Documentation (If Available)

- Cloud.ru may have API documentation
- Check: `https://cloud.ru/docs/console_api/ug/topics/overview__reestr_api`
- May list pricing endpoints

### Method 3: Programmatic Discovery (Limited)

- Our discovery script tried this
- **Result**: Limited by RBAC permissions
- Can verify endpoints exist but can't discover new ones

## Current Status

### ✅ Services with Pricing Endpoints (4)
- VMs/Compute
- Kubernetes
- Load Balancers
- Databases (PostgreSQL, MySQL, Redis, Kafka)

### ❌ Services Needing Pricing Endpoints (6+)
- Object Storage (S3)
- Container Registry
- CDN
- Monitoring
- Logging
- Backup

### 📋 Services We Can Skip (80+)
- UI/Admin services
- Documentation
- Support
- One-time tools
- Free services

## Next Steps

1. **Implement pricing for 4 known services** (VMs, K8s, LB, DB)
2. **Request HAR files** for high-priority missing services (S3, Registry, CDN)
3. **Analyze new HAR files** when available
4. **Implement pricing** for additional services
5. **Skip** low-priority/free services

## Summary

- **How we know services**: From HAR file analysis (98 products discovered)
- **Do we need endpoints for all?**: No, only for services with costs
- **How to get endpoints**: HAR file analysis (most reliable method)
- **Current status**: 4 services have endpoints, 6+ need endpoints, 80+ can skip

