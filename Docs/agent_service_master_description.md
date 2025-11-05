# InfraZen Agent Service – Consolidated Product Description

## 1. Vision & Positioning
- **Product:** InfraZen Agent Service – conversational FinOps assistant for InfraZen.
- **Primary Promise:** Drive faster, safer cost optimization decisions via context-aware chats and auto-generated recommendations, grounded in a user’s real infrastructure, prices, and analytics.
- **Target Users:** FinOps practitioners, DevOps, engineering managers, finance stakeholders.
- **Scenarios (MVP):**
  1) Recommendation text generator (deterministic, sync)
  2) Recommendation-specific chat (context-aware, multi-modal)
  3) Analytics page chat (global insights, multi-modal)

## 2. Requirements Summary
- **Persona & Tone:** Senior FinOps with deep sysadmin understanding; balances savings, effort, and risk.
- **Data Awareness:** Per-user scoped access to resources, recommendations, snapshots, prices, analytics.
- **Tooling:** Agent must call tool-scoped, read-only APIs; future action tools gated with confirmation.
- **Multi-Model:** Pluggable LLMs via a provider abstraction; start with OpenRouter; support direct and local (Ollama/GigaChat) later.
- **Multi-Modal:** Accept pasted images/screenshots; use vision-capable models for chart/invoice/screens review.
- **Security:** Role checks, demo-user read-only, tenant isolation, audit logs, output validation.
- **Latency & Cost:** Streaming responses, timeouts, retries, cost tracking, provider fallback.
- **RAG-Ready:** Index selected reports, summaries, and safe DB views for retrieval-augmented answers.

## 3. Selected Stack (All open-source and free)
- **Service:** FastAPI (HTTP/REST + WebSocket streaming)
- **Agent Orchestration:** LangGraph (tool-using, stateful agents; MIT)
- **RAG (later phase):** LlamaIndex (MIT) or native retrievers
- **Model Abstraction:** LiteLLM (MIT) with OpenRouter adapter as default
- **Vector Store:** Chroma (Apache-2.0) initially; pgvector later for production
- **Session/Cache:** Redis or Valkey (OSS drop-in)
- **Proxy:** Nginx
- **Observability:** Prometheus + Grafana
- **Local LLM (optional):** Ollama or vLLM
- **Provider:** OpenRouter (one API, many models/providers). Reference: https://openrouter.ai/

## 4. High-Level Architecture
```
Browser (UI)  ⇄  InfraZen App (Flask)  ⇄  Agent Service (FastAPI + LangGraph)
                                         ├─ LLM Gateway (LiteLLM/OpenRouter, direct, local)
                                         ├─ Tools SDK (read-only data access via InfraZen internal APIs)
                                         ├─ Context Packs (resource, recommendation, analytics)
                                         ├─ RAG (vector DB) [later]
                                         └─ Redis/Valkey (sessions) + Storage (images)
```

### 4.1 Modules
- **API Layer:** REST endpoints for sync generations; WebSocket for chats.
- **LLM Gateway:** Provider-agnostic client with retries, fallbacks, cost/latency logging; models configurable.
- **Tools SDK:** Registry for tools with JSON schemas, rate limits, auth scopes, optional tool prompts.
- **Context Packs:** Safe, shaped snapshots of user data for scenarios (resource, rec, analytics) with minimal tokens.
- **Guardrails:** Role checks, demo read-only, PII filtering, output schema validation, audit trail.
- **RAG Pipeline (future):** Index curated content (reports, summaries, safe views) with user/tenant scoping.

## 5. Data Access & Security
- **Tool-Scoped Access (Recommended):** Agent calls internal InfraZen APIs (read-only) instead of direct DB.
  - Benefits: security, stability, performance, caching, consistent schemas.
- **Auth:** Service-to-service JWT (rotating secret); per-request user context; strict tenant isolation.
- **Roles:** Enforce InfraZen roles; demo users are read-only.
- **Auditing:** Log each tool call with inputs, outputs (truncated), cost, latency, and user context.

## 6. Scenarios & Behavior
### 6.1 Scenario 1 – AI-Generated Recommendation Texts ✅ IMPLEMENTED

**Overview:**
Replace hardcoded recommendation descriptions with AI-generated, context-aware texts that focus on economics, specs, and actionable insights. Generated once during main sync and stored in database for instant display.

