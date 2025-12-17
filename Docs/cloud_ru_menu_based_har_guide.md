# Cloud.ru HAR Capture Guide - Based on Your Menu

## Priority Services to Capture (Based on Visible Menu)

### ✅ Already Have (Skip These)
- ✅ Виртуальные машины (Virtual Machines) - Have pricing
- ✅ Load Balancer - Have pricing  
- ✅ Managed Kubernetes - Have pricing
- ✅ Managed PostgreSQL® - Have pricing
- ✅ Artifact Registry - Have pricing
- ✅ Object Storage (S3) - Analyzed (no pricing endpoint, usage-based)

---

## 🔴 HIGH PRIORITY - Services with Costs

### 1. **Agent Backup** (Резервное копирование)
- **Location**: `Инфраструктура` → `Agent Backup`
- **Action**: 
  - Click on "Agent Backup"
  - Create backup service or view configuration
  - Look for pricing information
- **HAR File**: `agent_backup.har`
- **Why**: Backup services typically have storage costs

### 2. **Managed Redis®**
- **Location**: `Базы данных` → `Managed Redis®`
- **Action**:
  - Click on "Managed Redis®"
  - Create Redis instance
  - Configure (CPU, RAM, storage)
  - View pricing
- **HAR File**: `redis.har`
- **Why**: Database service, likely uses same pricing endpoint as PostgreSQL, but need to verify

### 3. **Container Apps**
- **Location**: `Контейнеры` → `Container Apps`
- **Action**:
  - Click on "Container Apps"
  - Create container app
  - Configure (CPU, RAM, instances)
  - View pricing
- **HAR File**: `container_apps.har`
- **Why**: Serverless containers may have separate pricing

---

## 🟡 MEDIUM PRIORITY - May Have Pricing

### 4. **Managed Kafka®** (Preview)
- **Location**: `Брокеры сообщений` → `Managed Kafka®`
- **Action**: Create Kafka cluster, view pricing
- **HAR File**: `kafka.har`
- **Note**: May use same pricing endpoint as PostgreSQL

### 5. **Managed Spark**
- **Location**: `Платформа данных` → `Managed Spark`
- **Action**: Create Spark cluster, view pricing
- **HAR File**: `spark.har`

### 6. **ML Inference**
- **Location**: `AI Factory` → `ML Inference`
- **Action**: Create inference service, view pricing
- **HAR File**: `ml_inference.har`

---

## ⚪ LOW PRIORITY - Likely Free/Included

These services are likely free or included, but capture if you see pricing:

- **DNS** (`Сеть` → `DNS`)
- **Key Management** (`Управление` → `Key Management`)
- **Secret Management** (`Управление` → `Secret Management`)
- **Repo** (`Инструменты разработчика` → `Repo`)
- **Notebooks** (`AI Factory` → `Notebooks`)

---

## 📋 Step-by-Step Instructions

### For Each Service:

1. **Open DevTools**:
   - Press `F12` or `Cmd+Option+I` (Mac) / `Ctrl+Shift+I` (Windows)
   - Go to **Network** tab
   - Click **Clear** (trash icon)

2. **Navigate to Service**:
   - Click on the service name from the menu

3. **Perform Action**:
   - Click "Create" or "Создать" button
   - Fill out the creation form (don't submit)
   - Try different configurations
   - Look for pricing information on the page

4. **Export HAR**:
   - In Network tab, click **Export HAR** (or right-click → Save all as HAR)
   - Save as: `{service_name}.har` in `Docs/har/` folder

---

## Recommended Order

**Start with these 3 (High Priority):**

1. **Agent Backup** ← Start here!
   - `Инфраструктура` → `Agent Backup`
   - HAR: `agent_backup.har`

2. **Managed Redis®**
   - `Базы данных` → `Managed Redis®`
   - HAR: `redis.har`

3. **Container Apps**
   - `Контейнеры` → `Container Apps`
   - HAR: `container_apps.har`

---

## What We're Looking For

In each HAR file, search for:
- URLs containing: `price`, `pricing`, `calculate-price`, `billing`, `tariff`
- Endpoints like: `/u-api/{service}/v*/price*` or `/u-api/{service}/v*/billing/*`
- Request/response showing pricing structure

---

## Services Not Visible (May Need Different Access)

These services from our list aren't visible in your menu:
- **CDN** - May not be available in your project
- **Cloud Monitoring** (Мониторинг) - Check bottom sidebar
- **Logging** (Логирование) - Check bottom sidebar

If you scroll down or check the bottom of the left sidebar, you might see:
- `Мониторинг` (Monitoring)
- `Контроль затрат` (Cost Control)
- `Администрирование` (Administration)

These sections might contain Monitoring and Logging services.

