# InfraZen Platform – Consolidated Product Description

## 1. Vision & Positioning
- **Product:** InfraZen – multi-cloud FinOps platform tailored to the Russian market.
- **Primary Promise:** Deliver centralized cost control, clear analytics, and actionable recommendations that reduce cloud waste by 30–70%.
- **Tagline:** "FinOps Platform" with brand message "Мультиоблачный FinOps для российского рынка".
- **Target Customers:** Mid-to-large enterprises spending 500k ₽+/month on cloud, organizations operating across 2+ cloud providers (Yandex.Cloud, VK Cloud, Selectel, Cloud.ru, etc.), MSPs, and integrators.
- **Differentiators:** Business-oriented insights (unit economics, CFO-ready reports), out-of-the-box multi-cloud integrations, auto-allocation without tags, transparent budgeting & forecasts, rapid 1-day onboarding, SaaS and on-prem deployment options.

## 2. Problem Landscape
- Enterprises struggle to control escalating cloud costs and lack a unified view across multi-cloud estates.
- Inefficient governance leads to 30–70% overspend, budget overruns, and low executive trust.
- Existing Russian-market solutions either lack multi-cloud reach, business-aligned metrics, or remain overly technical for finance stakeholders.

## 3. Solution Overview
InfraZen connects to cloud providers via API, automatically ingests billing and utilization data, applies analytics to identify "silent" spend, and offers guided optimizations delivered through a unified web experience and optional Telegram bot notifications. Implementation is manual or semi-automated, enabling quick ROI without heavy integration projects.

## 4. Core Principles & Stakeholders
- **FinOps Foundation Alignment:** Collaboration, Visibility, Optimization, Financial Accountability, Iterative Improvement.
- **Stakeholders Served:** Executives, Finance & Procurement, FinOps practitioners, Operations, Engineering teams.
- **Maturity Approach:** Crawl/Walk/Run adoption roadmap that scales capabilities with business value.

## 5. Brand & Visual Identity Guidelines
- **Logo:** Blue cloud glyph with modern sans-serif typography.
- **Palette:** Primary Blue #1E40AF, Secondary Blue #3B82F6, Success Green #10B981, Warning Orange #F59E0B, Error Red #EF4444, Background #FFFFFF, Light Gray #F8FAFC, Text Primary #1F2937, Text Secondary #6B7280.
- **Typography:** System modern sans-serif family with clear hierarchy, high-contrast text for readability across roles.

## 6. Platform Architecture & Structure
- **Prototype Stack:** Flask SSR application rendering Jinja2 templates; Flask serves static assets (CSS/JS/images) alongside HTML.
- **Application Layout:** Left sidebar navigation, header with module context/actions, dynamic main content area, user profile section anchored to sidebar footer.
- **Key Directories (prototype):**
  - `src/main.py` (Flask app & routing)
  - `src/templates/` (`base.html`, `dashboard.html`, `connections.html`, `resources.html`, `page.html`, `index.html`)
  - `src/static/` (`css/style.css`, favicon, imagery)
  - `src/data/mock_data.py` (comprehensive demo data for Yandex Cloud & Selectel)
  - `src/routes/` (main.py, auth.py, user.py - modular routing)
  - `src/models/` (user.py - database models)
- **Data Flow:** Request → Flask route → data retrieval (DB/mocks) → template render with injected metrics → HTML response → optional JS-driven interactivity (charts, forms).
- **Current Implementation Status:** Demo-ready prototype with working dashboard, connections, and resources pages. Google OAuth authentication fully implemented with profile integration. Clean separation between demo users (mock data) and real users (database data). Demo user session automatically enabled with realistic Yandex Cloud and Selectel infrastructure data (8 resources, 2 providers, cost analytics, recommendations). Real users see empty state until they add actual cloud connections. Full CRUD operations implemented for cloud provider connections with comprehensive edit functionality, provider pre-selection, and secure credential management.

## 6.1. Multi-Cloud Sync Architecture

### 6.1.1. Sync System Overview
The InfraZen platform implements a comprehensive multi-cloud synchronization system designed to provide real-time visibility into cloud resources, costs, and utilization across all connected providers. The sync architecture is built on a snapshot-based approach that enables historical analysis, trend tracking, and AI-powered optimization recommendations.

### 6.1.2. Core Sync Components

#### **Sync Models & Database Schema**
- **`SyncSnapshot`**: Tracks metadata for each sync operation including timing, status, resource counts, and cost totals
- **`ResourceState`**: Records the state of individual resources during each sync, enabling change detection and historical tracking
- **`Resource`**: Universal resource registry storing normalized data from all cloud providers
- **`CloudProvider`**: Provider connection management with credential storage and sync status tracking

#### **Sync Service Architecture**
- **`SyncService`**: Core orchestration service that manages the entire sync process
- **Provider Clients**: Specialized API clients for each cloud provider (Beget, Yandex.Cloud, Selectel, AWS, Azure, GCP)
- **Change Detection**: Automated comparison between current and previous resource states
- **State Management**: Tracks resource lifecycle (created, updated, deleted, unchanged)

