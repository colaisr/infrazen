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
- **Provider Support:** Beget (fully implemented with official OpenAPI SDK integration), AWS, Azure, GCP, VK Cloud, Yandex Cloud, Selectel (UI ready with dynamic forms)
- **Connection Testing:** Real-time API validation using official Beget OpenAPI Python SDK with proper token-based authentication
- **Security:** Encrypted password storage, user ownership validation, authentication checks, secure edit operations
- **User Experience:** Provider pre-selection from available providers, dynamic forms that adapt to provider type, loading states, comprehensive error handling, pre-filled edit forms
- **Edit Functionality:** Settings button opens modal with pre-filled connection details, secure password handling, connection validation on updates
- **API Integration:** Uses official Beget OpenAPI Python SDK (beget-openapi-auth) for robust, maintainable API interactions

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

## 13. Referencing this Document
Use this consolidated description as the canonical source while delivering InfraZen features, ensuring alignment with FinOps principles, brand identity, business goals, and technical architecture captured across all existing documentation and investor materials.
