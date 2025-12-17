# Cloud.ru Provider Implementation Plan

This document outlines the step-by-step plan for adding Cloud.ru provider support to InfraZen, organized into three phases as requested.

## Overview

**Provider Name**: Cloud.ru (Облако.ру)  
**Provider Type**: `cloud-ru`  
**Implementation Approach**: Plugin-based architecture following existing patterns (Beget, Selectel, Yandex)

## Progress Tracking

### Phase 1: Connection Dialogs and Guide
- [x] Step 1.1: Research Cloud.ru API Requirements - ✅ COMPLETED - Created research doc with authentication flow, API endpoints, billing API integration
- [x] Step 1.2: Add Cloud.ru to Provider Configuration (Frontend) - ✅ COMPLETED - Added to connections.js, removed account_id field
- [x] Step 1.3: Create Cloud.ru API Routes (Backend) - ✅ COMPLETED - Created routes.py with all CRUD operations, test, add, edit, update, sync, delete
- [x] Step 1.4: Create Cloud.ru API Client (Basic) - ✅ COMPLETED - Created client with token-based auth, project_id extraction from JWT, billing API integration
- [x] Step 1.5: Create Connection Instructions Page - ✅ COMPLETED - Created cloud_ru.html with step-by-step guide, all 8 screenshots integrated, route added to main.py
- [x] Step 1.6: Add Cloud.ru to Provider Catalog - ✅ COMPLETED - Added to database and template with icon

### Phase 2: Proper Syncing
- [x] Step 2.1: Create Cloud.ru Provider Plugin - ✅ COMPLETED - Plugin created with all required methods, billing-first sync
- [x] Step 2.2: Extend Cloud.ru API Client for Resource Discovery - ✅ COMPLETED - VM discovery working, billing API integration, hardware specs extraction
- [x] Step 2.3: Implement Resource Sync Logic - ✅ COMPLETED - Billing-first sync implemented with resource unification (volumes/IPs with VMs)
- [x] Step 2.4: Create Cloud.ru Service Layer - ✅ NOT NEEDED - Using plugin directly via orchestrator
- [x] Step 2.5: Update Sync Route to Use Plugin System - ✅ COMPLETED - Uses sync_orchestrator
- [x] Step 2.6: Register Resource Mappings - ✅ COMPLETED - Registered server, volume, network types in database

**Additional Implementations:**
- [x] Billing-first resource discovery - ✅ COMPLETED - All resources discovered from consumption API
- [x] Resource type mapping (SKU-based) - ✅ COMPLETED - Maps servname/SKU to unified types
- [x] Resource unification - ✅ COMPLETED - Volumes and IPs aggregated under parent VMs
- [x] Hardware specs extraction - ✅ COMPLETED - CPU, RAM, disk from VM flavor data
- [x] Cost extraction from billing API - ✅ COMPLETED - Daily/monthly costs from consumption records
- [x] Project ID auto-extraction - ✅ COMPLETED - Extracted from JWT token, no hardcoded values

### Phase 3: Price Updating
- [ ] Step 3.1: Research Cloud.ru Pricing API - 🔄 PENDING (Optional)
- [ ] Step 3.2: Create Cloud.ru Pricing Client - 🔄 PENDING (Optional)
- [ ] Step 3.3: Implement get_pricing_data() in Plugin - 🔄 PENDING (Optional)
- [ ] Step 3.4: Create Pricing Sync Script - 🔄 PENDING (Optional)
- [ ] Step 3.5: Test Price Update Service Integration - 🔄 PENDING (Optional)
- [ ] Step 3.6: Add Pricing to Provider Catalog - 🔄 PENDING (Optional)

**Current Status**: Phase 1 and Phase 2 COMPLETED! ✅
- ✅ Connection testing and adding working
- ✅ VM discovery working - billing-first approach discovers all resources
- ✅ Resources being saved to database with correct types
- ✅ Project ID extracted from JWT token automatically (no hardcoded values)
- ✅ Resource unification working - volumes and IPs aggregated under VMs
- ✅ Hardware specs (CPU, RAM, disk) extracted and displayed
- ✅ Cost extraction from billing API working
- ✅ All billable resources discovered (VMs, volumes, IPs, Bare Metal ready)
- ✅ Connection instructions page completed with all 8 screenshots properly integrated
- 🔄 Next: Phase 3 - Pricing sync (optional, can be done later)