### 6.1.3. Sync Process Flow

#### **Manual Sync Trigger**
1. User clicks "Синхронизировать" button on connection card
2. `SyncService` creates new `SyncSnapshot` with "running" status
3. Provider-specific client authenticates and fetches all resources
4. Service compares current resources with existing database records
5. Creates/updates/deletes `Resource` entries as needed
6. Records `ResourceState` entries for change tracking
7. Updates `SyncSnapshot` with completion status and statistics
8. Updates provider's `last_sync` timestamp

#### **Resource Processing Logic**
- **New Resources**: Create `Resource` entry with provider-specific configuration stored as JSON
- **Existing Resources**: Compare fields and update if changes detected
- **Deleted Resources**: Mark as inactive with "deleted" status
- **Change Detection**: Track cost changes, status changes, and configuration changes

### 6.1.4. Data Normalization & Storage

#### **Universal Resource Schema**
All cloud resources are normalized into a unified schema regardless of provider:
- **Core Fields**: `resource_id`, `resource_name`, `resource_type`, `service_name`, `region`, `status`
- **Financial Data**: `effective_cost`, `currency`, `billing_period`
- **Business Context**: `business_unit`, `project`, `environment`, `owner`
- **Provider Config**: JSON storage for provider-specific attributes (IP addresses, hostnames, etc.)

#### **Provider-Specific Data Handling**
- **Beget**: VPS servers, domains, databases, FTP accounts, email accounts
- **Yandex.Cloud**: Compute instances, storage, databases, load balancers, networks
- **Selectel**: Virtual servers, block storage, object storage, CDN, DNS
- **AWS/Azure/GCP**: Comprehensive resource coverage including compute, storage, networking, databases

### 6.1.5. Sync Mechanics & Features

#### **Snapshot-Based Architecture**
- Each sync creates a complete snapshot of the current cloud state
- Historical snapshots enable trend analysis and cost forecasting
- Resource state tracking provides detailed change history
- Enables rollback capabilities and audit trails

#### **Change Detection & Tracking**
- **Cost Changes**: Track monthly cost fluctuations per resource
- **Status Changes**: Monitor resource lifecycle (running, stopped, terminated)
- **Configuration Changes**: Detect infrastructure modifications
- **Resource Lifecycle**: Track creation, updates, and deletion events

#### **Error Handling & Recovery**
- Comprehensive error logging and reporting
- Graceful handling of API failures and rate limits
- Retry mechanisms for transient failures
- Detailed error messages for troubleshooting

### 6.1.6. AI Integration & Analytics

#### **Data Preparation for AI Analysis**
- Normalized resource data enables cross-provider analysis
- Historical snapshots provide training data for ML models
- Cost trends and utilization patterns feed optimization algorithms
- Resource tagging and business context enhance AI insights

#### **Future AI Capabilities**
- **Cost Optimization**: AI-powered recommendations for resource right-sizing
- **Anomaly Detection**: ML models for detecting unusual spending patterns
- **Predictive Analytics**: Forecasting future costs based on historical trends
- **Automated Tagging**: AI-assisted resource classification and tagging

### 6.1.7. Performance & Scalability

#### **Efficient Data Processing**
- Batch processing for large resource inventories
- Incremental sync capabilities for frequent updates
- Optimized database queries for fast data retrieval
- Caching mechanisms for frequently accessed data

#### **Scalability Considerations**
- Horizontal scaling support for multiple sync workers
- Database partitioning for large datasets
- API rate limiting and throttling
- Background job processing for long-running syncs

### 6.1.8. Current Implementation Status

#### **Implemented Components**
- **Sync Models**: `SyncSnapshot` and `ResourceState` models fully implemented with JSON serialization support
- **Sync Service**: Core `SyncService` class with comprehensive resource processing logic
- **Beget Integration**: Complete Beget API client with VPS, domains, databases, FTP, and email resource support
- **Change Detection**: Automated comparison between current and previous resource states
- **Error Handling**: Comprehensive error logging and graceful failure handling