**Business Logic:**
- **Trigger:** During main sync process, immediately after each recommendation is created and committed
- **Input:** `recommendation_id`
- **Output:** Two HTML-formatted texts:
  - `short_description_html` (~60-80 chars) - for collapsed card view
  - `detailed_description_html` (~200-300 chars) - replaces "Пояснения" and "Метрики" sections
- **Storage:** Stored in `optimization_recommendations` table alongside recommendation data
- **Display:** Pre-generated text rendered instantly in UI (no async loading, no token waste)
- **Fallback:** If agent fails, recommendation still created without AI text (shows original description)

#### 6.1.1 Implementation Architecture

```
Main Sync Process:
   ↓
Create Recommendation → db.session.commit()
   ↓
Call: generate_recommendation_text(rec.id)
   ↓
   ├─ HTTP POST → Agent Service (/v1/generate/recommendation-text)
   │     ↓
   │  Agent fetches data (within Flask app context):
   │     ├─ Recommendation (type, savings, target provider/SKU)
   │     ├─ Resource (specs from provider_config: vcpus, ram_gb, storage_gb)
   │     ├─ Current Provider (name, region)
   │     ├─ Parse insights & metrics (Python dict strings → JSON)
   │     ↓
   │  Route to appropriate prompt builder:
   │     ├─ Price comparison → build_recommendation_prompt()
   │     └─ Cleanup → build_cleanup_prompt()
   │     ↓
   │  Call LLM via OpenRouter (gpt-4o-mini)
   │     ↓
   │  Return JSON: {short_description_html, detailed_description_html}
   ↓
Store AI text in DB:
   rec.ai_short_description = result['short_description_html']
   rec.ai_detailed_description = result['detailed_description_html']
   rec.ai_generated_at = datetime.utcnow()
   db.session.commit()
```

#### 6.1.2 Recommendation Types & Prompts

**1. Price Comparison (Cross-Provider Migration)**

Types: `price_compare_cross_provider`, `price_compare_same_provider`

*FinOps Focus:* Economics and comparable configuration

*AI Text Format:*
- **Short:** `"{target_provider} предлагает аналог за {target_price} ₽/мес вместо текущих {current_price} ₽/мес"`
- **Detailed:** `"Экономия {savings} ₽/мес при переносе {resource_type} {resource_name} в {target_provider}. Схожая конфигурация (X CPU, Y GB RAM, Z GB HD) там стоит {target_price} ₽/мес"`

*Example:*
```
Short: selectel предлагает аналог за 5,349 ₽/мес вместо текущих 5,610 ₽/мес
Detailed: Экономия 261 ₽/мес при переносе сервера office в selectel. 
          Схожая конфигурация (4 CPU, 8.0 GB RAM, 92.0 GB HD) там стоит 5,349 ₽/мес
```

*Key Data Extraction:*
- Resource specs: `provider_config.vcpus`, `provider_config.ram_gb`, `provider_config.total_storage_gb`
- Current cost: `resource.effective_cost`
- Target cost: `insights.top2[0].monthly` or `metrics.target_monthly`
- Similarity: `metrics.similarity × 100%`

**2. Cleanup Recommendations (Resource Deletion)**

Types: `cleanup_old_snapshot`, `cleanup_unused_ip`, `cleanup_unused_volume`, `cleanup_stopped`

*FinOps Focus:* Cost elimination with delicate mention of wasted budget

*AI Text Format:*
- **Short:** `"Экономия {savings} ₽/мес при удалении неиспользуемого {resource_type}"`

- **Detailed (Snapshots & IPs with age data):**
  `"Экономия {savings} ₽/мес при удалении {resource_type} {resource_name}. {Type} не используется уже X дней (размер Y GB), за это время на него уже было потрачено {wasted} ₽."`

- **Detailed (Stopped Servers - no age data):**
  `"Экономия {savings} ₽/мес при удалении остановленного сервера {resource_name}. Сервер находится в статусе STOPPED и продолжает потреблять средства на хранение."`

*Examples:*
```
Snapshot:
  Short: Экономия 1,709 ₽/мес при удалении неиспользуемого снапшота
  Detailed: Экономия 1,709 ₽/мес при удалении снапшота gitdisk-1740816592565. 
            Снапшот не используется уже 248 дней (размер 507 GB), за это время 
            на него уже было потрачено 14,119 ₽.

IP Address:
  Short: Экономия 241 ₽/мес при удалении неиспользуемого IP-адреса
  Detailed: Экономия 241 ₽/мес при удалении IP-адреса gitlab_new. 
            IP не используется уже 547 дней, за это время на него уже было потрачено 4,394 ₽.

Stopped Server:
  Short: Экономия 1,289 ₽/мес при удалении неиспользуемого сервера
  Detailed: Экономия 1,289 ₽/мес при удалении остановленного сервера punch-dev-monitoring-1. 
            Сервер находится в статусе STOPPED и продолжает потреблять средства на хранение.
```

