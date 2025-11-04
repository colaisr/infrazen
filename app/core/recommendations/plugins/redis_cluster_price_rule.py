"""
Redis Managed Cluster Price Comparison Rule

Compares Yandex Managed Redis clusters with Selectel Managed Redis.
Uses Selectel unified DBaaS pricing (same as PostgreSQL/Kafka).
"""
from __future__ import annotations

import logging
import json
from typing import List

from flask import current_app

from app.core.models.resource import Resource
from app.core.models.provider import CloudProvider
from app.core.models.pricing import ProviderPrice
from app.core.models.user_provider_preference import UserProviderPreference
from app.core.models.recommendations import OptimizationRecommendation
from app.core.recommendations.interfaces import BaseRule, RuleCategory, RuleScope, RecommendationOutput

logger = logging.getLogger(__name__)


class RedisClusterPriceCheckRule(BaseRule):
    """Compare managed Redis cluster costs across providers."""
    
    @property
    def id(self) -> str:
        return "cost.price_check.redis_cluster"
    
    @property
    def name(self) -> str:
        return "Сравнение стоимости Redis кластера"
    
    @property
    def description(self) -> str:
        return "Сравнивает стоимость управляемого Redis кластера с аналогами у других провайдеров."
    
    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COST
    
    @property
    def scope(self) -> RuleScope:
        return RuleScope.RESOURCE
    
    @property
    def resource_types(self):
        return {"redis-cluster", "redis_cluster"}
    
    def applies(self, resource: Resource, context) -> bool:
        try:
            rtype = getattr(resource, 'resource_type', None) or getattr(resource, 'type', None)
        except Exception:
            rtype = None
        return rtype in self.resource_types
    
    def evaluate(self, resource: Resource, context) -> List[RecommendationOutput]:
        """Compare current Redis cluster with alternatives."""
        
        if resource.daily_cost:
            current_monthly = float(resource.daily_cost or 0) * 30.0
        else:
            current_monthly = float(resource.effective_cost or 0)
        
        if current_monthly <= 0:
            return []
        
        cfg = json.loads(resource.provider_config or '{}')
        
        total_vcpus = cfg.get('total_vcpus')
        total_ram_gb = cfg.get('total_ram_gb')
        total_storage_gb = cfg.get('total_storage_gb')
        total_hosts = cfg.get('total_hosts', 1)
        
        if not total_vcpus or not total_ram_gb or not total_storage_gb:
            return []
        
        provider = CloudProvider.query.get(resource.provider_id) if resource.provider_id else None
        provider_code = provider.provider_type if provider else None
        user_id = provider.user_id if provider else None
        
        if not provider_code or not user_id:
            return []
        
        prefs = UserProviderPreference.query.filter_by(user_id=user_id, is_enabled=True).all()
        enabled_provider_codes = {p.provider_type for p in prefs}
        
        if provider_code in enabled_provider_codes:
            enabled_provider_codes.remove(provider_code)
        
        if not enabled_provider_codes:
            return []
        
        # Check dismissed
        dismissed_providers = set()
        try:
            existing_dismissed = OptimizationRecommendation.query.filter_by(
                resource_id=resource.id,
                recommendation_type='price_compare_cross_provider',
                status='dismissed'
            ).all()
            
            for rec in existing_dismissed:
                if rec.target_provider:
                    dismissed_providers.add(rec.target_provider)
        except Exception:
            pass
        
        candidate_providers = enabled_provider_codes - dismissed_providers
        
        if not candidate_providers:
            return []
        
        cluster_zone = getattr(resource, 'region', '') or ''
        cluster_geo_prefix = cluster_zone.split('-')[0] if cluster_zone else None
        
        # Find alternatives (only Selectel offers managed Redis)
        alternatives = []
        
        for target_provider in candidate_providers:
            if target_provider == 'selectel':
                # Selectel Redis uses unified DBaaS pricing
                all_regions_query = ProviderPrice.query.filter_by(
                    provider='selectel',
                    resource_type='postgresql-cluster'  # Reuse unified DBaaS pricing
                ).with_entities(ProviderPrice.region).distinct()
                
                all_regions = [r[0] for r in all_regions_query.all()]
                
                regions = []
                if cluster_geo_prefix:
                    matching_regions = [r for r in all_regions if r.startswith(cluster_geo_prefix)]
                    regions = matching_regions if matching_regions else all_regions
                else:
                    regions = all_regions
                
                best_region_option = None
                
                for region in regions:
                    match = ProviderPrice.query.filter(
                        ProviderPrice.provider == 'selectel',
                        ProviderPrice.resource_type == 'postgresql-cluster',
                        ProviderPrice.region == region,
                        ProviderPrice.cpu_cores == total_vcpus,
                        ProviderPrice.ram_gb >= total_ram_gb,
                        ProviderPrice.storage_gb >= total_storage_gb * 0.8
                    ).order_by(ProviderPrice.monthly_cost).first()
                    
                    if match:
                        total_cost = float(match.monthly_cost) * total_hosts
                        
                        if best_region_option is None or total_cost < best_region_option['total_cost']:
                            best_region_option = {
                                'provider': 'selectel',
                                'region': region,
                                'total_cost': total_cost,
                                'provider_sku': match.provider_sku.replace('pg-', 'redis-'),
                                'config': f"{match.cpu_cores}c/{match.ram_gb:.0f}GB/{match.storage_gb:.0f}GB NVMe",
                            }
                
                if best_region_option:
                    savings = current_monthly - best_region_option['total_cost']
                    savings_pct = (savings / current_monthly * 100) if current_monthly > 0 else 0
                    
                    alternatives.append({
                        **best_region_option,
                        'savings': savings,
                        'savings_pct': savings_pct
                    })
        
        if not alternatives:
            return []
        
        alternatives.sort(key=lambda x: x['savings'], reverse=True)
        best = alternatives[0]
        
        min_abs = float(current_app.config.get('PRICE_CHECK_MIN_SAVINGS_RUB', 0) or 0)
        min_pct = float(current_app.config.get('PRICE_CHECK_MIN_SAVINGS_PERCENT', 0) or 0)
        
        if current_monthly > 0 and min_pct > 0:
            min_abs = max(min_abs, current_monthly * (min_pct / 100.0))
        
        if best['savings'] <= min_abs:
            return []
        
        cluster_name = getattr(resource, 'resource_name', 'кластер')
        
        title = "Доступен более дешёвый managed Redis у другого провайдера"
        
        desc = (
            f"Redis кластер '{cluster_name}' ({total_vcpus} vCPU, {total_ram_gb:.0f} GB RAM, {total_storage_gb:.0f} GB) "
            f"можно разместить дешевле у провайдера {best['provider']} в регионе {best['region']}. "
            f"Текущая стоимость ~{current_monthly:.0f} RUB/мес, "
            f"альтернатива ~{best['total_cost']:.0f} RUB/мес."
        )
        
        return [
            RecommendationOutput(
                recommendation_type="price_compare_cross_provider",
                title=title,
                description=desc,
                category=RuleCategory.COST,
                severity="medium",
                source=self.id,
                estimated_monthly_savings=round(best['savings'], 2),
                currency=getattr(resource, 'currency', 'RUB') or 'RUB',
                confidence_score=0.8,
                metrics_snapshot={
                    'similarity': 1.0,
                    'target_monthly': round(best['total_cost'], 2),
                    'current_monthly': round(current_monthly, 2),
                },
                insights={
                    'recommended_provider': best['provider'],
                    'recommended_sku': best['provider_sku'],
                    'recommended_region': best['region'],
                    'recommended_config': best['config'],
                }
            )
        ]


RULES = [RedisClusterPriceCheckRule]



