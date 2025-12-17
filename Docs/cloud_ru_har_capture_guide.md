# Cloud.ru HAR File Capture Guide

## Instructions

1. **Open Browser DevTools** → Network tab
2. **Clear network log** (trash icon)
3. **Navigate to the page** listed below
4. **Perform the action** (create, view pricing, configure)
5. **Save HAR file** → Export as `{service_name}.har` in `Docs/har/` folder

## Priority: High (Services with Significant Costs)

### 📦 Хранение данных (Data Storage)

#### 1. **S3 Object Storage** ✅ (You're already here!)
- **Menu Path**: `Хранение данных` → `S3 Storage` (or `Object Storage`)
- **Action**: 
  - Click "Create Bucket" or "Создать бакет"
  - Fill out the form (try different configurations)
  - Look for pricing information on the page
- **HAR File**: `s3_storage.har`
- **What to capture**: Bucket creation, pricing calculation, storage tiers

#### 2. **Container Registry** (Artifact Registry)
- **Menu Path**: `Инструменты разработчика` → `Artifact Registry` (or `Container Registry`)
- **Action**:
  - Click "Create Registry" or "Создать реестр"
  - Configure registry settings
  - View pricing if available
- **HAR File**: `artifact_registry.har`
- **What to capture**: Registry creation, storage pricing, bandwidth pricing

### 🌐 Сеть (Network)

#### 3. **CDN**
- **Menu Path**: `Сеть` → `CDN`
- **Action**:
  - Click "Create CDN" or "Создать CDN"
  - Configure CDN settings
  - View pricing (bandwidth, requests)
- **HAR File**: `cdn.har`
- **What to capture**: CDN creation, bandwidth pricing, request pricing

### 📊 Мониторинг (Monitoring)

#### 4. **Cloud Monitoring** (MONAAS)
- **Menu Path**: `Мониторинг` → `Cloud Monitoring` (or just `Мониторинг`)
- **Action**:
  - Create monitoring dashboard or service
  - View pricing/quotas
  - Configure metrics/alerts
- **HAR File**: `monitoring.har`
- **What to capture**: Service creation, pricing, quota limits

#### 5. **Logging** (Logging as a Service)
- **Menu Path**: `Мониторинг` → `Logging` (or `Логирование`)
- **Action**:
  - Create logging service
  - View pricing (storage per GB, ingestion)
  - Configure log retention
- **HAR File**: `logging.har`
- **What to capture**: Service creation, storage pricing, ingestion pricing

### 💾 Инфраструктура (Infrastructure)

#### 6. **Backup** (Agent Backup)
- **Menu Path**: `Инфраструктура` → `Agent Backup` (or `Резервное копирование`)
- **Action**:
  - Create backup service
  - Configure backup settings
  - View pricing (storage per GB)
- **HAR File**: `backup.har`
- **What to capture**: Service creation, storage pricing, retention pricing

## Priority: Medium (May Use Existing Endpoints)

### 🗄️ Базы данных (Databases)

#### 7. **Redis** (Managed Redis)
- **Menu Path**: `Базы данных` → `Redis` (or `Managed Redis`)
- **Action**:
  - Create Redis instance
  - Configure (CPU, RAM, storage)
  - View pricing
- **HAR File**: `redis.har`
- **Note**: May use same pricing endpoint as PostgreSQL (`/u-api/paas-bff/api/v1/price-calculator/sku-list`)

#### 8. **Kafka** (Managed Kafka)
- **Menu Path**: `Брокеры сообщений` → `Kafka` (or `Managed Kafka`)
- **Action**:
  - Create Kafka cluster
  - Configure (brokers, storage)
  - View pricing
- **HAR File**: `kafka.har`
- **Note**: May use same pricing endpoint as PostgreSQL

### 🐳 Контейнеры (Containers)

#### 9. **Container Apps** (Serverless Containers)
- **Menu Path**: `Контейнеры` → `Container Apps` (or `Serverless Containers`)
- **Action**:
  - Create container app
  - Configure (CPU, RAM, instances)
  - View pricing