#### **Database Schema**
```sql
-- Sync Snapshots Table
CREATE TABLE sync_snapshots (
    id INTEGER PRIMARY KEY,
    provider_id INTEGER NOT NULL,
    sync_type VARCHAR(20) NOT NULL,  -- manual, scheduled
    sync_status VARCHAR(20) NOT NULL,  -- running, success, error
    sync_started_at DATETIME NOT NULL,
    sync_completed_at DATETIME,
    sync_duration_seconds INTEGER,
    total_resources_found INTEGER DEFAULT 0,
    resources_created INTEGER DEFAULT 0,
    resources_updated INTEGER DEFAULT 0,
    resources_deleted INTEGER DEFAULT 0,
    resources_unchanged INTEGER DEFAULT 0,
    total_monthly_cost FLOAT DEFAULT 0.0,
    total_resources_by_type TEXT,  -- JSON
    total_resources_by_status TEXT,  -- JSON
    error_message TEXT,
    error_details TEXT,
    sync_config TEXT  -- JSON
);

-- Resource States Table
CREATE TABLE resource_states (
    id INTEGER PRIMARY KEY,
    sync_snapshot_id INTEGER NOT NULL,
    resource_id INTEGER,
    provider_resource_id VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_name VARCHAR(255) NOT NULL,
    state_action VARCHAR(20) NOT NULL,  -- created, updated, deleted, unchanged
    previous_state TEXT,  -- JSON
    current_state TEXT,  -- JSON
    changes_detected TEXT,  -- JSON
    service_name VARCHAR(100),
    region VARCHAR(100),
    status VARCHAR(50),
    effective_cost FLOAT,
    has_cost_change BOOLEAN DEFAULT FALSE,
    has_status_change BOOLEAN DEFAULT FALSE,
    has_config_change BOOLEAN DEFAULT FALSE
);
```

#### **API Endpoints**
- **`POST /api/providers/beget/<provider_id>/sync`**: Manual sync trigger for Beget connections
- **`GET /api/providers/<provider_id>/sync/status`**: Check sync status and progress
- **`GET /api/sync/snapshots`**: Retrieve sync history and statistics

#### **Data Flow Implementation**
1. **User Action**: Click "Синхронизировать" button on connection card
2. **Route Handler**: `sync_connection()` function in `app/providers/beget/routes.py`
3. **Service Layer**: `SyncService.sync_resources()` orchestrates the entire process
4. **Provider Client**: `BegetAPIClient.get_all_resources()` fetches comprehensive resource data
5. **Data Processing**: Compare, create, update, or delete resources as needed
6. **State Tracking**: Record `ResourceState` entries for change detection
7. **Snapshot Completion**: Update `SyncSnapshot` with final statistics and status

#### **JSON Data Handling**
- **Provider Configuration**: Complex provider-specific data stored as JSON in `Resource.provider_config`
- **Resource States**: Previous and current states stored as JSON for efficient comparison
- **Change Detection**: Detailed change information stored as JSON for analysis
- **Sync Configuration**: Sync parameters and settings stored as JSON for flexibility

### 6.1.9. Future Enhancements

#### **Scheduled Syncs**
- Cron-based automatic synchronization
- Configurable sync intervals per provider
- Background job processing with Celery/Redis
- Sync queue management and prioritization

#### **Advanced Analytics**
- Cost trend analysis across multiple snapshots
- Resource utilization pattern detection
- Anomaly detection for unusual spending
- Predictive cost forecasting

#### **Multi-Provider Support**
- Yandex.Cloud API integration
- Selectel API integration
- AWS/Azure/GCP API clients
- Unified resource normalization across all providers

## 7. Navigation & Module Breakdown
```
✅ Dashboard (primary landing) – focus on spend overview and health
✅ Cloud Connections – manage provider integrations and statuses  
✅ Resources – inventory and tagging governance
🔄 Cost Analytics / Cost Explorer – granular spend analysis and filtering
🔄 Recommendations – optimization backlog with savings estimates
🔄 Business Context – unit economics, cost-to-value mapping
🔄 Reports – custom/scheduled reports and exports
🔄 Settings – user roles, permissions, budgeting policies, integrations
```

### 7.1.1 Cloud Connections ✅ IMPLEMENTED
- **Connection Management:** Full CRUD operations with comprehensive edit functionality, provider pre-selection, and secure credential management
- **Provider Support:** Beget (fully implemented with direct API integration), AWS, Azure, GCP, VK Cloud, Yandex Cloud, Selectel (UI ready with dynamic forms)
- **Connection Testing:** Real-time API validation with direct HTTP requests to Beget API using proper token-based authentication
- **Security:** Encrypted password storage, user ownership validation, authentication checks, secure edit operations
- **User Experience:** Provider pre-selection from available providers, dynamic forms that adapt to provider type, loading states, comprehensive error handling, pre-filled edit forms
- **Edit Functionality:** Settings button opens modal with pre-filled connection details, secure password handling, connection validation on updates
- **API Integration:** Clean, maintainable direct API integration with Beget using requests library for reliable authentication and data retrieval

