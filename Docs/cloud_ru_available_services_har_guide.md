# Cloud.ru HAR Capture Guide - Based on Available Services

## ✅ Services Already Captured
- ✅ VMs/Compute
- ✅ Kubernetes
- ✅ Load Balancers
- ✅ PostgreSQL
- ✅ Redis
- ✅ Container Registry
- ✅ S3 Object Storage
- ✅ Container Apps

## 🔴 Available Services to Capture (From Your Menu)

### High Priority - Likely Have Pricing

#### 1. **Managed Kafka®** (Preview)
- **Location**: `Брокеры сообщений` → `Managed Kafka®`
- **Action**: 
  - Click on "Managed Kafka®"
  - Create Kafka cluster
  - Configure (brokers, storage)
  - View pricing
- **HAR File**: `kafka.har`
- **Why**: Database/messaging service, likely uses same pricing endpoint as PostgreSQL/Redis
- **Expected**: Same endpoint as databases (`/u-api/paas-bff/api/v1/price-calculator/sku-list`) with `paas_kafka.*` SKU codes

#### 2. **Managed Spark**
- **Location**: `Платформа данных` → `Managed Spark`
- **Action**:
  - Click on "Managed Spark"
  - Create Spark cluster
  - Configure (workers, storage)
  - View pricing
- **HAR File**: `spark.har`
- **Why**: Data platform service, may have pricing

#### 3. **Managed Trino**
- **Location**: `Платформа данных` → `Managed Trino`
- **Action**: Create Trino cluster, view pricing
- **HAR File**: `trino.har`

#### 4. **ML Inference**
- **Location**: `AI Factory` → `ML Inference`
- **Action**: Create inference service, view pricing
- **HAR File**: `ml_inference.har`

### Medium Priority - May Have Pricing

#### 5. **Managed Airflow** (Preview)
- **Location**: `Платформа данных` → `Managed Airflow`
- **Action**: Create Airflow instance, view pricing
- **HAR File**: `airflow.har`

#### 6. **Managed Metastore**
- **Location**: `Платформа данных` → `Managed Metastore`
- **Action**: Create Metastore, view pricing
- **HAR File**: `metastore.har`

#### 7. **Managed ArenadataDB**
- **Location**: `Платформа данных` → `Managed ArenadataDB`
- **Action**: Create ArenadataDB, view pricing
- **HAR File**: `arenadatadb.har`

#### 8. **Managed BI**
- **Location**: `Платформа данных` → `Managed BI`
- **Action**: Create BI service, view pricing
- **HAR File**: `managed_bi.har`

#### 9. **Foundation Models**
- **Location**: `AI Factory` → `Foundation Models`
- **Action**: View/create model, check pricing
- **HAR File**: `foundation_models.har`

#### 10. **Notebooks**
- **Location**: `AI Factory` → `Notebooks`
- **Action**: Create notebook, view pricing
- **HAR File**: `notebooks.har`

### Low Priority - Likely Free/Low Cost

#### 11. **DNS**
- **Location**: `Сеть` → `DNS`
- **Action**: Create DNS zone, check pricing
- **HAR File**: `dns.har` (optional)

#### 12. **Key Management**
- **Location**: `Управление` → `Key Management`
- **Action**: Create key, check pricing
- **HAR File**: `key_management.har` (optional)

#### 13. **Secret Management**
- **Location**: `Управление` → `Secret Management`
- **Action**: Create secret, check pricing
- **HAR File**: `secret_management.har` (optional)

#### 14. **Repo** (Git Repository)
- **Location**: `Инструменты разработчика` → `Repo`
- **Action**: Create repository, check pricing
- **HAR File**: `repo.har` (optional)

---

## 📋 Recommended Order

**Start with these (High Priority):**

1. **Managed Kafka®** ← Start here!
   - `Брокеры сообщений` → `Managed Kafka®`
   - HAR: `kafka.har`
   - **Why**: Very likely uses same pricing endpoint as PostgreSQL/Redis

2. **Managed Spark**
   - `Платформа данных` → `Managed Spark`
   - HAR: `spark.har`

3. **ML Inference**
   - `AI Factory` → `ML Inference`
   - HAR: `ml_inference.har`

---

## Step-by-Step Instructions

For each service:

1. **Open DevTools** → Network tab → Clear log
2. **Click the service name** from menu
3. **Click "Create"** or "Создать"
4. **Fill the form** (don't submit)
5. **Check for pricing** on the page
6. **Export HAR** → Save as `{service_name}.har` in `Docs/har/`

---

## What We're Looking For

In each HAR file:
- URLs with: `price`, `pricing`, `calculate-price`, `billing`, `tariff`
- Endpoints like: `/u-api/{service}/v*/price*` or `/u-api/{service}/v*/billing/*`

---

## Services Not Available (Skip These)

- ❌ Agent Backup - Not in your menu
- ❌ Monitoring - Not in your menu
- ❌ Logging - Not in your menu
- ❌ CDN - Not in your menu

These services might:
- Require different project/account permissions
- Be in a different region
- Not be available in your subscription tier
- Be accessed via different menu paths

---

## Summary

**Available to capture**: ~14 services from your menu
**Priority**: Start with Kafka, Spark, ML Inference
**Already have**: 8 services captured

