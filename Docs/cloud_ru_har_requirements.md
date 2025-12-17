# Cloud.ru HAR Files Requirements

## Overview

This document lists all Cloud.ru services that need HAR files to implement complete pricing support. Based on the codebase analysis, Cloud.ru supports multiple resource types that we need to price.

## ✅ Already Covered (Have HAR Files)

1. **VMs/Compute** ✅
   - HAR: `console.cloud.ru.har` (VM creation)
   - Endpoint: `POST /u-api/svp/svc/v1/projects/{project_id}/price-calculation`
   - Status: Implemented

2. **Kubernetes** ✅
   - HAR: `console.cloud.ru.har` (Kubernetes cluster creation)
   - Endpoint: `POST /u-api/mk8s/v2/billing/calculate-price-ext`
   - Status: Found endpoint, needs implementation

3. **Disks/Volumes** ✅
   - HAR: `console.cloud.ru.har` (VM creation includes disk pricing)
   - Endpoint: `POST /u-api/svp/svc/v1/projects/{project_id}/price-calculation` (disks component)
   - Status: Can be extracted from VM pricing endpoint

4. **Floating IPs / NAT Gateways** ✅
   - HAR: `console.cloud.ru.har` (VM creation includes network pricing)
   - Endpoint: `POST /u-api/svp/svc/v1/projects/{project_id}/price-calculation` (floating_ips, nat_gateways components)
   - Status: Can be extracted from VM pricing endpoint

## ✅ Services Found via Product Discovery

From the `/u-api/bff-console/v1/project/{project_id}/aggregated-available-products` endpoint, we discovered **98 products**. Key services that need pricing:

- **S3E** - Evolution Object Storage (S3)
- **ARTIFACT_REGISTRY** - Evolution Artifact Registry (Container Registry)
- **AGENT_BACKUP** - Evolution Agent Backup
- **MONAAS** - Cloud Monitoring
- **LOGGING_AS_A_SERVICE** - Logging
- **CDN** - CDN
- **SERVERLESS_CONTAINER** - Evolution Container Apps

## ❌ Missing HAR Files (Need to Collect)

### 1. **Managed Databases** 🔴 HIGH PRIORITY
   - **Services**: PostgreSQL, MySQL, Redis, MongoDB, Kafka
   - **What to capture**: Creating a new database instance (any type)
   - **What we need**:
     - Database creation form/page
     - Pricing calculation endpoint
     - Available database flavors/configurations
     - Pricing response structure
   - **Expected endpoints**:
     - `POST /u-api/dbaas/v*/billing/calculate-price` or similar
     - `GET /u-api/dbaas/v*/flavors` or similar
   - **Why important**: Databases are commonly used and have significant costs

### 2. **Load Balancers** 🔴 HIGH PRIORITY
   - **What to capture**: Creating a new load balancer
   - **What we need**:
     - Load balancer creation form/page
     - Pricing calculation endpoint
     - Available load balancer types/configurations
     - Pricing response structure
   - **Expected endpoints**:
     - `POST /u-api/lb/v*/billing/calculate-price` or similar
     - `GET /u-api/lb/v*/types` or similar
   - **Why important**: Load balancers are essential for production workloads

### 3. **Object Storage (S3)** 🔴 HIGH PRIORITY
   - **What to capture**: Creating a new S3 bucket or viewing pricing
   - **What we need**:
     - S3 bucket creation page
     - Storage pricing endpoint (per GB pricing)
     - Request pricing endpoint (per request pricing)
     - Pricing tiers/regions
   - **Expected endpoints**:
     - `GET /u-api/s3/v*/pricing` or similar
     - `GET /u-api/storage/v*/pricing` or similar
   - **Why important**: Object storage is widely used and pricing is typically per GB + requests

### 4. **Container Registry** 🟡 MEDIUM PRIORITY
   - **What to capture**: Creating a new container registry or viewing pricing
   - **What we need**:
     - Registry creation page
     - Storage pricing (per GB)
     - Bandwidth pricing
   - **Expected endpoints**:
     - `GET /u-api/registry/v*/pricing` or similar
   - **Why important**: Used for Kubernetes deployments

### 5. **Backup Services** 🟡 MEDIUM PRIORITY
   - **What to capture**: Setting up backup service or viewing pricing
   - **What we need**:
     - Backup configuration page
     - Storage pricing (per GB)
     - Retention pricing
   - **Expected endpoints**:
     - `GET /u-api/backup/v*/pricing` or similar

### 6. **Monitoring/Logging Services** 🟢 LOW PRIORITY
   - **What to capture**: Setting up monitoring/logging or viewing pricing
   - **What we need**:
     - Monitoring setup page
     - Log storage pricing (per GB)
     - Metrics pricing
   - **Expected endpoints**:
     - `GET /u-api/monitoring/v*/pricing` or similar

### 7. **CDN** 🟢 LOW PRIORITY
   - **What to capture**: Setting up CDN or viewing pricing
   - **What we need**:
     - CDN configuration page
     - Bandwidth pricing (per GB)
     - Request pricing
   - **Expected endpoints**:
     - `GET /u-api/cdn/v*/pricing` or similar

## How to Capture HAR Files

### Steps for Each Service:

1. **Open Cloud.ru Console** → Navigate to the service creation page
2. **Open Browser DevTools** → Network tab
3. **Clear network log** → Start fresh
4. **Fill out creation form** → Select different configurations/flavors
5. **Watch for pricing API calls** → Look for:
   - `calculate-price` endpoints
   - `pricing` endpoints
   - `flavors` or `configurations` endpoints
6. **Save HAR file** → Export as `console.cloud.ru.{service_name}.har`
   - Example: `console.cloud.ru.database.har`
   - Example: `console.cloud.ru.loadbalancer.har`

### What to Look For:

- **POST requests** with `calculate-price` or `pricing` in URL
- **GET requests** with `flavors`, `configurations`, or `pricing` in URL
- **Request bodies** that include:
  - Resource type (database type, load balancer type, etc.)
  - Configuration (CPU, RAM, storage size, etc.)
  - Region/zone
- **Response bodies** that include:
  - Hourly/monthly costs
  - Price breakdown by component
  - Resource specifications

## Priority Order

Based on usage and cost impact:

1. **Databases** (PostgreSQL, MySQL, Redis) - Most commonly used, significant costs
2. **Load Balancers** - Essential for production, moderate costs
3. **Object Storage (S3)** - Widely used, storage costs can be high
4. **Container Registry** - Used with Kubernetes
5. **Backup Services** - Important for production
6. **Monitoring/Logging** - Lower priority, typically lower costs
7. **CDN** - Lower priority, usage-dependent

## Current Resource Type Mapping

From `app/providers/plugins/cloud_ru.py`, we already map these types:
- ✅ `server` (VMs, Bare Metal) - Pricing found
- ✅ `volume` (Disks) - Pricing found
- ✅ `network` (IPs) - Pricing found
- ❌ `database` - **NEEDS HAR**
- ✅ `kubernetes` - Pricing found
- ❌ `load_balancer` - **NEEDS HAR**
- ❌ `s3` - **NEEDS HAR**

## Next Steps

1. User provides HAR files for each service (starting with databases)
2. Analyze each HAR file to find pricing endpoints
3. Document endpoints in `cloud_ru_pricing_research.md`
4. Implement pricing client methods for each service
5. Test pricing sync for each service