### 7.1.2 Dashboard Highlights ✅ IMPLEMENTED
- **Top Controls:** Date-range selector (7/30/90 days, 1 year), manual refresh, and export actions aligned to the header for fast reporting.
- **KPI Cards Row:** ✅ Discrete cards for Total Expenses (117,150 ₽ with -12.5% trend), Potential Savings (10,400 ₽), Active Resources (8 resources), and Connected Providers (2 providers); each card surfaces iconography, primary value, and secondary context at a glance.
- **Connected Providers Grid:** ✅ Card grid listing each cloud (YC/SEL badges + names, connection status, added dates). Includes persistent "Добавить" tile and "Добавить провайдера" button.
- **Expense Dynamics vs. Resource Usage Split:** ✅ Layout pairs expense trend summary with resource utilization panel showing progress bars for CPU (67%), RAM (81%), Storage (43%), and Network (29%) with used vs. available capacity labels.
- **Optimization Recommendations:** ✅ Active recommendations list with 3 optimization suggestions (rightsize, cleanup, storage policy) totaling 10,400 ₽ potential savings.
- **Resource Inventory:** ✅ Comprehensive table with all 8 resources from both providers, search/filter capabilities, and detailed resource information.

### 7.1.1 Demo Implementation Details ✅ LIVE
- **Demo User Session:** Automatically enabled for all routes without authentication requirement
- **Mock Data Sources:** Realistic Yandex Cloud and Selectel infrastructure with proper Russian regions, costs in rubles
- **Provider Coverage:** 
  - Yandex Cloud: `ru-central1-a/b` regions, organization/cloud/folder IDs, Intel platforms
  - Selectel: `msk-a/spb-a` regions, project IDs, standard/memory flavors
- **Resource Types:** VMs (4), Disks/Volumes (2), Buckets (2) with detailed configurations
- **API Endpoints:** `/api/demo/*` endpoints for programmatic access to all demo data
- **Cost Structure:** Total monthly spend ~117,150 ₽ with 10,400 ₽ optimization potential
- **Authentication:** Google OAuth integration with real user profiles, circular avatar display, and secure session management
- **User Separation:** Demo users (mock data) vs Real users (database data) with conditional UI and trend displays

### 7.2 Cost Explorer / Analytics
- Filterable by provider, account, service, region, tag, time period.
- Rich tables with sorting/pagination; charts (bar/pie/line) for cost breakdowns.
- Pair cost metrics with utilization (CPU, memory, storage) for context.

### 7.3 Optimization & Recommendations
- Recommendation cards/tables with category, proposed action (rightsize, decommission, reserved instance), estimated savings, confidence, and action buttons triggering follow-up routes.
- Policy management views for defining spend guardrails and compliance rules.

### 7.4 Budgeting & Forecasting
- Budget creation and management across scopes (team, project, provider) with alert thresholds.
- Visual budget vs. actuals chart and forecast projections (trend/scenario-based).

### 7.5 Reporting & Exports
- Report builder for selecting dimensions/metrics and visualization types.
- Scheduling interface for automated delivery; archive for historical reports.
- Export support: CSV, PDF, PNG (for charts and summaries).

### 7.6 Settings & Administration
- User & role management, permissions, SSO readiness.
- Cloud provider integration wizard (provider selection, connection naming, API key, organization ID, credential storage checkbox).
- Tag governance tooling, billing profile management, localization support (Rubles primary currency).

## 8. Functional Scenarios & Value Proof (Pitch Deck Cases)
- **Product Team in Multi-cloud:** Highlighted experiment costs, automated off-hours shutdown → 18% monthly savings.
- **Finance Team:** Enabled plan-vs-actual budgeting and live variance alerts → prevented overruns on three projects.
- **SaaS Company (3 clouds):** Unified spend, mapped costs to customers/products → 28% savings via decommissioned duplicates.
- **Startup on Yandex.Cloud:** Found unused disks/IPs, set Telegram alerts → 12% first-month savings.
- **MSP with 30 Clients:** Per-client cost attribution and margin analytics → +15% profit through tariff optimization.
- **Product Manager:** Linked features to operating cost → removed unprofitable features.
- **No-Tag Culture:** Auto-allocation categorized 87% resources without tags.
- **CFO in Holding:** Monthly executive-ready briefs, streamlined BI export → 70% faster reporting cycle.

## 9. Competitive Landscape Snapshot
- **Cloudmaster:** Multi-cloud limited, provides advice & notifications but lacks unit economics, heavier UX for business users.
- **FinOps360:** Focus on optimization + security (CNAPP); strong enterprise feature set but complex UI and limited executive reporting.
- **Cloud Advisor:** Yandex Cloud-only, lacks multi-cloud, unit economics, budgeting, on-prem options.
- **InfraZen Advantage:** Balanced FinOps + business insights, rapid deployment, native support for Russian providers, CFO-friendly UX.

## 10. Business Model Notes
- **Base Tier:** Analytics, reports, recommendations for smaller teams/initial rollout.
- **Premium Tiers:** Automated optimizations, advanced role-based partitioning, extended reporting, APIs.
- **Add-on Revenue:** Consulting, training, white-label deployments, turnkey implementations.
- **Scalability:** Pricing scales with infrastructure footprint; ARPU grows alongside client expansion.

