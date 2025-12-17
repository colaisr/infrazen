# Cloud.ru Pricing Endpoints Summary

## ✅ Confirmed Pricing Endpoints

### 1. **VMs/Compute**
- **Endpoint**: `POST /u-api/svp/svc/v1/projects/{project_id}/price-calculation`
- **Status**: ✅ Working
- **Source**: `console.cloud.ru.har`

### 2. **Kubernetes**
- **Endpoint**: `POST /u-api/mk8s/v2/billing/calculate-price-ext`
- **Status**: ✅ Working
- **Source**: `console.cloud.ru.har`

### 3. **Load Balancers**
- **Endpoint**: `GET /u-api/svp/v2/nlb/calculate-price`
- **Status**: ✅ Working
- **Source**: `load_balancers.har`

### 4. **Databases (PostgreSQL, Redis, MySQL, Kafka, etc.)**
- **Endpoint**: `POST /u-api/paas-bff/api/v1/price-calculator/sku-list`
- **Status**: ✅ Working
- **Source**: `db.har` (PostgreSQL), `redis.har` (Redis)
- **Note**: All managed databases use the same endpoint with different SKU codes:
  - PostgreSQL: `paas_postgres.{resource}#{tier}#{platform}`
  - Redis: `paas_redis.{resource}#{tier}#{platform}`
  - MySQL: `paas_mysql.{resource}#{tier}#{platform}` (likely)
  - Kafka: `paas_kafka.{resource}#{tier}#{platform}` (likely)

### 5. **Container Registry**
- **Endpoint**: `GET /u-api/container-registry/v1/api/v3/{project_id}/tariffs/`
- **Status**: ✅ Working
- **Source**: `artifact_registry.har`
- **Response**: Returns tariff plans (PREMIUM, BASIC) with monthly prices

## ❌ No Pricing Endpoints Found

### 6. **S3 Object Storage**
- **Status**: ❌ No pricing endpoint
- **Source**: `menue.har` (S3 page)
- **Reason**: Usage-based pricing (storage, traffic, operations)
- **Solution**: Use billing API for actual costs + static unit prices from documentation

### 7. **Container Apps**
- **Status**: ❌ No pricing endpoint
- **Source**: `container_apps.har`
- **Findings**: 
  - Found instance-types endpoint: `GET /u-api/serverless/v1/api/{instance_id}/serverless/instance-types/v1/`
  - Returns instance configurations (CPU, RAM) but **no pricing**
- **Possible Solutions**:
  1. May use VM pricing endpoint with container-specific flavors
  2. Pricing might be calculated client-side
  3. Need to check billing API for actual costs

## 📊 Current Status

| Service | Pricing Endpoint | Status | HAR File |
|---------|-----------------|--------|----------|
| VMs/Compute | ✅ Found | Working | `console.cloud.ru.har` |
| Kubernetes | ✅ Found | Working | `console.cloud.ru.har` |
| Load Balancers | ✅ Found | Working | `load_balancers.har` |
| Databases (PostgreSQL) | ✅ Found | Working | `db.har` |
| Databases (Redis) | ✅ Found | Working | `redis.har` |
| Container Registry | ✅ Found | Working | `artifact_registry.har` |
| S3 Object Storage | ❌ Not found | Usage-based | `menue.har` |
| Container Apps | ❌ Not found | Unknown | `container_apps.har` |
| Managed Spark | ⚠️ Endpoint exists (400 error) | Under investigation | `spark.har` |

## 🎯 Next Services to Explore

Based on your available menu, these services need HAR files:

### High Priority (Likely Have Pricing)

1. **Managed Kafka®** (`Брокеры сообщений` → `Managed Kafka®`)
   - HAR: `kafka.har`
   - Priority: High
   - **Expected**: Uses same endpoint as PostgreSQL/Redis with `paas_kafka.*` SKU codes

2. **Managed Spark** (`Платформа данных` → `Managed Spark`)
   - HAR: `spark.har`
   - Priority: High
   - **Why**: Data platform service, commonly used

3. **ML Inference** (`AI Factory` → `ML Inference`)
   - HAR: `ml_inference.har`
   - Priority: High
   - **Why**: AI services often have significant costs

### Medium Priority

4. **Managed Trino** (`Платформа данных` → `Managed Trino`)
   - HAR: `trino.har`

5. **Managed Airflow** (`Платформа данных` → `Managed Airflow`)
   - HAR: `airflow.har`

6. **Managed Metastore** (`Платформа данных` → `Managed Metastore`)
   - HAR: `metastore.har`

7. **Managed BI** (`Платформа данных` → `Managed BI`)
   - HAR: `managed_bi.har`

8. **Foundation Models** (`AI Factory` → `Foundation Models`)
   - HAR: `foundation_models.har`

### Not Available in Your Menu (Skip)
- ❌ Agent Backup
- ❌ Monitoring
- ❌ Logging
- ❌ CDN

## 📝 Key Findings

1. **Database Services**: All use the same pricing endpoint (`/u-api/paas-bff/api/v1/price-calculator/sku-list`) with different SKU codes
2. **S3**: No pricing endpoint - usage-based, use billing API
3. **Container Apps**: No pricing endpoint found - may use VM pricing or separate endpoint
4. **Container Registry**: Simple tariff-based pricing (PREMIUM/BASIC plans)

## Implementation Priority

### Phase 1: Services with Pricing Endpoints (6 services)
1. ✅ VMs/Compute
2. ✅ Kubernetes
3. ✅ Load Balancers
4. ✅ Databases (PostgreSQL, Redis, MySQL, Kafka)
5. ✅ Container Registry

### Phase 2: Services Needing Alternative Approach (2 services)
6. S3 Object Storage (use billing API + static prices)
7. Container Apps (investigate further or use VM pricing)

### Phase 3: Remaining Services (Need HAR files)
8. Agent Backup
9. Monitoring
10. Logging
11. Kafka (verify uses same endpoint)
12. Spark
13. ML Inference