- **HAR File**: `container_apps.har`
- **Note**: May use VM pricing or have separate endpoint

## Priority: Low (Optional - May Be Free/Low Cost)

### 🔧 Инструменты разработчика (Developer Tools)

#### 10. **Git Repository** (Git as a Service)
- **Menu Path**: `Инструменты разработчика` → `Git Repository` (or `Evolution Repo`)
- **Action**: Create repository, view pricing
- **HAR File**: `git_repository.har` (optional)

### 📊 Платформа данных (Data Platform)

#### 11. **Managed Spark**
- **Menu Path**: `Платформа данных` → `Spark` (or `Managed Spark`)
- **Action**: Create Spark cluster, view pricing
- **HAR File**: `spark.har` (optional)

## Already Have (No Need to Capture)

✅ **VMs/Compute** - Already have from `console.cloud.ru.har`
✅ **Kubernetes** - Already have from `console.cloud.ru.har`
✅ **Load Balancers** - Already have from `load_balancers.har`
✅ **PostgreSQL** - Already have from `db.har`

## Step-by-Step Process

### For Each Service:

1. **Open DevTools**:
   - Press `F12` or `Cmd+Option+I` (Mac) / `Ctrl+Shift+I` (Windows/Linux)
   - Go to **Network** tab
   - Click **Clear** (trash icon) to start fresh

2. **Navigate to Service**:
   - Use the menu path provided above
   - Click on the service name

3. **Perform Action**:
   - Click "Create" or "Создать" button
   - Fill out the creation form
   - Try different configurations (sizes, regions, etc.)
   - Look for pricing information displayed on the page
   - **Don't actually create** - just fill the form and check pricing

4. **Save HAR File**:
   - In DevTools Network tab, click **Export HAR** (or right-click → Save all as HAR)
   - Save as: `{service_name}.har` in `Docs/har/` folder
   - Example: `s3_storage.har`, `cdn.har`, etc.

5. **Verify**:
   - Check that HAR file contains API calls to `/u-api/` endpoints
   - Look for calls with "price", "pricing", "calculate" in the URL

## What We're Looking For

In each HAR file, we need to find:

1. **Pricing Endpoints**:
   - URLs containing: `price`, `pricing`, `calculate-price`, `billing`
   - Usually POST or GET requests to `/u-api/...`

2. **Configuration Endpoints**:
   - URLs containing: `flavor`, `config`, `product`, `sku`
   - These help us understand what parameters pricing needs

3. **Request/Response Examples**:
   - Request body (JSON) showing what parameters are needed
   - Response body (JSON) showing pricing structure

## Quick Reference: Menu Structure

```
Cloud.ru Console
├── Инфраструктура (Infrastructure)
│   ├── Виртуальные машины ✅ (have)
│   ├── Agent Backup 🔴 (need)
│   └── ...
├── Сеть (Network)
│   ├── Load Balancer ✅ (have)
│   ├── CDN 🔴 (need)
│   └── ...
├── Хранение данных (Data Storage)
│   ├── S3 Storage 🔴 (need - you're here!)
│   └── ...
├── Контейнеры (Containers)
│   ├── Kubernetes ✅ (have)
│   ├── Container Apps 🟡 (optional)
│   └── ...
├── Базы данных (Databases)
│   ├── PostgreSQL ✅ (have)
│   ├── Redis 🟡 (optional - may use same endpoint)
│   └── ...
├── Инструменты разработчика (Developer Tools)
│   ├── Artifact Registry 🔴 (need)
│   └── ...
└── Мониторинг (Monitoring)
    ├── Cloud Monitoring 🔴 (need)
    └── Logging 🔴 (need)
```

## Status Legend

- ✅ **Have** - Already captured, no need to capture again
- 🔴 **Need** - High priority, please capture
- 🟡 **Optional** - Medium priority, capture if easy
- ⚪ **Skip** - Low priority or free service

## Next Steps

1. **Start with S3 Storage** (you're already there!)
2. **Then do**: Container Registry, CDN, Monitoring, Logging, Backup
3. **Save each HAR file** with the name specified
4. **Let me know when done** - I'll analyze them!