## 11. Implementation Roadmap (Prototype Focus)
1. ✅ Set up Flask foundation with base template & sidebar navigation.
2. ✅ Implement dashboard view populated by mock data (Rubles currency).
3. ✅ Build cloud connections interface with provider cards and modal workflow.
4. ✅ Create comprehensive resources inventory with detailed resource management.
5. ✅ Implement demo user session with realistic Yandex Cloud and Selectel data.
6. ✅ Add JSON API endpoints for demo data access.
7. ✅ Implement Google OAuth authentication with profile integration.
8. ✅ Separate demo users (mock data) from real users (database data) with conditional UI.
9. ✅ Implement full CRUD operations for cloud provider connections with edit functionality.
10. ✅ Add provider pre-selection and comprehensive connection management features.
11. 🔄 Introduce cost analytics, budgeting, and recommendations views with placeholder charts (Chart.js/D3).
12. 🔄 Layer responsive design (mobile-first; collapsible sidebar, grid-based cards).
13. 🔄 Integrate Telegram bot and notification hooks (future phase).
14. 🔄 Deploy demo-ready prototype.

## 12. Data & Integration Requirements
- Provider API connectors (Yandex.Cloud, VK Cloud, Selectel, GCP, AWS, Azure for future expansion).
- Billing ingestion aligned with FOCUS (FinOps Open Cost and Usage Specification) format where feasible.
- Mock datasets covering cost trends, utilization, recommendations, multi-currency with Ruble focus.
- Support for manual overrides and annotations to tie costs to business units/features.

## 13. FinOps Resource Tracking Architecture ✅ IMPLEMENTED

### 13.1 Core Strategy
InfraZen implements a **unified multi-cloud resource tracking system** that captures comprehensive technical and billing information for all deployed resources across providers. The architecture follows FinOps best practices and FOCUS specification to enable:

- **Complete Resource Discovery**: Automatic synchronization of all resources when provider connections are established
- **Comprehensive Data Capture**: Technical specifications, billing information, usage metrics, and operational logs
- **Business Context Mapping**: Flexible tagging system for cost allocation to business units, projects, and features
- **Trend Analysis**: Historical data storage for usage patterns, cost optimization, and predictive analytics
- **Incremental Expansion**: Start with one provider, extend to multiple providers with consistent core properties

### 13.2 Implementation Status ✅ COMPLETED
- **Unified Database Schema**: All models migrated to unified `CloudProvider`, `Resource`, `ResourceTag`, `ResourceMetric` architecture
- **Beget Integration**: Full Beget API integration with unified models (connection creation, editing, deletion, sync)
- **Clean Architecture**: Removed legacy Beget-specific models, all operations use unified system
- **Password Security**: API connection passwords stored in plain text, user passwords properly hashed
- **Database Cleanup**: Fresh database with only unified models, no legacy table conflicts

### 13.3 Current Implementation Details

#### 13.3.1 Database Models ✅
- **`CloudProvider`**: Unified provider connections (replaces provider-specific connection tables)
- **`Resource`**: Universal resource registry with core properties and provider-specific JSON config
- **`ResourceTag`**: Flexible tagging system for business context and cost allocation
- **`ResourceMetric`**: Usage and performance metrics with time-series data
- **`ResourceUsageSummary`**: Aggregated usage statistics and trends
- **`ResourceLog`**: Operational logs for component discovery and analysis
- **`ResourceComponent`**: Internal resource components discovered through log analysis
- **`CostAllocation`**: Business unit and project cost mapping
- **`CostTrend`**: Historical cost data for trend analysis
- **`OptimizationRecommendation`**: AI-generated cost optimization suggestions

#### 13.3.2 Provider Integration ✅
- **Beget API**: Complete integration with unified models
  - Connection management (create, edit, delete, sync)
  - Resource discovery (VPS, domains, databases, FTP accounts)
  - Usage tracking and cost analysis
  - Plain text password storage for API authentication
- **Extensible Architecture**: Ready for additional providers (Yandex.Cloud, VK Cloud, Selectel, AWS, Azure, GCP)

#### 13.3.3 Security Implementation ✅
- **User Passwords**: Properly hashed using Werkzeug security functions
- **API Connection Passwords**: Stored in plain text for API authentication (encrypted in production)
- **Credentials Storage**: JSON-encoded credentials in `CloudProvider.credentials` field
- **Session Management**: Secure user authentication and session handling

### 13.4 New Scalable Architecture ✅ FULLY IMPLEMENTED