*Key Data Extraction:*
- Age: `insights.age_days` (available for snapshots, IPs, volumes; NOT for stopped servers)
- Size: `insights.size_gb` (for snapshots, volumes)
- Wasted amount: calculated as `(monthly_savings × age_days) / 30`
- Status: `metrics.status` (for stopped servers)

*Special Handling:*
- Stopped servers: no age/wasted data (we don't know WHEN they were stopped), focus on current status
- Concrete resource types: "Снапшот" (not "Ресурс"), "IP" (not "IP-адрес" in second sentence)
- No redundant fluff: removed "Удаление полностью исключит эти расходы" (obvious)

#### 6.1.3 Prompt Engineering Principles

**FinOps Persona:**
- 10+ years FinOps experience
- Deep sysadmin understanding
- Balances savings, implementation effort, and risks
- Professional, conversational tone (not robotic templates)

**Writing Style:**
- **Focus on Economics:** Start with savings amount, always highlighted
- **Natural Language:**
  - ✅ "при переносе" (when migrating) vs ❌ "при миграции"
  - ✅ "там стоит" (costs there) vs ❌ "стоимость составит"
  - ✅ "схожая конфигурация" (similar config) with real values in parentheses
  - ✅ "не используется" (not used) vs ❌ "существует" (exists)
- **Concrete, Not Generic:**
  - ✅ "Снапшот не используется" vs ❌ "Ресурс не используется"
  - ✅ "(4 CPU, 7 GB RAM, 105 GB HD)" vs ❌ "(CPU/RAM/HD)"
- **Delicate About Waste:**
  - ✅ "уже было потрачено" vs ❌ "потрачено впустую"
  - Only mention if age > 30 days and amount > 0
- **No Redundancy:**
  - ❌ "Удаление полностью исключит эти расходы" - removed
  - ❌ "освободит средства для более нужных задач" - removed

**HTML Formatting:**
- `<strong>` for prices, savings, wasted amounts
- `<span class='provider-name'>` for provider names
- No lists (ul/ol), only inline text
- Preserve HTML in database and render safely in UI

**Validation:**
- LLM returns clean JSON (no markdown code blocks)
- Fallback texts if LLM fails to parse or returns invalid JSON
- Error logged but sync continues (non-fatal)

#### 6.1.4 Database Schema

```sql
ALTER TABLE optimization_recommendations
ADD COLUMN ai_short_description TEXT NULL,
ADD COLUMN ai_detailed_description TEXT NULL,
ADD COLUMN ai_generated_at DATETIME NULL;
```

**Migration:** `b8136224cf9c_add_ai_text_fields_to_recommendations.py`

#### 6.1.5 Files Involved

**Main App:**
- `app/core/recommendations/orchestrator.py` - calls AI generator after rec creation (line 353-366)
- `app/core/services/ai_text_generator.py` - HTTP client for agent service
- `app/core/models/recommendations.py` - added 3 AI text columns
- `app/web/main.py` - passes `enable_ai_recommendations` and `agent_service_url` to template
- `app/config.py` - feature flags: `ENABLE_AI_RECOMMENDATIONS`, `AGENT_SERVICE_URL`
- `app/templates/recommendations.html` - passes config to JS
- `app/static/js/recommendations.js` - renders `rec.ai_short_description` and `rec.ai_detailed_description`

**Agent Service:**
- `agent_service/api/recommendations.py` - `POST /v1/generate/recommendation-text` endpoint
- `agent_service/core/recommendation_generator.py` - orchestrates data fetch + LLM call
- `agent_service/tools/data_access.py` - fetches recommendation, parses provider_config for specs
- `agent_service/llm/gateway.py` - LLM abstraction (OpenRouter, with fallback support)
- `agent_service/llm/prompts.py` - separate prompt builders:
  - `build_recommendation_prompt()` - for price comparison
  - `build_cleanup_prompt()` - for cleanup/deletion

**Utilities:**
- `scripts/generate_ai_text_for_existing.py` - backfill AI text for historical recommendations

#### 6.1.6 Performance & Cost

- **Latency:** ~2-4 seconds per recommendation during sync
- **Cost:** ~1,700 tokens per recommendation (gpt-4o-mini: ~$0.0003 per rec)
- **Optimization:** Generated once during sync, stored, reused forever (no repeated calls)
- **Token Savings vs Live Generation:** 100x+ (no regeneration on every page load)
- **Model:** `openai/gpt-4o-mini` via OpenRouter (fast, cheap, good quality)

### 6.2 Scenario 2 – Recommendation Chat (Context-Aware, Multi-Modal)
- **Session:** `user_id` + `recommendation_id` (+ provider scope)
- **Context Pack:** Recommendation + resource + top-5 alternatives, normalized spec parity, latest snapshot facts, relevant prices.
- **Tools:** get_recommendation, get_resource, get_latest_snapshot, list_top_alternatives(limit=5), estimate_migration_effort, generate_step_plan
- **Behavior:** Explain trade-offs, effort vs savings, propose staged plan; accept image pastes (screenshots, consoles).
- **Transport:** WebSocket streaming; Redis for session; transcript persisted.

### 6.3 Scenario 3 – Analytics Page Chat (Global Insights, Multi-Modal)
- **Session:** `user_id` + `time_range` + `page_context`
- **Context Pack:** KPIs, charts, cost trends, anomalies, top N recommendations; optional RAG for narrative tone.
- **Tools:** get_analytics_overview, get_cost_trends, get_service_breakdown, get_anomalies, summarize_top_recommendations
- **Behavior:** Answer questions about charts/KPIs; produce short narratives; accept pasted chart images.
- **Future:** One-click “Generate Report” (HTML/PDF) similar to sample.

## 7. Tools Catalog (v1)
- `get_user_context(user_id)` – base profile, roles, preferences (read-only)
- `get_resource(resource_id)` – spec, provider, tags, monthly cost snapshot
- `get_latest_snapshot(resource_id|provider_id)` – utilization, state changes
- `list_top_alternatives(resource_id, limit=5)` – normalized spec matching and price deltas
- `get_prices_for_skus(skus[])` – current prices with regions/currencies
- `get_recommendation(recommendation_id)` – current text, savings, classification
- `get_analytics_overview(user_id, range)` – KPIs, breakdowns, anomalies
- `estimate_migration_effort(rec|resource)` – heuristic effort score + notes
- `generate_step_plan(rec)` – ordered steps with risk flags

All tools:
- Have JSON schemas, rate limits, per-tool prompts (optional), and strict return schemas.
- Are read-only by default; action tools will require explicit user confirmation.

## 8. Prompts & Policies
- **System Persona:** “Senior FinOps with 10+ years; deep sysadmin experience; clear, concise, and actionable.”
- **Tool Prompts:** Optional preambles for each tool to guide usage and constraints.
- **Output Validation:** Structured JSON where applicable; enforce numeric formats and currency symbols.
- **Guardrails:** Avoid speculative claims; cite tool-derived facts; highlight effort/risk alongside savings.

## 9. API Surface (Initial)
- `POST /v1/generate/recommendation-text` – Sync generation for Scenario 1
- `GET /v1/chat/ws?session=...` – WebSocket chat for Scenarios 2–3 (with auth token)
- `POST /v1/chat/start` – Create chat session (scope: rec or analytics)
- `POST /v1/upload` – Image upload endpoint (multipart/base64), returns handle for multi-modal models
- `GET /v1/health` – Liveness/readiness

Notes:
- Streaming tokens over WebSocket; partial deltas + tool call events.
- Strict auth and user scoping; transcripts stored with tenant boundary.

## 10. Deployment Model
### 10.1 Same Server (Phase 1 – Fastest)
- Separate process and port (e.g., 8001), proxied at `/agent/` via Nginx.
- Independent systemd unit: `infrazen-agent.service`.
- Separate env file: `config.agent.env` (OpenRouter key, model names, InfraZen API URL, JWT secret).

### 10.2 Separate Server / K8s (Phase 2 – Scalable)
- Own CI job; horizontal scaling; Redis for sessions; Prometheus metrics.
- Same service-to-service auth and internal API contracts.

## 11. Deployment Strategy
**Current Approach (Manual):**
- Monorepo with manual deployment via `deploy.sh` script
- Supports: `./deploy.sh app`, `./deploy.sh agent`, `./deploy.sh both`
- Production-tested with zero-downtime deployments
- Works perfectly for solo/small team workflow

**CI/CD (Deferred):**
- Automated CI pipelines not implemented (over-engineering for current needs)
- Can be added later if team grows or automation requirements increase
- Would include:
  - App pipeline (Flask app)
  - Agent pipeline (Agent Service)
  - Separate secrets and environment configs

**Current Benefits:**
- Full control over deployment timing
- Simple, reliable script-based process
- No CI complexity or maintenance overhead
- Secrets managed via server environment files

## 12. Configuration Keys (Initial)
- `AGENT_PORT=8001`
- `AGENT_ENV=dev|prod`
- `AGENT_INTERNAL_API_BASE=http://127.0.0.1:5001/internal` (or service DNS)
- `AGENT_SERVICE_JWT_SECRET=...`
- `LLM_PROVIDER=openrouter|openai|anthropic|ollama|gigachat`
- `LLM_MODEL_TEXT=...` (e.g., openrouter/gpt-5)
- `LLM_MODEL_VISION=...` (e.g., openrouter/gemini-2.5-pro)
- `OPENROUTER_API_KEY=...` (if using OpenRouter)
- `REDIS_URL=redis://127.0.0.1:6379/0` (or Valkey)
- `VECTOR_STORE=chroma|pgvector`
- `LOG_LEVEL=INFO`

## 13. Observability & Cost Control
- **Metrics:** request latency, tool call counts, LLM token usage/costs, error rates, cache hit ratio.
- **Logs:** structured JSON with correlation IDs, per-tool audits.
- **Alerts:** latency spikes, tool error bursts, cost anomalies per provider/model.

## 14. Risks & Mitigations
- **Tool sprawl:** Use a curated catalog and versioning (`tool@vN`).
- **Data leakage:** Tool-scoped APIs only; enforce tenant scoping and PII filters.
- **Model variance:** Use OpenRouter routing + fallback; keep deterministic sync path for Scenario 1.
- **Latency/cost:** Streaming, caching, provider fallbacks, max tokens and timeouts.

## 15. Roadmap & Extensions
- **Short-term:** Add RAG for analytics narratives; report generator (HTML/PDF) on demand; effort estimators per resource type.
- **Mid-term:** Action tools with confirmations (e.g., create JIRA task, draft change plan docs).
- **Long-term:** Fine-tuned models, per-tenant adapters, and on-prem LLM options at scale.

---

### Appendix A – Model Strategy (Initial)
- Text + tools: GPT‑class or Claude Sonnet via OpenRouter (cost/perf tuned).
- Vision: Gemini 2.5 Pro or Sonnet Vision via OpenRouter.
- Local: Ollama profiles for dev air-gapped testing.

Reference: OpenRouter – The Unified Interface for LLMs: https://openrouter.ai/

## 16. Implementation Plan & Milestones

This section tracks execution progress. We will update checkboxes as we proceed, refine scope when discoveries occur, and clean up progress notes at the end to leave a final specification.

### Milestone 1 – Skeleton + Local/Server Validation ✅ COMPLETE
- [x] Scaffold agent_service skeleton (FastAPI, LangGraph) with:
  - [x] Health endpoint (`GET /v1/health`)
  - [x] WebSocket echo (`/v1/chat/ws`) for basic connectivity
  - ✅ **Created:** `agent_service/` directory structure with FastAPI app, health & readiness checks, WebSocket echo endpoint
- [x] Add config assets:
  - [x] `requirements-agent.txt` (FastAPI, LangGraph, LiteLLM, Redis, Chroma, etc.)
  - [x] `Dockerfile` (Python 3.10-slim with health check)
  - [x] `config.agent.env.sample` (template for all required env vars)
- [x] Minimal test UI page in the app and an app route that pings the agent
  - ✅ **Created:** `/agent-test` route in Flask app with test page for health & WebSocket testing
- [x] Local run scripts: app on 5001, agent on 8001 behind reverse proxy
  - ✅ **Created:** `run_both.sh` and `stop_both.sh` for unified local development
  - ✅ **Verified:** Both services running and healthy (agent: port 8001, app: port 5001)
- [x] Server prep:
  - [x] Nginx location `/agent/` → upstream `127.0.0.1:8001` (with WebSocket support, long timeouts)
  - [x] systemd `infrazen-agent.service` and `config.agent.env`
  - ✅ **Production:** Nginx proxying HTTPS traffic to agent on port 8001
- [x] Deploy agent locally and validate health/readiness
  - ✅ **Committed:** dec0baa - Agent Service skeleton with 23 files
  - ✅ **Pushed:** to master branch
  - ✅ **Production:** Both services running, health checks passing

Definition of done: ✅ COMPLETE - health endpoint OK, WebSocket echo works, test page shows "connected to agent", production deployment successful.

### Milestone 2 – Deployment Automation ✅ COMPLETE
- [x] Extend `deploy.sh` to support `app|agent|both` with idempotent steps and rollback
  - ✅ **Production:** Deploy script supports `./deploy.sh app|agent|both`
  - ✅ **Health Checks:** Both services have automated health validation
  - ✅ **Zero-downtime:** App uses systemctl reload, Agent restarts gracefully
  - ✅ **Tested on production:** Multiple successful deployments
- [cancelled] Add separate CI job for agent (build, push, restart) independent of app pipeline
  - **Reason:** Manual deployment via `deploy.sh` works perfectly for current workflow
  - **Future:** Can be added later if team grows or automation needs increase
- [cancelled] Wire agent secrets/env in CI without touching existing app secrets
  - **Reason:** Not needed without CI pipeline

Definition of done: ✅ COMPLETE - Manual deployment works perfectly; deploy.sh supports all scenarios; CI/CD deferred as over-engineering for solo/small team.

### Milestone 3 – Joint Deploy Test ✅ COMPLETE
- [x] Make a trivial change to both app and agent; deploy both
- [x] Verify both changes delivered and healthy without downtime
  - ✅ **Tested:** Console message in dashboard.js + message field in health endpoint
  - ✅ **Verified:** Both changes deployed successfully with `./deploy.sh both`
  - ✅ **Zero downtime:** App reloaded, agent restarted, both healthy

Definition of done: ✅ COMPLETE - both services reflect changes; clean logs; zero app downtime.

### Milestone 4 – LLM Recommendation Text (with Fallback) ✅ COMPLETE
- [x] Implement `POST /v1/generate/recommendation-text` with tool-scoped reads
  - ✅ **Tools:** Data access for recommendations, resources, providers with Python dict parsing
  - ✅ **LLM Gateway:** OpenRouter integration with gpt-4o-mini
  - ✅ **Prompts:** FinOps persona with HTML formatting, Russian language
  - ✅ **Sanitization:** Basic HTML whitelist (strong, span, em, br)
- [x] UI feature flag to switch from hardcoded text to agent output; preserve fallback
  - ✅ **Config:** ENABLE_AI_RECOMMENDATIONS and AGENT_SERVICE_URL flags
  - ✅ **UI:** Async fetch with caching, replaces short description in collapsed cards
  - ✅ **Details:** AI detailed description + "Обсудить с FinOps" button in expanded view
  - ✅ **Fallback:** Graceful degradation to original Пояснения/Метрики if AI fails
  - ✅ **Tested:** Working with gpt-4o-mini, ~830 tokens/call, correct prices and formatting
  - ✅ **Commits:** c62094e (API), c419c9f (UI)

Definition of done: ✅ COMPLETE - flag ON shows agent text with HTML formatting; OFF uses current implementation.

### Milestone 5 – Recommendation/Resource Chat
- [ ] WebSocket chat with session scoped to `recommendation_id` + user
- [ ] Tools: recommendation/resource/snapshot/alternatives/effort/steps (read-only)
- [ ] Multi-modal upload endpoint and vision model wiring for screenshots
- [ ] UI: Chat drawer on recommendation card

Definition of done: agent discusses the specific recommendation with user infra context and images.

### Milestone 6 – Analytics Chat (Global Insights)
- [ ] Tools for KPIs, trends, breakdowns, anomalies, top recommendations
- [ ] WebSocket streaming; UI entry on analytics page

Definition of done: agent answers about charts/KPIs and produces concise insights.

### Milestone 7 – AI-Generated Report
- [ ] RAG-lite on approved content; generator for HTML/PDF similar to the sample report

Definition of done: one-click report reflects current data with citations and metrics.

### Governance & Safety (Parallel, Non-Disruptive)
- [ ] Guardrails: roles, demo read-only, quotas, cost tracking, audit trail
- [ ] Observability: metrics, logs, alerts for agent (no impact to app)

Notes:
- The agent runs as a separate process, port, env, and systemd unit; the app remains untouched.
- Nginx reloads are zero-downtime; deploy script supports app-only, agent-only, or both.
- Feature flags ensure we can ship incrementally and revert safely.
- Manual deployment via `deploy.sh` provides full control without CI/CD complexity.


