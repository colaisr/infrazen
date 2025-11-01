from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import and_
import logging

from ..interfaces import BaseRule, RuleScope, RuleCategory, RecommendationOutput
from ..normalization import normalize_resource, normalize_price_row, candidates_for_resource

from app.core.models.pricing import ProviderPrice, PriceComparisonRecommendation
from flask import current_app
from app.core.models.resource import Resource
from app.core.models.provider import CloudProvider
from app.core.models import db


class CrossProviderPriceCheckRule(BaseRule):
    @property
    def id(self) -> str:
        return "cost.price_check.cross_provider"

    @property
    def name(self) -> str:
        return "Сравнение цен между провайдерами"

    @property
    def description(self) -> str:
        return (
            "Ищет более дешёвые аналоги у других провайдеров на основе нормализованных спецификаций (vCPU, RAM, регион). "
            "При наличии данных подбирает кандидатов в нужном регионе, при отсутствии — ослабляет фильтры и даёт низкую уверенность. "
            "Сохраняет также диагностическую запись с экономией и top-2 альтернативами. Порог экономии настраивается флагами, по умолчанию 0."
        )

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COST

    @property
    def scope(self) -> RuleScope:
        return RuleScope.RESOURCE

    @property
    def resource_types(self):
        return {"server", "vm"}

    def evaluate(self, resource: Resource, context) -> List[RecommendationOutput]:
        logger = logging.getLogger(__name__)
        # Load provider code and region
        provider: Optional[CloudProvider] = CloudProvider.query.get(resource.provider_id) if resource.provider_id else None
        provider_code = provider.provider_type if provider else None
        region = getattr(resource, 'region', None)
        # Treat 'global' as no region preference
        region_prefix = None if (isinstance(region, str) and region.lower() == 'global') else ((region or '')[:2] if region else None)

        # Determine current monthly cost
        current_monthly = 0.0
        try:
            if getattr(resource, 'effective_cost', 0) and getattr(resource, 'billing_period', '') == 'monthly':
                current_monthly = float(resource.effective_cost or 0.0)
            elif getattr(resource, 'daily_cost', 0):
                current_monthly = float(resource.daily_cost or 0.0) * 30.0
        except Exception:
            current_monthly = 0.0

        # Not useful without current cost baseline
        if current_monthly <= 0:
            logger.info(
                "price_check: skip (no current cost) | res_id=%s name=%s provider=%s",
                getattr(resource, 'id', None), getattr(resource, 'resource_name', None), provider_code,
            )
            return []

        norm_res = normalize_resource(resource)
        logger.info(
            "price_check: normalized | res_id=%s name=%s vcpu=%s mem_gib=%s region=%s",
            getattr(resource, 'id', None), getattr(resource, 'resource_name', None), getattr(norm_res, 'vcpu', None), getattr(norm_res, 'memory_gib', None), region,
        )

        # Get user's enabled providers for recommendations
        from app.core.models.user_provider_preference import UserProviderPreference
        user_id = resource.user_id if hasattr(resource, 'user_id') else (provider.user_id if provider else None)
        enabled_providers = []
        
        if user_id:
            try:
                enabled_providers = UserProviderPreference.get_enabled_providers_for_user(user_id)
                logger.info(
                    "price_check: user preferences | user_id=%s enabled_providers=%s",
                    user_id, enabled_providers
                )
            except Exception as e:
                logger.warning(
                    "price_check: failed to get user preferences (defaulting to all) | user_id=%s error=%s",
                    user_id, str(e)
                )
                enabled_providers = []  # Empty list means all providers when no preferences set

        # Query candidate price rows excluding same provider to focus on cross-provider
        base_query = ProviderPrice.query.filter(ProviderPrice.cpu_cores.isnot(None), ProviderPrice.ram_gb.isnot(None))
        if provider_code:
            base_query = base_query.filter(ProviderPrice.provider != provider_code)
        
        # Filter by user's enabled providers if preferences are set
        if enabled_providers:
            base_query = base_query.filter(ProviderPrice.provider.in_(enabled_providers))
        # Narrow by specs when known to ensure relevant matches are included in the limited window
        if getattr(norm_res, 'vcpu', None) is not None:
            base_query = base_query.filter(ProviderPrice.cpu_cores == int(norm_res.vcpu))
        if getattr(norm_res, 'memory_gib', None) is not None:
            try:
                mem = float(norm_res.memory_gib)
                base_query = base_query.filter(ProviderPrice.ram_gb.between(max(0.5, mem * 0.8), mem * 1.25))
            except Exception:
                pass
        total_prices = base_query.count()
        price_query = base_query
        if region_prefix:
            price_query = price_query.filter(ProviderPrice.region.startswith(region_prefix))
        region_filtered_count = price_query.count()
        # Prefer cheaper options first
        price_query = price_query.order_by((ProviderPrice.monthly_cost==None).asc(), ProviderPrice.monthly_cost.asc())
        prices = price_query.limit(500).all()  # MVP cap
        logger.info(
            "price_check: catalog scope | res_id=%s total_prices=%s region_filtered=%s",
            getattr(resource, 'id', None), total_prices, region_filtered_count,
        )

        # If specs are unknown, relax matching and select cheapest options as low-confidence candidates
        specs_unknown = (norm_res.vcpu is None) or (norm_res.memory_gib is None)
        min_score = 0.8 if not specs_unknown else 0.0
        # Use normalized region (None when original is 'global') to avoid over-filtering
        preferred_region = getattr(norm_res, 'region', None)
        logger.info(
            "price_check: candidate_search | res_id=%s pref_region=%s min_score=%.2f",
            getattr(resource, 'id', None), preferred_region, min_score,
        )
        candidates = candidates_for_resource(
            norm_res,
            prices,
            preferred_region=preferred_region,
            region_prefix_match=True,
            min_score=min_score,
            limit=5,
        )
        if not candidates:
            logger.info(
                "price_check: no candidates for preferred region | res_id=%s pref_region=%s -> fallback to any region",
                getattr(resource, 'id', None), preferred_region,
            )
            candidates = candidates_for_resource(
                norm_res,
                prices,
                preferred_region=None,
                region_prefix_match=False,
                min_score=min_score,
                limit=5,
            )
            if not candidates:
                logger.info(
                    "price_check: no candidates | res_id=%s min_score=%.2f specs_unknown=%s",
                    getattr(resource, 'id', None), min_score, specs_unknown,
                )
                return []

        # Choose the cheapest among top scored and also collect top-2
        best_norm, best_score, best_row = None, 0.0, None
        alt_list: List[Tuple] = []
        for ns, score, row in candidates:
            alt_list.append((ns, score, row))
            if best_row is None:
                best_norm, best_score, best_row = ns, score, row
            else:
                current_best_cost = float(best_norm.monthly_cost or 1e12)
                candidate_cost = float(ns.monthly_cost or 1e12)
                if candidate_cost < current_best_cost:
                    best_norm, best_score, best_row = ns, score, row

        if best_row is None or best_norm is None:
            logger.info(
                "price_check: no best after evaluation | res_id=%s",
                getattr(resource, 'id', None),
            )
            
            return []

        # Compute savings
        rec_monthly = float(best_norm.monthly_cost or 0.0)
        if rec_monthly <= 0:
            logger.info(
                "price_check: skip (no target monthly) | res_id=%s",
                getattr(resource, 'id', None),
            )
            return []
        savings = round(max(0.0, current_monthly - rec_monthly), 2)
        # Apply configurable thresholds (default 0)
        try:
            min_abs = float(current_app.config.get('PRICE_CHECK_MIN_SAVINGS_RUB', 0) or 0)
            min_pct = float(current_app.config.get('PRICE_CHECK_MIN_SAVINGS_PERCENT', 0) or 0)
        except Exception:
            min_abs, min_pct = 0.0, 0.0
        if current_monthly > 0 and min_pct > 0:
            min_abs = max(min_abs, current_monthly * (min_pct / 100.0))
        logger.info(
            "price_check: candidate | res_id=%s best_price_id=%s score=%.2f target_monthly=%.2f current_monthly=%.2f savings=%.2f min_abs=%.2f",
            getattr(resource, 'id', None), getattr(best_row, 'id', None), best_score, rec_monthly, current_monthly, savings, min_abs,
        )
        # If savings less than threshold, still proceed (thresholds default to 0); we only log

        # Create or update a PriceComparisonRecommendation (idempotent)
        try:
            user_id = context.get('user_id') if isinstance(context, dict) else None
            if user_id:
                existing = PriceComparisonRecommendation.query.filter_by(
                    user_id=user_id,
                    current_resource_id=resource.id,
                    recommended_price_id=best_row.id,
                ).first()
                if existing is None:
                    pcr = PriceComparisonRecommendation(
                        user_id=user_id,
                        current_resource_id=resource.id,
                        recommended_price_id=best_row.id,
                        similarity_score=round(best_score * 100, 2),
                        monthly_savings=savings,
                        annual_savings=round(savings * 12.0, 2),
                        savings_percent=round((savings / current_monthly) * 100.0, 2) if current_monthly > 0 else None,
                        migration_effort='medium',
                    )
                    db.session.add(pcr)
                else:
                    existing.similarity_score = round(best_score * 100, 2)
                    existing.monthly_savings = savings
                    existing.annual_savings = round(savings * 12.0, 2)
                    existing.savings_percent = round((savings / current_monthly) * 100.0, 2) if current_monthly > 0 else None
        except Exception:
            # Non-fatal for MVP
            pass

        title = "Доступен более дешёвый аналог у другого провайдера"
        desc = (
            f"Найдено сопоставимое предложение у {best_norm.provider} ({best_norm.region or 'неизвестный регион'}) "
            f"примерно за {int(rec_monthly)} {best_norm.currency or 'RUB'}/мес. Текущая стоимость ~{int(current_monthly)} {getattr(resource, 'currency', 'RUB')}."
        )

        confidence = min(0.9, best_score)
        if specs_unknown:
            confidence = min(confidence, 0.4)

        # Prepare top-2 alternatives for insights (single card per provider)
        top2 = []
        for ns, score, row in sorted(alt_list, key=lambda t: (float(t[0].monthly_cost or 1e12)) )[:2]:
            top2.append({
                'provider': ns.provider,
                'region': ns.region,
                'sku': ns.sku_id,
                'monthly': float(ns.monthly_cost or 0.0),
                'score': round(score, 2),
                'price_id': row.id,
            })

        rec = RecommendationOutput(
            recommendation_type="price_compare_cross_provider",
            title=title,
            description=desc,
            category=RuleCategory.COST,
            severity="low",
            source=self.id,
            estimated_monthly_savings=savings,
            currency=getattr(resource, 'currency', 'RUB') or 'RUB',
            confidence_score=confidence,
            metrics_snapshot={
                "similarity": round(best_score, 2),
                "target_monthly": rec_monthly,
                "current_monthly": current_monthly,
            },
            insights={
                "recommended_provider": best_norm.provider,
                "recommended_region": best_norm.region,
                "recommended_sku": best_norm.sku_id,
                "recommended_price_id": best_row.id,
                "specs_unknown": specs_unknown,
                "top2": top2,
            },
        )
        return [rec]


RULES = [CrossProviderPriceCheckRule]



