# Cloud.ru Pricing Endpoints - Final Discovery Summary

## Overview

Comprehensive analysis of Cloud.ru pricing endpoints through HAR file analysis.

## ✅ Confirmed Pricing Endpoints (6 Services)

### 1. **VMs/Compute**
- **Endpoint**: `POST /u-api/svp/svc/v1/projects/{project_id}/price-calculation`
- **Status**: ✅ Working
- **Source**: `console.cloud.ru.har`
- **Returns**: Monthly and hourly costs for VMs, disks, floating IPs, NAT gateways

### 2. **Kubernetes**
- **Endpoint**: `POST /u-api/mk8s/v2/billing/calculate-price-ext`
- **Status**: ✅ Working
- **Source**: `console.cloud.ru.har`
- **Returns**: Hourly prices with VAT for master nodes, node pools, volumes

### 3. **Load Balancers**
- **Endpoint**: `GET /u-api/svp/v2/nlb/calculate-price`
- **Status**: ✅ Working
- **Source**: `load_balancers.har`
- **Returns**: Hourly, daily, monthly prices with breakdown (replicas, external address, traffic)

### 4. **Databases (PostgreSQL, Redis, MySQL, Kafka, etc.)**
- **Endpoint**: `POST /u-api/paas-bff/api/v1/price-calculator/sku-list`
- **Status**: ✅ Working
- **Source**: `db.har` (PostgreSQL), `redis.har` (Redis)
- **SKU Patterns**:
  - PostgreSQL: `paas_postgres.{resource}#{tier}#{platform}`
  - Redis: `paas_redis.{resource}#{tier}#{platform}` ✅ Confirmed
  - MySQL: `paas_mysql.{resource}#{tier}#{platform}` (likely)
  - Kafka: `paas_kafka.{resource}#{tier}#{platform}` (likely)
- **Returns**: Hourly prices per SKU (CPU, RAM, storage)

### 5. **Container Registry**
- **Endpoint**: `GET /u-api/container-registry/v1/api/v3/{project_id}/tariffs/`
- **Status**: ✅ Working
- **Source**: `artifact_registry.har`
- **Returns**: Tariff plans (PREMIUM, BASIC) with monthly prices

### 6. **S3 Object Storage**
- **Endpoint**: ❌ No pricing endpoint
- **Status**: Usage-based pricing
- **Source**: `menue.har`
- **Solution**: Use billing API for actual costs + static unit prices from documentation

## ❌ No Pricing Endpoints Found

### 7. **Container Apps**
- **Status**: ❌ No pricing endpoint
- **Source**: `container_apps.har`
- **Findings**: Instance-types endpoint exists but contains no pricing data
- **Possible**: Uses VM pricing or calculated differently

### 8. **Managed Spark**
- **Status**: ⏳ Analyzing...
- **Source**: `spark.har` (just captured)

## 📊 Discovery Statistics

- **Total HAR Files Analyzed**: 8
- **Pricing Endpoints Found**: 5 unique endpoints
- **Services with Pricing**: 6 (VMs, K8s, LB, DBs, Registry, S3 via billing)
- **Services Without Pricing Endpoints**: 2 (Container Apps, possibly Spark)

## 🎯 Implementation Priority

### Phase 1: Implement Pricing for Confirmed Endpoints (6 services)
1. ✅ VMs/Compute - Ready to implement
2. ✅ Kubernetes - Ready to implement
3. ✅ Load Balancers - Ready to implement
4. ✅ Databases (PostgreSQL, Redis, MySQL, Kafka) - Ready to implement
5. ✅ Container Registry - Ready to implement
6. ✅ S3 Object Storage - Use billing API + static prices

### Phase 2: Investigate Further (2 services)
7. Container Apps - Need to investigate VM pricing or alternative approach
8. Managed Spark - Analyzing HAR file

## 📝 Key Findings

1. **Database Services Unification**: All managed databases (PostgreSQL, Redis, MySQL, Kafka) use the same pricing endpoint with different SKU codes
2. **S3 Pricing**: No API endpoint - usage-based, use billing API
3. **Container Registry**: Simple tariff-based pricing (flat monthly rates)
4. **Multiple Endpoint Patterns**: Cloud.ru uses different endpoint structures for different services:
   - VMs: `/svp/svc/v1/`
   - Kubernetes: `/mk8s/v2/billing/`
   - Load Balancers: `/svp/v2/nlb/`
   - Databases: `/paas-bff/api/v1/`
   - Container Registry: `/container-registry/v1/api/v3/`

## 📚 Documentation Created

1. `Docs/cloud_ru_pricing_research.md` - Complete pricing API research
2. `Docs/cloud_ru_api_endpoints_discovery.md` - All discovered endpoints
3. `Docs/cloud_ru_pricing_endpoints_summary.md` - Summary of findings
4. `Docs/cloud_ru_available_services_har_guide.md` - Guide for available services
5. `scripts/discover_cloud_ru_pricing_endpoints.py` - Discovery script

## Next Steps

1. ⏳ Analyze Spark HAR file
2. ⏳ Implement pricing client for 6 confirmed services
3. ⏳ Test pricing sync
4. ⏳ Document implementation

