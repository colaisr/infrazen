# Recommendations Engine Architecture Plan

## Objectives
- Build an extensible recommendations engine that runs post main sync.
- Start with empty rule scaffolding, validate orchestration, then add first two rules.
- Ensure effortless extension by new providers, resource types, and recommendation categories.

## Key Principles
- Central recommendation module; providers focus on data ingestion only.
- Plugin-based rules with a stable interface and capability metadata.
- Hybrid processing: resource-first pass, then global pass.
- Idempotent persistence (dedup/update), lifecycle-aware status.
- Config-driven thresholds/flags, strong observability.

## Current Anchors in Codebase
- Models: `OptimizationRecommendation`, `PriceComparisonRecommendation`, `Resource`.
- API: `/api/recommendations` for listing/filtering.
- Sync: `CompleteSync` flow orchestrates provider syncs.

## Architecture Overview
- RecommendationOrchestrator (service): runs analysis for a `complete_sync_id`.
- RuleRegistry (plugin system): discovers rule classes and exposes applicability.
- Rule Interface:
  - Metadata: `id`, `name`, `category`, `severity_default`, `scope` (resource|global), `resource_types`, `providers` (optional).
  - Methods:
    - Resource scope: `applies(resource, ctx)`, `evaluate(resource, ctx)` → list of rec outputs
    - Global scope: `evaluate_global(inventory, ctx)` → list of rec outputs
- Context Providers:
  - Pricing context (prices, SKU mappings), Metrics/usage context, Inventory graph.
- Persistence Adapter:
  - Create/update recommendations with dedup key `(rule_id, resource_id/null, key_params_hash)`.

## Data Flow
1. Complete Sync completes → trigger orchestrator (MVP: synchronous call; later: async worker).
2. Orchestrator loads inventory for the user/providers changed.
3. Pass A (resource-centric): for each resource, run applicable rules from registry.
4. Pass B (global): run global rules requiring cross-resource context.
5. Persist outputs; update or dismiss obsolete recs.
6. Emit metrics/logs and return summary.

## Phased Plan

### Phase 0 – Scaffolding (no real recommendations)
- Create module `app/core/recommendations/`:
  - `orchestrator.py`: `RecommendationOrchestrator.run_for_sync(complete_sync_id)`.
  - `registry.py`: `RuleRegistry` with discovery from `app/core/recommendations/plugins/`.
  - `interfaces.py`: `BaseRule`, `RuleScope`, `RuleCategory`, `RecommendationOutput` dataclass.
  - `context.py`: builders for pricing/metrics/inventory context.
  - `persistence.py`: upsert/dedup logic to `OptimizationRecommendation` and `PriceComparisonRecommendation`.
  - `plugins/` directory with empty example rules:
    - `example_resource_rule.py` (returns debug recommendation based on resource name).
    - `example_global_rule.py` (returns debug recommendation counting resources).
- Extend providers plugin map only if needed to tag resource types consistently (no rule logic in providers).
- Wire a post-sync trigger in `CompleteSyncService` to call orchestrator after success/partial.
- Add feature flag `RECOMMENDATIONS_ENABLED` and `RECOMMENDATIONS_DEBUG_MODE` in config.

Deliverables:
- Orchestrator and registry with empty plugins.
- Post-sync trigger integrated (synchronous).
- Debug-only recommendations created to validate flow.

### Phase 1 – Validation with Debug Recommendations
- Run a complete sync on a test user with multiple providers.
- Verify orchestrator executes:
  - Resource pass touches all resources; debug recommendations created.
  - Global pass runs once; debug recommendation created.
- Validate API `/api/recommendations` returns expected debug items.
- Confirm dedup works across repeated runs; obsolete debug items can be dismissed when conditions change.
- Log timings and counts.

Exit criteria:
- End-to-end path verified: sync → orchestrator → rules → persistence → API.

### Phase 2 – First Real Recommendations (with MVP SKU normalization)
- MVP SKU Normalization (for price comparisons):
  - Define a lightweight mapping layer translating provider instance types/SKUs to a normalized shape: `{vCPU, RAM, storage_type, family_hint}` and region.
  - Heuristic equivalence scoring for cross-provider comparisons; prefer exact vCPU/RAM match within ±10%.
  - Central helper: `sku_normalize(resource, pricing_item) -> NormalizedSKU`.
- Rule A (resource-specific): Server CPU underuse last month → downsize recommendation.
  - Scope: `resource`
  - Resource types: `server`/`vm`.
  - Inputs: usage metrics (avg/percentile CPU), instance family mapping.
  - Output: estimated monthly savings by downsizing one size; confidence from variance/uptime.
- Rule B (general): Cross-provider price check and comparison.
  - Scope: `global` or `resource` with pricing context lookup.
  - Inputs: `ProviderPrice` table, MVP SKU normalization, region, performance equivalency heuristics.
  - Output: `PriceComparisonRecommendation` and/or `OptimizationRecommendation` with migration effort notes.
- Configuration:
  - Thresholds: e.g., CPU under 10% for 7 days.
  - Allowed provider candidates for price checks.