---

## Phase 1: Connection Dialogs and Guide

### Step 1.1: Research Cloud.ru API Requirements
**Goal**: Understand Cloud.ru authentication and API structure

**Tasks**:
- [ ] Research Cloud.ru API documentation
- [ ] Identify authentication method (API key, OAuth, service account, etc.)
- [ ] Document required credentials (API key, account ID, region, etc.)
- [ ] Identify API endpoints for:
  - Account information
  - Resource listing
  - Billing/cost data
  - Pricing information
- [ ] Test API access with sample credentials (if available)

**Deliverables**:
- API documentation notes
- Credential requirements list
- API endpoint mapping

**Estimated Time**: 2-4 hours

---

### Step 1.2: Add Cloud.ru to Provider Configuration (Frontend)
**Goal**: Add Cloud.ru to the connection dialog

**Files to Modify**:
- `app/static/js/connections.js`

**Tasks**:
- [ ] Add Cloud.ru entry to `providers` object in `connections.js`
  ```javascript
  'cloud-ru': {
      name: 'Cloud.ru',
      description: 'Cloud.ru — российская облачная платформа...',
      fields: [
          { name: 'api_key', label: 'API Key *', type: 'text', placeholder: '...', required: true },
          { name: 'account_id', label: 'Account ID *', type: 'text', placeholder: '...', required: true },
          // Add other required fields based on API research
      ]
  }
  ```
- [ ] Update `changeProvider()` function to handle `cloud-ru` provider
  - Add route mapping: `form.action = '/api/providers/cloud-ru/add'`
- [ ] Update `testConnection()` function to handle Cloud.ru test endpoint
  - Add: `testEndpoint = '/api/providers/cloud-ru/test'`
- [ ] Update `fillEditForm()` function to handle Cloud.ru credential fields

**Deliverables**:
- Updated `connections.js` with Cloud.ru configuration
- Connection dialog shows Cloud.ru as an option

**Estimated Time**: 1-2 hours

---

### Step 1.3: Create Cloud.ru API Routes (Backend)
**Goal**: Create Flask routes for Cloud.ru connection management

**Files to Create**:
- `app/providers/cloud_ru/__init__.py`
- `app/providers/cloud_ru/routes.py`

**Files to Modify**:
- `app/__init__.py` (register blueprint)

**Tasks**:
- [ ] Create `app/providers/cloud_ru/` directory structure
- [ ] Create `routes.py` with blueprint:
  ```python
  cloud_ru_bp = Blueprint('cloud_ru', __name__)
  ```
- [ ] Implement routes:
  - `POST /api/providers/cloud-ru/test` - Test connection
  - `POST /api/providers/cloud-ru/add` - Add new connection
  - `GET /api/providers/cloud-ru/<id>/edit` - Get connection for editing
  - `POST /api/providers/cloud-ru/<id>/update` - Update connection
  - `POST /api/providers/cloud-ru/<id>/sync` - Manual sync trigger
  - `DELETE /api/providers/cloud-ru/<id>/delete` - Soft delete connection
- [ ] Follow patterns from `app/providers/beget/routes.py` and `app/providers/selectel/routes.py`
- [ ] Include:
  - Authentication checks
  - Demo user write protection
  - Organization context validation
  - Connection testing before save
  - Error handling

**Deliverables**:
- Complete routes file with all CRUD operations
- Blueprint registered in main app

**Estimated Time**: 3-4 hours

---

### Step 1.4: Create Cloud.ru API Client (Basic)
**Goal**: Create basic API client for connection testing

**Files to Create**:
- `app/providers/cloud_ru/client.py`

**Tasks**:
- [ ] Create `CloudRuClient` class
- [ ] Implement `__init__()` method accepting credentials
- [ ] Implement `test_connection()` method:
  - Authenticate with Cloud.ru API
  - Fetch basic account information
  - Return standardized response format:
    ```python
    {
        'success': True/False,
        'message': 'Connection successful' or error message,
        'account_info': {
            'account_id': '...',
            'account_name': '...',
            # Other account details
        }
    }
    ```