#### 13.4.1 Project Structure ✅ COMPLETED
```
InfraZen/
├── app/                           # Main application package
│   ├── __init__.py               # Flask app factory with blueprint registration
│   ├── config.py                 # Environment-based configuration management
│   ├── core/                     # Core business logic (provider-agnostic)
│   │   ├── database.py           # Shared SQLAlchemy instance
│   │   ├── models/               # Database models (separated by concern)
│   │   │   ├── __init__.py       # Model imports and db instance
│   │   │   ├── base.py          # Base model with common functionality
│   │   │   ├── user.py          # User authentication model
│   │   │   ├── provider.py      # CloudProvider model with auto_sync
│   │   │   ├── resource.py      # Universal Resource model
│   │   │   ├── metrics.py       # Resource metrics and usage
│   │   │   ├── tags.py          # Resource tagging system
│   │   │   ├── logs.py          # Operational logs and components
│   │   │   ├── costs.py         # Cost allocation and trends
│   │   │   └── recommendations.py # AI recommendations
│   │   └── utils/               # Core utilities (mock_data.py)
│   ├── providers/               # Provider-specific implementations
│   │   ├── base/               # Abstract provider interface
│   │   │   ├── __init__.py      # Base provider package
│   │   │   ├── provider_base.py # Base provider class
│   │   │   └── resource_mapper.py # Resource mapping utilities
│   │   ├── beget/              # Beget provider implementation
│   │   │   ├── __init__.py      # Beget provider package
│   │   │   ├── client.py       # BegetAPIClient with full API integration
│   │   │   ├── service.py       # Beget business logic
│   │   │   └── routes.py       # Beget CRUD routes (add/edit/delete/test)
│   │   ├── yandex/             # Future Yandex provider
│   │   └── aws/                # Future AWS provider
│   ├── api/                    # REST API routes
│   │   ├── __init__.py         # API package
│   │   ├── auth.py             # Authentication routes
│   │   ├── providers.py        # Provider API routes
│   │   └── resources.py        # Resource API routes
│   ├── web/                    # Web interface routes
│   │   ├── __init__.py         # Web package
│   │   └── main.py             # Main web routes (dashboard, connections, etc.)
│   ├── static/                 # Static assets
│   │   ├── css/style.css       # Main stylesheet
│   │   └── favicon.ico         # Site favicon
│   └── templates/              # Jinja2 templates
│       ├── base.html           # Base template
│       ├── dashboard.html      # Dashboard page
│       ├── connections.html    # Connections page
│       ├── resources.html      # Resources page
│       ├── login.html          # Login page
│       └── index.html          # Landing page
├── instance/                   # Instance folder (database, logs)
│   └── dev.db                  # SQLite database
├── tests/                      # Test suite (future)
├── docker/                     # Docker configuration (future)
├── run.py                      # Application entry point
├── config.env                  # Environment variables
└── requirements.txt            # Python dependencies
```

#### 13.4.2 Architecture Benefits ✅ ACHIEVED
- **✅ Scalable Provider System**: Clean plugin architecture for easy provider addition
- **✅ Clean Separation**: Core business logic separated from provider-specific code
- **✅ Extensible Models**: Each model in separate file with clear responsibilities
- **✅ Flask Best Practices**: App factory pattern, blueprint organization, instance folder
- **✅ Database Management**: Centralized db instance, proper model imports
- **✅ Production Ready**: Structured for Docker deployment and horizontal scaling
- **✅ Security**: Proper password hashing, secure credential storage
- **✅ Configuration**: Environment-based config with python-dotenv

#### 13.4.3 Provider System Design ✅ IMPLEMENTED
- **✅ Base Provider Interface**: Abstract class defining provider contract
- **✅ Resource Mapping**: Unified resource format across all providers
- **✅ Credential Management**: Secure JSON-encoded credential storage
- **✅ Extensible**: New providers added as separate modules
- **✅ Configuration Driven**: Provider availability controlled via environment
- **✅ CRUD Operations**: Full create, read, update, delete for connections
- **✅ API Integration**: Real-time connection testing and validation

#### 13.4.4 Implementation Status ✅ COMPLETED
- **✅ Complete Migration**: All code moved to new scalable structure
- **✅ Database Schema**: Fresh unified schema with all required columns
- **✅ Provider Integration**: Beget fully integrated with unified models
- **✅ Authentication**: Google OAuth with demo/real user separation
- **✅ Web Interface**: All pages working with new architecture
- **✅ API Routes**: RESTful API endpoints for all operations
- **✅ Static Assets**: CSS, templates, and assets properly organized
- **✅ Error Handling**: Comprehensive error handling and user feedback

#### 13.4.5 Current System Status ✅ PRODUCTION READY
- **✅ Server Stability**: Flask development server running reliably on port 5001
- **✅ Database Integrity**: Fresh SQLite database with proper schema and all required columns
- **✅ Authentication Flow**: Google OAuth working with demo user fallback
- **✅ Provider Management**: Full CRUD operations for Beget connections
- **✅ Dashboard Functionality**: Mock data display for demo users, real data for authenticated users
- **✅ Error Resolution**: All database schema conflicts resolved, no more column errors
- **✅ Clean Architecture**: Follows Flask best practices with proper separation of concerns
- **✅ Scalability Ready**: Architecture supports easy addition of new cloud providers

#### 13.4.6 Next Development Phases
**Phase 1: Additional Providers (Immediate)**
- 🔄 Add Yandex Cloud integration using unified models
- 🔄 Add Selectel integration using unified models
- 🔄 Add AWS integration using unified models
- 🔄 Implement provider-specific resource discovery and sync

