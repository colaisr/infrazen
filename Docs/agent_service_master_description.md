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
### 6.1 Scenario 1 – Recommendation Text Generator (Sync)
- **Input:** `resource_id` (+ optional `target_provider` or candidate SKUs)
- **Tools:** get_resource, get_prices_for_candidates, get_latest_snapshot
- **Output:** Structured JSON + friendly text (title, summary, details, monthly and yearly savings, effort score, risks)
- **Latency Target:** 2–4 seconds; caching by (resource + candidate set); invalidate on price/snapshot changes.

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

## 11. CI/CD
- Monorepo with two pipelines:
  - App pipeline (Flask app)
  - Agent pipeline (Agent Service)
- Dev convenience: combined “deploy both” path.
- Version independently; shared changelog sections.
- Secrets via environment (server), not in repo.

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

### Milestone 1 – Skeleton + Local/Server Validation
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
- [ ] Server prep:
  - [ ] Nginx location `/agent/` → upstream `127.0.0.1:8001`
  - [ ] systemd `infrazen-agent.service` and `config.agent.env`
- [ ] Deploy agent safely (no impact to app) and validate health/readiness

Definition of done: health endpoint OK, WebSocket echo works, test page shows “connected to agent”.

### Milestone 2 – CI/CD for Agent (No Impact to App)
- [ ] Extend `deploy.sh` to support `app|agent|both` with idempotent steps and rollback
- [ ] Add separate CI job for agent (build, push, restart) independent of app pipeline
- [ ] Wire agent secrets/env in CI without touching existing app secrets

Definition of done: pushing an agent-only change deploys agent; app pipeline remains unchanged.

### Milestone 3 – Joint Deploy Test
- [ ] Make a trivial change to both app and agent; deploy both
- [ ] Verify both changes delivered and healthy without downtime

Definition of done: both services reflect changes; clean logs; zero app downtime.

### Milestone 4 – LLM Recommendation Text (with Fallback)
- [ ] Implement `POST /v1/generate/recommendation-text` with tool-scoped reads
- [ ] UI feature flag to switch from hardcoded text to agent output; preserve fallback

Definition of done: flag ON shows agent text (savings/effort/risks); OFF uses current implementation.

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
- CI/CD adds an isolated path for the agent; the app pipeline remains intact.