- [ ] Handle authentication errors gracefully
- [ ] Add logging for debugging

**Deliverables**:
- Working API client with connection testing
- Can authenticate and retrieve account info

**Estimated Time**: 4-6 hours

---

### Step 1.5: Create Connection Instructions Page
**Goal**: Create user-friendly setup guide for Cloud.ru

**Files to Create**:
- `app/templates/instructions/cloud_ru.html`

**Files to Modify**:
- `app/web/main.py` - Add route mapping

**Tasks**:
- [ ] Create instruction template extending `instructions_base.html`
- [ ] Include sections:
  - Prerequisites
  - Step-by-step API setup guide
  - Screenshots (if available) or detailed text instructions
  - Common issues and troubleshooting
  - Security best practices
- [ ] Follow format from `app/templates/instructions/beget.html`
- [ ] Add route in `main.py`:
  ```python
  'cloud-ru': 'instructions/cloud_ru.html',
  ```

**Deliverables**:
- Complete instruction page accessible at `/instructions/cloud-ru`
- Instructions button in connection dialog opens this page

**Estimated Time**: 2-3 hours

---

### Step 1.6: Add Cloud.ru to Provider Catalog (Optional)
**Goal**: Make Cloud.ru available in admin/provider selection

**Files to Modify**:
- `app/templates/connections.html` (if provider list is hardcoded)
- Database: `provider_catalog` table (if used)

**Tasks**:
- [ ] Add Cloud.ru to enabled providers list in connections template
- [ ] Add provider logo (if available) to `app/static/provider_logos/`
- [ ] Update any provider catalog database entries

**Deliverables**:
- Cloud.ru appears in provider selection dropdown
- Provider logo displays correctly

**Estimated Time**: 1 hour

---

### Phase 1 Testing Checklist
- [ ] Cloud.ru appears in provider selection dropdown
- [ ] Connection dialog shows correct fields for Cloud.ru
- [ ] "Test Connection" button works and shows appropriate feedback
- [ ] "Instructions" button opens Cloud.ru instruction page
- [ ] Can successfully add a Cloud.ru connection
- [ ] Can edit an existing Cloud.ru connection
- [ ] Can delete a Cloud.ru connection (soft delete)
- [ ] Error messages are clear and helpful
- [ ] Demo user cannot modify connections (read-only protection)

**Phase 1 Total Estimated Time**: 13-20 hours

---

## Phase 2: Proper Syncing

### Step 2.1: Create Cloud.ru Provider Plugin
**Goal**: Implement the plugin interface for Cloud.ru

**Files to Create**:
- `app/providers/plugins/cloud_ru.py`

**Tasks**:
- [ ] Create `CloudRuProviderPlugin` class extending `ProviderPlugin`
- [ ] Implement required abstract methods:
  - `get_provider_type()` → return `"cloud-ru"`
  - `get_provider_name()` → return `"Cloud.ru"`
  - `get_required_credentials()` → return list of required fields
  - `test_connection()` → use CloudRuClient
  - `sync_resources()` → implement sync logic (Step 2.2)
  - `get_resource_mappings()` → map Cloud.ru resource types to unified taxonomy
  - `get_capabilities()` → return provider capabilities dict
- [ ] Add `__version__ = "1.0.0"`
- [ ] Initialize Cloud.ru client in `__init__()`

**Deliverables**:
- Plugin class that can be discovered by PluginManager
- All abstract methods implemented (sync can be placeholder initially)

**Estimated Time**: 2-3 hours

---

### Step 2.2: Extend Cloud.ru API Client for Resource Discovery
**Goal**: Add methods to fetch resources from Cloud.ru

**Files to Modify**:
- `app/providers/cloud_ru/client.py`

**Tasks**:
- [ ] Research Cloud.ru API endpoints for:
  - Virtual machines/servers
  - Storage volumes
  - Networks
  - Databases (if applicable)
  - Load balancers (if applicable)
  - Other resource types
