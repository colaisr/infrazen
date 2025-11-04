from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import time
from datetime import datetime

from app.core.models import db
from app.core.models.recommendation_settings import RecommendationRuleSetting
from flask import current_app
from app.core.models.complete_sync import CompleteSync, ProviderSyncReference
from app.core.models.resource import Resource
from app.core.models.provider import CloudProvider
from app.core.models.recommendations import OptimizationRecommendation

from .registry import RuleRegistry
from .interfaces import RecommendationOutput, RuleScope
from app.core.services.ai_text_generator import generate_recommendation_text


logger = logging.getLogger(__name__)


class RecommendationOrchestrator:
    """Runs recommendation rules after a complete sync.

    MVP: synchronous execution with resource-first pass and a global pass.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.registry = RuleRegistry()
        self.registry.discover()

    def run_for_sync(self, complete_sync_id: int) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            'complete_sync_id': complete_sync_id,
            'resource_rules_run': 0,
            'global_rules_run': 0,
            'recommendations_created': 0,
            'recommendations_updated': 0,
            'resources_processed': 0,
            'skipped_rules_disabled': 0,
            'suppressed_dismissed': 0,
            'suppressed_implemented': 0,
            'suppressed_snoozed': 0,
            'rule_timings': {},
        }

        complete_sync: Optional[CompleteSync] = CompleteSync.query.get(complete_sync_id)
        if not complete_sync:
            return {**summary, 'error': 'complete_sync_not_found'}

        # Resolve providers included in this complete sync
        provider_refs: List[ProviderSyncReference] = ProviderSyncReference.query.filter_by(
            complete_sync_id=complete_sync_id
        ).all()
        provider_ids = [ref.provider_id for ref in provider_refs if ref.provider_id]
        if not provider_ids:
            return {**summary, 'warning': 'no_providers_in_sync'}

        # Load resources for those providers
        resources: List[Resource] = Resource.query.filter(Resource.provider_id.in_(provider_ids)).all()
        summary['resources_processed'] = len(resources)

        # Build a minimal context for MVP
        context: Dict[str, Any] = {
            'user_id': complete_sync.user_id,
            'complete_sync_id': complete_sync_id,
        }

        created_count = 0
        updated_count = 0

        # Reset per-run metrics for internal counters used in _persist_output
        self._metrics = {
            'suppressed_dismissed': 0,
            'suppressed_implemented': 0,
            'suppressed_snoozed': 0,
        }

        # Resource-first pass
        resource_rules = self.registry.resource_rules()
        disabled_rules = set()
        try:
            disabled_rules = set(current_app.config.get('RECOMMENDATION_RULES_DISABLED', set()) or [])
        except Exception:
            disabled_rules = set()
        # Load DB-based rule settings
        db_settings = RecommendationRuleSetting.query.all()
        db_disabled = set()
        scoped_disabled = set()  # tuples (rule_id, provider_type)
        for s in db_settings:
            if not s.enabled:
                if s.scope == 'global':
                    db_disabled.add(s.rule_id)
                elif s.scope == 'resource':
                    scoped_disabled.add((s.rule_id, (s.provider_type or '')))
        for resource in resources:
            provider = CloudProvider.query.get(resource.provider_id) if resource.provider_id else None
            for rule in resource_rules:
                try:
                    # Feature flag: per-rule disable
                    try:
                        rule_id = getattr(rule, 'id') if isinstance(getattr(rule, 'id', None), str) else rule.id
                    except Exception:
                        rule_id = None
                    # Check config disabled
                    if rule_id and rule_id in disabled_rules:
                        summary['skipped_rules_disabled'] += 1
                        try:
                            self.logger.info(
                                "rule_skip | reason=config_disabled rule_id=%s provider=%s resource_id=%s",
                                rule_id, getattr(provider, 'provider_type', None), getattr(resource, 'id', None)
                            )
                        except Exception:
                            pass
                        continue
                    # Check DB disabled (global)
                    if rule_id and rule_id in db_disabled:
                        summary['skipped_rules_disabled'] += 1
                        try:
                            self.logger.info(
                                "rule_skip | reason=db_disabled_global rule_id=%s provider=%s resource_id=%s",
                                rule_id, getattr(provider, 'provider_type', None), getattr(resource, 'id', None)
                            )
                        except Exception:
                            pass
                        continue
                    # Check scoped disabled by provider
                    provider_code = getattr(provider, 'provider_type', None) if provider else None
                    if rule_id and (rule_id, (provider_code or '')) in scoped_disabled:
                        summary['skipped_rules_disabled'] += 1
                        try:
                            self.logger.info(
                                "rule_skip | reason=db_disabled_scoped rule_id=%s provider=%s resource_id=%s",
                                rule_id, provider_code, getattr(resource, 'id', None)
                            )
                        except Exception:
                            pass
                        continue

                    t0 = time.perf_counter()
                    created_local = 0
                    updated_local = 0
                    # First check applicability; log skip if not applicable
                    applies = False
                    try:
                        applies = rule.applies(resource, context)
                    except Exception:
                        applies = False
                    if not applies:
                        if rule_id:
                            try:
                                self.logger.info(
                                    "rule_skip | reason=not_applicable rule_id=%s provider=%s resource_id=%s rtype=%s",
                                    rule_id, provider_code, getattr(resource, 'id', None), getattr(resource, 'resource_type', None)
                                )
                            except Exception:
                                pass
                        continue

                    if rule_id:
                        try:
                            self.logger.info(
                                "rule_run_start | rule_id=%s provider=%s resource_id=%s rtype=%s",
                                rule_id, provider_code, getattr(resource, 'id', None), getattr(resource, 'resource_type', None)
                            )
                        except Exception:
                            pass

                    if applies:
                        outputs = rule.evaluate(resource, context) or []
                        for out in outputs:
                            # Backfill targeting fields if missing
                            if out.resource_id is None:
                                out.resource_id = getattr(resource, 'id', None)
                            if out.provider_id is None and provider is not None:
                                out.provider_id = provider.id
                            if out.resource_type is None:
                                out.resource_type = getattr(resource, 'resource_type', None)
                            if out.resource_name is None:
                                out.resource_name = getattr(resource, 'resource_name', None)
                            c, u = self._persist_output(out)
                            created_count += c
                            updated_count += u
                            created_local += c
                            updated_local += u
                        summary['resource_rules_run'] += 1
                    dt = time.perf_counter() - t0
                    if rule_id:
                        summary['rule_timings'][rule_id] = summary['rule_timings'].get(rule_id, 0.0) + dt
                        try:
                            self.logger.info(
                                "rule_run_end | rule_id=%s provider=%s resource_id=%s outputs=%d created=%d updated=%d duration_ms=%d",
                                rule_id, provider_code, getattr(resource, 'id', None),
                                len(outputs) if 'outputs' in locals() and isinstance(outputs, list) else 0,
                                created_local, updated_local, int(dt * 1000)
                            )
                        except Exception:
                            pass
                except Exception:
                    # Keep going even if one rule fails
                    continue

        # Global pass (single inventory view)
        global_rules = self.registry.global_rules()
        for rule in global_rules:
            try:
                # Feature flag: per-rule disable
                try:
                    rule_id = getattr(rule, 'id') if isinstance(getattr(rule, 'id', None), str) else rule.id
                except Exception:
                    rule_id = None
                if rule_id and rule_id in disabled_rules:
                    summary['skipped_rules_disabled'] += 1
                    try:
                        self.logger.info("rule_skip | reason=config_disabled_global rule_id=%s", rule_id)
                    except Exception:
                        pass
                    continue

                t0 = time.perf_counter()
                if rule_id:
                    try:
                        self.logger.info("rule_run_start | scope=global rule_id=%s inventory=%d", rule_id, len(resources))
                    except Exception:
                        pass
                outputs = rule.evaluate_global(resources, context) or []
                for out in outputs:
                    # Ensure provider/resource association for global outputs to satisfy DB constraints
                    if resources:
                        # Prefer an anchor resource from the same provider if provider_id is set
                        anchor = None
                        if out.provider_id is not None:
                            for r in resources:
                                if r.provider_id == out.provider_id:
                                    anchor = r
                                    break
                        if anchor is None:
                            anchor = resources[0]

                        if out.provider_id is None:
                            out.provider_id = anchor.provider_id
                        if out.resource_id is None:
                            out.resource_id = getattr(anchor, 'id', None)
                        if out.resource_type is None:
                            out.resource_type = getattr(anchor, 'resource_type', None)
                        if out.resource_name is None:
                            out.resource_name = getattr(anchor, 'resource_name', None)
                    c, u = self._persist_output(out)
                    created_count += c
                    updated_count += u
                summary['global_rules_run'] += 1
                dt = time.perf_counter() - t0
                if rule_id:
                    summary['rule_timings'][rule_id] = summary['rule_timings'].get(rule_id, 0.0) + dt
                    try:
                        self.logger.info(
                            "rule_run_end | scope=global rule_id=%s outputs=%d duration_ms=%d",
                            rule_id, len(outputs), int(dt * 1000)
                        )
                    except Exception:
                        pass
            except Exception:
                continue

        # Commit once at the end for performance
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            return {**summary, 'error': 'db_commit_failed'}

        summary['recommendations_created'] = created_count
        summary['recommendations_updated'] = updated_count
        # Propagate internal suppression counters
        try:
            summary['suppressed_dismissed'] += int(self._metrics.get('suppressed_dismissed', 0))
            summary['suppressed_implemented'] += int(self._metrics.get('suppressed_implemented', 0))
            summary['suppressed_snoozed'] += int(self._metrics.get('suppressed_snoozed', 0))
        except Exception:
            pass
        return summary

    # ---- Persistence helpers ----
    def _persist_output(self, out: RecommendationOutput) -> (int, int):
        """Create or update OptimizationRecommendation with provider-specific dedup.

        Dedup key: (source, resource_id, recommendation_type, target_provider, target_sku)
        If target_provider is None, falls back to resource-level dedup.
        Returns (created_count, updated_count).
        """
        try:
            # Extract target provider info from insights
            target_provider = None
            target_sku = None
            target_region = None
            
            if out.insights and isinstance(out.insights, dict):
                target_provider = out.insights.get('recommended_provider')
                target_sku = out.insights.get('recommended_sku')
                target_region = out.insights.get('recommended_region')
            
            # Build dedup query
            if out.source and out.resource_id and out.recommendation_type:
                existing = OptimizationRecommendation.query.filter_by(
                    resource_id=out.resource_id,
                    recommendation_type=out.recommendation_type,
                    source=out.source,
                )
                
                # Add provider-specific filter for cross-provider recommendations
                if target_provider and target_sku:
                    existing = existing.filter_by(
                        target_provider=target_provider,
                        target_sku=target_sku
                    )
                
                existing = existing.first()
            else:
                existing = None

            if existing is None:
                rec = OptimizationRecommendation(
                    resource_id=out.resource_id,
                    provider_id=out.provider_id,
                    recommendation_type=out.recommendation_type,
                    category=out.category.value if hasattr(out.category, 'value') else str(out.category),
                    severity=out.severity,
                    title=out.title,
                    description=out.description,
                    source=out.source,
                    resource_type=out.resource_type,
                    resource_name=out.resource_name,
                    potential_savings=out.potential_savings,
                    estimated_monthly_savings=out.estimated_monthly_savings,
                    estimated_one_time_savings=out.estimated_one_time_savings,
                    currency=out.currency,
                    confidence_score=out.confidence_score,
                    metrics_snapshot=str(out.metrics_snapshot) if out.metrics_snapshot else None,
                    insights=str(out.insights) if out.insights else None,
                    first_seen_at=datetime.utcnow(),
                    # Provider-specific tracking
                    target_provider=target_provider,
                    target_sku=target_sku,
                    target_region=target_region,
                    # Verification tracking
                    last_verified_at=datetime.utcnow(),
                    verification_fail_count=0,
                )
                db.session.add(rec)
                db.session.flush()  # Get ID before generating AI text
                
                # Generate AI text for the new recommendation
                try:
                    ai_text = generate_recommendation_text(rec.id)
                    if ai_text:
                        rec.ai_short_description = ai_text.get('short_description_html')
                        rec.ai_detailed_description = ai_text.get('detailed_description_html')
                        rec.ai_generated_at = datetime.utcnow()
                        self.logger.info(f"✓ AI text generated and stored for recommendation {rec.id}")
                except Exception as e:
                    self.logger.warning(f"Failed to generate AI text for rec {rec.id}: {e}")
                    # Non-fatal - recommendation still created without AI text
                
                return 1, 0
            else:
                # Auto-dismiss stale "seen" recommendations after 30 days
                if existing.status == 'seen' and existing.seen_at:
                    try:
                        days_seen = (datetime.utcnow() - existing.seen_at).days
                        if days_seen >= 30:
                            existing.status = 'auto_dismissed'
                            existing.dismissed_at = datetime.utcnow()
                            existing.dismissed_reason = 'Рекомендация устарела: не применена в течение 30 дней'
                            try:
                                self.logger.info(
                                    "auto_dismissed_stale | rec_id=%s resource_id=%s days_seen=%d",
                                    existing.id, existing.resource_id, days_seen
                                )
                            except Exception:
                                pass
                            return 0, 0  # Don't update, just auto-dismiss
                    except Exception:
                        pass
                
                # Suppression logic: avoid spamming dismissed/implemented unless meaningfully changed
                try:
                    significant_improvement = False
                    old = float(existing.estimated_monthly_savings or 0.0)
                    new = float(out.estimated_monthly_savings or 0.0)
                    if new > old * 1.15:  # +15% improvement threshold
                        significant_improvement = True
                except Exception:
                    significant_improvement = False

                if existing.status == 'dismissed' and existing.dismissed_at:
                    # Suppress for 60 days unless significant improvement
                    if (datetime.utcnow() - existing.dismissed_at).days < 60 and not significant_improvement:
                        try:
                            self._metrics['suppressed_dismissed'] = self._metrics.get('suppressed_dismissed', 0) + 1
                        except Exception:
                            pass
                        return 0, 0

                if existing.status == 'implemented' and existing.applied_at:
                    # Suppress for 90 days unless strong improvement (+20%)
                    try:
                        strong_improvement = float(out.estimated_monthly_savings or 0.0) > float(existing.estimated_monthly_savings or 0.0) * 1.20
                    except Exception:
                        strong_improvement = False
                    if (datetime.utcnow() - existing.applied_at).days < 90 and not strong_improvement:
                        try:
                            self._metrics['suppressed_implemented'] = self._metrics.get('suppressed_implemented', 0) + 1
                        except Exception:
                            pass
                        return 0, 0

                # Snoozed: suppress until snoozed_until is in the past
                if existing.status == 'snoozed':
                    try:
                        if existing.snoozed_until and existing.snoozed_until > datetime.utcnow():
                            try:
                                self._metrics['suppressed_snoozed'] = self._metrics.get('suppressed_snoozed', 0) + 1
                            except Exception:
                                pass
                            return 0, 0
                    except Exception:
                        # If snoozed but invalid date, suppress for safety
                        try:
                            self._metrics['suppressed_snoozed'] = self._metrics.get('suppressed_snoozed', 0) + 1
                        except Exception:
                            pass
                        return 0, 0

                # Update existing fields
                existing.title = out.title
                existing.description = out.description
                existing.severity = out.severity
                existing.category = out.category.value if hasattr(out.category, 'value') else str(out.category)
                existing.potential_savings = out.potential_savings
                existing.estimated_monthly_savings = out.estimated_monthly_savings
                existing.estimated_one_time_savings = out.estimated_one_time_savings
                existing.currency = out.currency
                existing.confidence_score = out.confidence_score
                if out.resource_name:
                    existing.resource_name = out.resource_name
                if out.resource_type:
                    existing.resource_type = out.resource_type
                if out.provider_id:
                    existing.provider_id = out.provider_id
                existing.metrics_snapshot = str(out.metrics_snapshot) if out.metrics_snapshot else existing.metrics_snapshot
                existing.insights = str(out.insights) if out.insights else existing.insights
                
                # Update verification tracking (rule regenerated this recommendation)
                existing.last_verified_at = datetime.utcnow()
                existing.verification_fail_count = 0
                
                # Update provider tracking if available
                if target_provider:
                    existing.target_provider = target_provider
                if target_sku:
                    existing.target_sku = target_sku
                if target_region:
                    existing.target_region = target_region
                
                return 0, 1
        except Exception:
            # Failed to persist this item; skip
            return 0, 0