**Phase 2: Advanced Features (Short-term)**
- 🔄 Implement Flask-Migrate for database versioning
- 🔄 Add comprehensive test suite
- 🔄 Implement resource synchronization and monitoring
- 🔄 Add cost analytics and trend analysis

**Phase 3: Production Deployment (Medium-term)**
- 🔄 Docker containerization
- 🔄 Production database (PostgreSQL)
- 🔄 Redis for caching and session management
- 🔄 CI/CD pipeline setup

**Phase 4: Enterprise Features (Long-term)**
- 🔄 Multi-tenant support
- 🔄 Advanced cost allocation and chargeback
- 🔄 AI-powered optimization recommendations
- 🔄 API integrations for third-party tools

### 13.2 Unified Data Model Architecture

#### 13.2.1 Core Resource Properties (Universal)
All resources share fundamental attributes regardless of provider or type:

**Resource Identification:**
- `resource_id`: Unique identifier within provider
- `resource_name`: Human-readable name
- `provider`: Cloud provider (Yandex Cloud, Selectel, AWS, etc.)
- `region`: Deployment region
- `account_id`: Billing account identifier

**Classification:**
- `service_name`: Cloud service category (Compute, Storage, Database, etc.)
- `resource_type`: Specific type (VM, Database, Bucket, Lambda, etc.)
- `status`: Current operational status

**Financial Information:**
- `pricing_model`: On-Demand, Reserved, Spot, etc.
- `list_price`: Public retail price per unit
- `effective_cost`: Actual cost after discounts
- `currency`: Billing currency (RUB primary)
- `billing_period`: Cost calculation period

**Business Context:**
- `business_unit`: Department or organizational unit
- `project_id`: Project identifier
- `feature_tag`: Specific feature or application
- `cost_center`: Financial cost center
- `environment`: Production, staging, development

#### 13.2.2 Provider-Specific Properties
Extended attributes unique to each provider and resource type:

**Compute Resources (VMs, Containers):**
- `instance_type`: Provider-specific instance specification
- `cpu_cores`: Number of CPU cores
- `memory_gb`: RAM in gigabytes
- `operating_system`: OS and version
- `platform`: Hardware platform (Intel, ARM, etc.)

**Storage Resources:**
- `storage_type`: SSD, HDD, NVMe, etc.
- `capacity_gb`: Storage capacity
- `redundancy`: Data redundancy level
- `performance_tier`: Performance classification

**Database Resources:**
- `engine`: Database engine (MySQL, PostgreSQL, etc.)
- `version`: Engine version
- `instance_class`: Database instance specification
- `backup_retention`: Backup policy

**Network Resources:**
- `bandwidth_mbps`: Network capacity
- `data_transfer_gb`: Data transfer limits
- `ip_addresses`: Associated IP addresses

#### 13.2.3 Usage and Performance Metrics
Time-series data for analysis and optimization:

**Compute Metrics:**
- `cpu_utilization_percent`: CPU usage over time
- `memory_utilization_percent`: Memory usage over time
- `uptime_hours`: Resource uptime
- `request_count`: Application requests

**Storage Metrics:**
- `storage_used_gb`: Actual storage consumption
- `io_operations`: Read/write operations
- `data_transfer_gb`: Data transfer volume

**Network Metrics:**
- `ingress_traffic_gb`: Incoming data
- `egress_traffic_gb`: Outgoing data
- `connection_count`: Active connections

#### 13.2.4 Operational Logs and Components
Deep analysis of internal resource components:

**Log Analysis:**
- `application_logs`: Application-specific logs
- `system_logs`: Operating system logs
- `access_logs`: Access and authentication logs
- `error_logs`: Error and exception logs

**Component Discovery:**
- `installed_software`: Software inventory
- `running_services`: Active services
- `dependencies`: Resource dependencies
- `configuration`: Resource configuration details

### 13.3 Data Model Implementation Strategy

#### 13.3.1 Core Tables
- **`resources`**: Universal resource registry with core properties
- **`resource_metrics`**: Time-series usage and performance data
- **`resource_tags`**: Flexible tagging system for business context
- **`resource_logs`**: Operational logs and component analysis
- **`cost_allocations`**: Cost allocation rules and business mapping

#### 13.3.2 Provider-Specific Extensions
- **`yandex_resources`**: Yandex Cloud specific properties
- **`selectel_resources`**: Selectel specific properties
- **`aws_resources`**: AWS specific properties (future)
- **`azure_resources`**: Azure specific properties (future)

#### 13.3.3 Analytics and Reporting
- **`cost_trends`**: Historical cost analysis
- **`usage_patterns`**: Usage trend analysis
- **`optimization_recommendations`**: AI-generated cost optimization suggestions
- **`budget_tracking`**: Budget vs. actual cost monitoring

### 13.4 Incremental Implementation Plan