- [ ] Implement methods:
  - `get_vms()` - List virtual machines
  - `get_volumes()` - List storage volumes
  - `get_networks()` - List networks
  - `get_billing_data()` - Get billing/cost information
  - `get_account_billing()` - Get account-level billing summary
- [ ] Normalize API responses to consistent format
- [ ] Handle pagination if API supports it
- [ ] Add error handling and retry logic
- [ ] Add logging for debugging

**Deliverables**:
- Extended client with resource discovery methods
- Can fetch all major resource types from Cloud.ru

**Estimated Time**: 6-8 hours

---

### Step 2.3: Implement Resource Sync Logic
**Goal**: Implement billing-first sync approach (like Beget/Selectel)

**Files to Modify**:
- `app/providers/plugins/cloud_ru.py`

**Tasks**:
- [ ] Implement `sync_resources()` method following billing-first pattern:
  
  **Phase 1: Billing Data Collection**
  - Collect account-level billing data
  - Get daily/monthly rates
  - Store billing summary
  
  **Phase 2: Resource Discovery**
  - Discover all resources (VMs, volumes, networks, etc.)
  - Filter for paid resources only (if applicable)
  - Collect resource metadata
  
  **Phase 3: Resource Processing and Unification**
  - Convert Cloud.ru resources to `ProviderResource` objects
  - Map Cloud.ru resource types to unified taxonomy:
    - VMs → `server`
    - Volumes → `volume`
    - Networks → `network`
    - etc.
  - Extract costs from billing data or resource metadata
  - Normalize costs to daily basis
  - Attach tags with Cloud.ru-specific metadata
  
  **Phase 4: Cost Validation**
  - Validate calculated costs against account billing
  - Log warnings if costs don't match
  
- [ ] Use `resource_registry` for status mapping
- [ ] Create helper methods for each resource type:
  - `_create_unified_vm()`
  - `_create_unified_volume()`
  - `_create_unified_network()`
  - etc.
- [ ] Return `SyncResult` object with:
  - `success`: boolean
  - `message`: string
  - `resources_synced`: count
  - `total_cost`: daily cost
  - `data`: dict with sync details

**Deliverables**:
- Complete sync implementation
- Resources are normalized and stored correctly
- Costs are calculated and validated

**Estimated Time**: 8-12 hours

---

### Step 2.4: Create Cloud.ru Service Layer (Optional but Recommended)
**Goal**: Create service class for business logic (following Selectel pattern)

**Files to Create**:
- `app/providers/cloud_ru/service.py`

**Tasks**:
- [ ] Create `CloudRuService` class
- [ ] Implement `sync_resources()` method that:
  - Uses the plugin for actual sync
  - Creates SyncSnapshot records
  - Saves resources to database
  - Handles errors and rollback
  - Returns standardized result dict
- [ ] Add helper methods:
  - `get_resource_summary()` - Get resource counts by type
  - `validate_credentials()` - Test credentials
- [ ] Integrate with existing sync orchestrator

**Deliverables**:
- Service layer that wraps plugin sync
- Handles database operations and error recovery

**Estimated Time**: 4-6 hours

---

### Step 2.5: Update Sync Route to Use Plugin System
**Goal**: Ensure sync route uses plugin orchestrator

**Files to Modify**:
- `app/providers/cloud_ru/routes.py`

**Tasks**:
- [ ] Update `sync_connection()` route to use `sync_orchestrator`:
  ```python
  from app.providers import sync_orchestrator
  
  sync_result = sync_orchestrator.sync_provider(provider_id, sync_type='manual')
  ```
- [ ] Format response to match frontend expectations
- [ ] Handle sync errors gracefully
- [ ] Return appropriate HTTP status codes

**Deliverables**:
- Sync route integrated with plugin system
- Sync works from UI "Sync" button

**Estimated Time**: 2 hours

---

### Step 2.6: Register Resource Mappings
**Goal**: Ensure Cloud.ru resource types map correctly

**Files to Modify**:
- `app/providers/resource_registry.py` (if needed)