Exit criteria:
- Both rules generate sensible outputs on seed data; no duplicates; performance acceptable.
- Normalization supports at least our current providers and common VM families.

#### MVP SKU Normalizer – Detailed Spec
- Normalized shape (`NormalizedSKU`):
  - `provider`, `region`, `sku_id`
  - `vcpu` (int), `memory_gib` (float)
  - `family_hint` (string; e.g., general, compute, memory)
  - `cpu_baseline_type` (enum: standard|burstable)
  - `storage_type` (enum: none|local_ssd|network_ssd|hdd), `storage_included_gib` (float|None)
  - `network_bandwidth_gbps` (float|None)
  - Optional: `gpu_count`, `gpu_mem_gib`, `tenancy`
- Helpers:
  - `normalize_resource(resource) -> NormalizedSKU`
  - `normalize_price_row(price_row) -> NormalizedSKU`
  - `equivalence_score(a: NormalizedSKU, b: NormalizedSKU) -> float`
- Matching rules (cross-provider):
  - Base filter: same country/geo; prefer same region; allow configured region groups.
  - Score components (weights): vCPU exact match (0.5); memory within ±10% (0.3) with linear penalty; baseline compatibility (0.1); storage type compatibility (0.05); network tier similarity (0.05).
  - Threshold: accept candidates with score ≥ 0.8; break ties by lowest monthly price.
  - Exclusions: dedicated tenancy, reserved/burst credit-specific SKUs for MVP; burstable↔standard mixing penalized.
- Data sources:
  - `ProviderPrice` rows mapped to normalized fields per provider adapter.
  - Resource→SKU mapping via provider-specific hints in `resource_type`/`provider_config`.
- Tests:
  - Unit fixtures for current providers (VM families) to verify normalization fields.
  - Golden tests: same-provider downsize/resize mapping yields expected adjacent sizes.
  - Cross-provider: known equivalent pairs exceed 0.8 threshold; non-equivalents below 0.6.

### Phase 3 – Observability, Controls, Documentation
- Observability:
  - Metrics: rule executions, durations, recommendations generated/updated/dismissed.
  - Structured logs with rule_id, resource_type, provider.
- Controls:
  - Per-rule enable/disable; per-user/provider toggles.
  - Rate limiting caps per run.
- Documentation:
  - Rule authoring guide (metadata, applies/evaluate patterns, context access, persistence contract).
  - System diagram and data flow.
  - API docs for recommendations and filtering.

### Phase 4 – Deferred (Future Hardening & Roadmap)
- Note: Deferred for later; not part of the current MVP scope.
- Async execution via background worker; backoff/retry.
- History-aware rules (trends across periods).
- Security and compliance categories using same interface.
- Rule versioning and A/B evaluation.
- Expand SKU normalization to a richer library: families, burstable/base CPU, storage IOPS, network caps.

## Timeline & Milestones (updated)
- Week 1:
  - Scaffold orchestrator, registry, contexts, persistence; post-sync trigger; debug rules.
  - Exit: end-to-end debug recommendations visible via API.
- Week 2:
  - Define rule interface; implement MVP SKU normalizer; CPU underuse rule (basic thresholds).
  - Exit: downsizing recs appear with savings; normalization unit tests passing.
- Week 3:
  - Global price check rule using normalizer; dedup/lifecycle; observability and flags.
  - Admin UI: recommendations settings (global/per-resource), enable/disable scoped by provider/resource type; provider inventory of known resource types; Unrecognized Resources promote flow.
  - Exit: cross-provider comparison recs generated; metrics/logs in place; admin controls available.


## Test Plan
- Unit tests:
  - Registry discovery, rule applicability filtering, dedup key stability.
  - Persistence upsert/cleanup behavior.
  - SKU normalization helpers and equivalence scoring.
- Integration tests:
  - Complete sync triggers orchestrator; both passes create debug recs.
  - Sample rules produce expected outputs on fixtures.
  - Cross-provider comparison works on known price fixtures.
- Performance budget:
  - N resources × R rules per resource; log timings; cap per-run totals.

## Work Breakdown (Track in TODOs)
1. Draft plan (this document).
2. Define rule interface and registry design.
3. Scaffold orchestrator and empty plugins.
4. Integrate post-sync trigger.
5. Implement MVP SKU normalization helpers.
6. Implement sample CPU underuse rule.
7. Implement global price check rule using normalization.
8. Add persistence/dedup/lifecycle utilities.
9. Add observability and feature flags.
10. Document, QA, and cleanup.

## Risks & Mitigations
- SKU equivalence complexity → start with heuristic mapping; improve iteratively.
- Metrics gaps → fall back to recent period; flag low-confidence results.
- Performance under large inventories → batch, cap, async path later.

## Acceptance Criteria
- After a complete sync, the orchestrator runs both passes and persists recommendations.
- Two initial rules work and are configurable.
- SKU normalization enables meaningful cross-provider comparisons for current providers.
- Adding a new rule or provider requires only plugin additions, not core rewrites.