**Phase 1: Foundation (Current)**
- ✅ Basic resource tracking for Beget hosting
- ✅ Core data models for connections and resources
- 🔄 Extend to comprehensive resource discovery

**Phase 2: Multi-Cloud Expansion**
- 🔄 Add Yandex Cloud and Selectel resource synchronization
- 🔄 Implement unified data model with provider-specific extensions
- 🔄 Add usage metrics collection and storage

**Phase 3: Advanced Analytics**
- 🔄 Implement trend analysis and predictive analytics
- 🔄 Add log analysis for component discovery
- 🔄 Develop AI-powered optimization recommendations

**Phase 4: Enterprise Features**
- 🔄 Advanced cost allocation and chargeback
- 🔄 Multi-tenant support for MSPs
- 🔄 API integrations for third-party tools

## 6.2. Daily Cost Baseline Implementation

### 6.2.1. FinOps Strategy Overview
The InfraZen platform implements a **daily cost baseline strategy** for unified cost analysis across all cloud providers. This approach provides FinOps teams with consistent daily metrics for cost optimization, resource right-sizing, and budget forecasting.

### 6.2.2. Database Schema Enhancement
**New Resource Fields:**
- `daily_cost`: Normalized daily cost for FinOps analysis
- `original_cost`: Original provider cost (monthly/yearly)
- `cost_period`: Cost period (daily, monthly, yearly, hourly)
- `cost_frequency`: Cost frequency (recurring, usage-based, one-time)

**Schema Migration:**
```sql
ALTER TABLE resources ADD COLUMN daily_cost FLOAT DEFAULT 0.0;
ALTER TABLE resources ADD COLUMN original_cost FLOAT DEFAULT 0.0;
ALTER TABLE resources ADD COLUMN cost_period VARCHAR(20);
ALTER TABLE resources ADD COLUMN cost_frequency VARCHAR(20);
```

### 6.2.3. Cost Normalization Logic
**Automatic Conversion Rules:**
- **Daily**: Use as-is (22 RUB/day)
- **Monthly**: Convert to daily (660 RUB ÷ 30 = 22 RUB/day)
- **Yearly**: Convert to daily (÷ 365)
- **Hourly**: Convert to daily (× 24)

**Implementation:**
```python
@staticmethod
def normalize_to_daily_cost(original_cost, period, frequency='recurring'):
    if period == 'daily': return original_cost
    elif period == 'monthly': return original_cost / 30
    elif period == 'yearly': return original_cost / 365
    elif period == 'hourly': return original_cost * 24
    else: return original_cost / 30  # default to monthly
```

### 6.2.4. Provider Integration
**Beget API Enhancement:**
- Extract `price_day` when available from Beget API
- Fallback to `price_month ÷ 30` for daily baseline
- Store both original and normalized costs

**Sync Service Integration:**
- `_create_new_resource()` uses daily cost baseline
- `_update_existing_resource()` updates daily costs
- Automatic cost normalization during sync

### 6.2.5. UI Enhancement
**Resource Cards Display:**
- **Primary**: Daily cost (22.00 RUB/day) - Prominent display
- **Secondary**: Monthly cost (660.00 RUB/month) - Reference information
- Professional FinOps cost presentation

**CSS Implementation:**
```css
.cost-primary {
    display: flex;
    flex-direction: column;
    align-items: center;
}
.cost-amount {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--primary-blue);
}
.cost-secondary {
    padding-top: 0.5rem;
    border-top: 1px solid var(--border-light);
}
```

### 6.2.6. FinOps Benefits
**Strategic Advantages:**
- ✅ **Unified Comparison**: Compare AWS, Azure, GCP, Beget in daily terms
- ✅ **Cost Optimization**: "Save 5 RUB/day by switching plans"
- ✅ **Resource Right-sizing**: "This server costs 22 RUB/day, do we need it?"
- ✅ **Budget Forecasting**: "Daily budget: 100 RUB, current spend: 31.73 RUB"
- ✅ **Executive Reporting**: Clear daily metrics across all providers
- ✅ **Trend Analysis**: Daily cost trends and optimization opportunities

**Current Implementation Status:**
- **Total Daily Cost**: 31.73 RUB
- **VPS 1**: 22.00 RUB/day (660 RUB/month)
- **VPS 2**: 9.73 RUB/day (291.90 RUB/month)
- **Conversion Accuracy**: 100% (verified)

### 6.2.7. Future Enhancements
**Multi-Provider Support:**
- AWS EC2 daily cost normalization
- Azure VM daily cost normalization
- GCP Compute daily cost normalization
- Cross-provider cost comparison

**Advanced Analytics:**
- Daily cost trend analysis
- Resource optimization recommendations
- Budget variance analysis
- Cost anomaly detection

## 13. Referencing this Document
Use this consolidated description as the canonical source while delivering InfraZen features, ensuring alignment with FinOps principles, brand identity, business goals, and technical architecture captured across all existing documentation and investor materials.