**Tasks**:
- [ ] Review resource type mappings in plugin's `get_resource_mappings()`
- [ ] Add any Cloud.ru-specific status mappings to `ResourceRegistry`
- [ ] Test that resources appear correctly in UI
- [ ] Verify resource filtering works (by type, status, etc.)

**Deliverables**:
- Resources display correctly in dashboard
- Resource types are properly categorized

**Estimated Time**: 2-3 hours

---

### Phase 2 Testing Checklist
- [ ] Plugin is discovered by PluginManager
- [ ] Can sync Cloud.ru resources successfully
- [ ] Resources appear in dashboard after sync
- [ ] Resource types are correctly mapped
- [ ] Costs are calculated and displayed correctly
- [ ] Sync snapshot is created with correct metadata
- [ ] Multiple syncs create multiple snapshots
- [ ] Error handling works (invalid credentials, API errors, etc.)
- [ ] Sync can be triggered manually from UI
- [ ] Auto-sync works if enabled
- [ ] Resources can be filtered and searched in UI

**Phase 2 Total Estimated Time**: 24-36 hours

---

## Phase 3: Price Updating

### Step 3.1: Research Cloud.ru Pricing API
**Goal**: Understand how to fetch pricing data from Cloud.ru

**Tasks**:
- [ ] Research Cloud.ru pricing API endpoints
- [ ] Identify pricing data sources:
  - Public pricing API
  - Billing API with SKU prices
  - Configurator API (like Beget)
  - Manual pricing data
- [ ] Document pricing structure:
  - Resource types with pricing
  - Pricing units (hourly, monthly, per GB, etc.)
  - Regional pricing differences
  - Commitment/reserved instance pricing (if applicable)
- [ ] Test API access for pricing endpoints

**Deliverables**:
- Pricing API documentation
- List of available pricing endpoints
- Pricing data structure notes

**Estimated Time**: 3-4 hours

---

### Step 3.2: Create Cloud.ru Pricing Client
**Goal**: Create client for fetching pricing data

**Files to Create**:
- `app/providers/cloud_ru/pricing.py` (or add to `client.py`)

**Tasks**:
- [ ] Create `CloudRuPricingClient` class
- [ ] Implement pricing fetch methods:
  - `get_vm_prices()` - Virtual machine pricing
  - `get_storage_prices()` - Storage/volume pricing
  - `get_network_prices()` - Network pricing
  - `get_all_prices()` - Fetch all pricing data
- [ ] Normalize pricing to standard format:
  ```python
  {
      'provider': 'cloud-ru',
      'resource_type': 'server',
      'provider_sku': 'vm-standard-1',
      'region': 'ru-central1',
      'cpu_cores': 1,
      'ram_gb': 2,
      'storage_gb': 20,
      'storage_type': 'SSD',
      'hourly_cost': 0.50,
      'monthly_cost': 360.0,
      'currency': 'RUB',
      'source': 'billing_api',
      'confidence_score': 0.95
  }
  ```
- [ ] Handle different pricing models (hourly, monthly, per-unit)
- [ ] Generate grid pricing if needed (CPU/RAM/Disk combinations)
- [ ] Add error handling and logging

**Deliverables**:
- Pricing client that can fetch all pricing data
- Pricing data normalized to standard format

**Estimated Time**: 6-8 hours

---

### Step 3.3: Implement get_pricing_data() in Plugin
**Goal**: Add pricing method to Cloud.ru plugin

**Files to Modify**:
- `app/providers/plugins/cloud_ru.py`

**Tasks**:
- [ ] Implement `get_pricing_data()` method in `CloudRuProviderPlugin`
- [ ] Use `CloudRuPricingClient` to fetch pricing
- [ ] Combine pricing from different sources if needed
- [ ] Return list of standardized pricing records
- [ ] Handle errors gracefully (return empty list on failure)
- [ ] Add logging for pricing collection progress

**Deliverables**:
- Plugin method that returns pricing data
- Pricing data ready for database storage

**Estimated Time**: 2-3 hours

---

### Step 3.4: Create Pricing Sync Script (Optional)
**Goal**: Create standalone script for testing pricing sync

**Files to Create**:
- `scripts/cloud_ru_pricing_fetch.py` (optional, for testing)

**Tasks**:
- [ ] Create script similar to `scripts/selectel_vpc_pricing_fetch.py`
- [ ] Allow manual pricing sync for testing
- [ ] Output pricing data to JSON file for inspection
- [ ] Add command-line arguments for credentials

**Deliverables**:
- Standalone script for testing pricing collection

**Estimated Time**: 2-3 hours

---

### Step 3.5: Test Price Update Service Integration
**Goal**: Ensure pricing sync works with existing price update service

**Files to Review**:
- `app/core/services/price_update_service.py`

**Tasks**:
- [ ] Verify `PriceUpdateService` can discover Cloud.ru plugin
- [ ] Test pricing sync via:
  - Admin panel (if available)
  - CLI script: `scripts/sync_provider_prices.py`
  - API endpoint (if available)
- [ ] Verify pricing data is saved to `provider_prices` table
- [ ] Check that pricing records have correct:
  - Provider type: `cloud-ru`
  - Resource types
  - Costs (hourly, monthly)
  - Regions
  - Metadata

**Deliverables**:
- Pricing sync works end-to-end
- Pricing data stored in database

**Estimated Time**: 3-4 hours

---

### Step 3.6: Add Pricing to Provider Catalog (If Needed)
**Goal**: Ensure Cloud.ru pricing appears in price comparison features

**Tasks**:
- [ ] Test price comparison UI with Cloud.ru pricing
- [ ] Verify Cloud.ru appears in provider selection for comparisons
- [ ] Test filtering by resource type, region, etc.
- [ ] Verify pricing recommendations include Cloud.ru options

**Deliverables**:
- Cloud.ru pricing integrated into comparison features

**Estimated Time**: 2-3 hours

---

### Phase 3 Testing Checklist
- [ ] Can fetch pricing data from Cloud.ru API
- [ ] Pricing data is normalized correctly
- [ ] Pricing sync saves data to database
- [ ] Pricing records have correct structure
- [ ] Price comparison UI shows Cloud.ru pricing
- [ ] Pricing recommendations include Cloud.ru
- [ ] Pricing updates work via admin panel/scripts
- [ ] Error handling works for pricing API failures

**Phase 3 Total Estimated Time**: 18-25 hours

---

## Summary

### Total Estimated Time
- **Phase 1 (Connection & Guide)**: 13-20 hours
- **Phase 2 (Syncing)**: 24-36 hours
- **Phase 3 (Pricing)**: 18-25 hours
- **Total**: 55-81 hours

### Key Files to Create/Modify

**New Files**:
1. `app/providers/cloud_ru/__init__.py`
2. `app/providers/cloud_ru/routes.py`
3. `app/providers/cloud_ru/client.py`
4. `app/providers/cloud_ru/service.py` (optional)
5. `app/providers/cloud_ru/pricing.py` (or in client.py)
6. `app/providers/plugins/cloud_ru.py`
7. `app/templates/instructions/cloud_ru.html`
8. `scripts/cloud_ru_pricing_fetch.py` (optional)

**Files to Modify**:
1. `app/static/js/connections.js` - Add Cloud.ru to provider config
2. `app/__init__.py` - Register Cloud.ru blueprint
3. `app/web/main.py` - Add instruction route
4. `app/templates/connections.html` - Add to provider list (if needed)

### Dependencies
- Cloud.ru API documentation
- Cloud.ru API credentials for testing
- Understanding of Cloud.ru resource types and billing model

### Notes
- Follow existing patterns from Beget/Selectel implementations
- Use billing-first sync approach for consistency
- Ensure proper error handling and logging throughout
- Test each phase before moving to the next
- Consider Cloud.ru-specific features (regions, resource types, etc.)

---

## Next Steps

1. **Start with Phase 1**: Research Cloud.ru API and create connection infrastructure
2. **Test thoroughly**: Ensure connection works before moving to sync
3. **Iterate**: Adjust implementation based on Cloud.ru API specifics
4. **Document**: Keep notes on Cloud.ru-specific quirks or requirements

Good luck with the implementation! 🚀

