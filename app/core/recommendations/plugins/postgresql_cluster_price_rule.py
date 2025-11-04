"""
PostgreSQL Managed Cluster Price Comparison Rule

Compares Yandex Managed PostgreSQL clusters with Selectel Managed PostgreSQL
"""
from __future__ import annotations

import logging
import json
from typing import List, Dict, Any, Optional

from flask import current_app

from app.core.models.resource import Resource
from app.core.models.provider import CloudProvider
from app.core.models.pricing import ProviderPrice
from app.core.models.user_provider_preference import UserProviderPreference
from app.core.models.recommendations import OptimizationRecommendation
from app.core.recommendations.interfaces import BaseRule, RuleCategory, RuleScope, RecommendationOutput

logger = logging.getLogger(__name__)


class PostgreSQLClusterPriceCheckRule(BaseRule):
    """Compare managed PostgreSQL cluster costs across providers."""
    
    @property
    def id(self) -> str:
        return "cost.price_check.postgresql_cluster"
    
    @property
    def name(self) -> str:
        return "Сравнение стоимости PostgreSQL кластера"
    
    @property
    def description(self) -> str:
        return (
            "Сравнивает стоимость управляемого PostgreSQL кластера "
            "с аналогичной конфигурацией у других провайдеров."
        )
    
    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COST
    
    @property
    def scope(self) -> RuleScope:
        return RuleScope.RESOURCE
    
    @property
    def resource_types(self):
        return {"postgresql-cluster", "postgres-cluster", "postgresql_cluster"}
    
    def applies(self, resource: Resource, context) -> bool:
        """Applies only to PostgreSQL cluster resources."""
        try:
            rtype = getattr(resource, 'resource_type', None) or getattr(resource, 'type', None)
        except Exception:
            rtype = None
        return rtype in self.resource_types
    
    def evaluate(self, resource: Resource, context) -> List[RecommendationOutput]:
        """Compare current PostgreSQL cluster with alternatives."""
        
        # Get current monthly cost
        if resource.daily_cost:
            current_monthly = float(resource.daily_cost or 0) * 30.0
        else:
            current_monthly = float(resource.effective_cost or 0)
        
        if current_monthly <= 0:
            logger.info(
                "pg_price_check: skip (no current cost) | res_id=%s name=%s",
                getattr(resource, 'id', None),
                getattr(resource, 'resource_name', 'unknown')
            )
            return []
        
        # Extract cluster configuration from provider_config
        cfg = json.loads(resource.provider_config or '{}')
        
        # Get vCPU, RAM, Storage from cluster config
        total_vcpus = cfg.get('total_vcpus')
        total_ram_gb = cfg.get('total_ram_gb')
        total_storage_gb = cfg.get('total_storage_gb')
        total_hosts = cfg.get('total_hosts', 1)
        
        # If not in summary, try to extract from cluster.config
        if not total_vcpus or not total_ram_gb or not total_storage_gb:
            cluster_config = cfg.get('cluster', {}).get('config', {})
            resources = cluster_config.get('resources', {})
            
            if resources:
                # Parse preset ID (e.g., "c3-c2-m4" = 2 vCPU, 4GB RAM)
                preset_id = resources.get('resourcePresetId', '')
                disk_size_bytes = int(resources.get('diskSize', 0))
                total_storage_gb = disk_size_bytes / (1024**3) if disk_size_bytes else 0
                
                # Parse preset format: c3-c{vcpu}-m{ram_gb}
                if preset_id:
                    parts = preset_id.split('-')
                    for part in parts:
                        if part.startswith('c') and part[1:].isdigit():
                            total_vcpus = int(part[1:])
                        elif part.startswith('m') and part[1:].isdigit():
                            total_ram_gb = int(part[1:])
        
        if not total_vcpus or not total_ram_gb or not total_storage_gb:
            logger.info(
                "pg_price_check: skip (missing specs) | res_id=%s name=%s",
                getattr(resource, 'id', None),
                getattr(resource, 'resource_name', 'unknown')
            )
            return []
        
        # Get current provider and user
        provider: Optional[CloudProvider] = CloudProvider.query.get(resource.provider_id) if resource.provider_id else None
        provider_code = provider.provider_type if provider else None
        user_id = provider.user_id if provider else None
        
        if not provider_code or not user_id:
            return []
        
        # Get enabled alternative providers
        prefs = UserProviderPreference.query.filter_by(
            user_id=user_id,
            is_enabled=True
        ).all()
        
        enabled_provider_codes = {p.provider_type for p in prefs}
        
        # Remove current provider
        if provider_code in enabled_provider_codes:
            enabled_provider_codes.remove(provider_code)
        
        if not enabled_provider_codes:
            return []
        
        # Check for previously dismissed providers
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
        
        # Filter out dismissed providers
        candidate_providers = enabled_provider_codes - dismissed_providers
        
        if not candidate_providers:
            logger.info(
                "pg_price_check: all alternatives dismissed | res_id=%s",
                getattr(resource, 'id', None)
            )
            return []
        
        # Extract cluster's geographic region (e.g., 'ru' from 'ru-central1-b')
        cluster_zone = getattr(resource, 'region', '') or ''
        cluster_geo_prefix = cluster_zone.split('-')[0] if cluster_zone else None
        
        # Find alternatives
        alternatives = []
        
        for target_provider in candidate_providers:
            if target_provider == 'selectel':
                # Get available regions for Selectel
                all_regions_query = ProviderPrice.query.filter_by(
                    provider='selectel',
                    resource_type='postgresql-cluster'
                ).with_entities(ProviderPrice.region).distinct()
                
                all_regions = [r[0] for r in all_regions_query.all()]
                
                # Prioritize matching geographic regions
                regions = []
                if cluster_geo_prefix:
                    matching_regions = [r for r in all_regions if r.startswith(cluster_geo_prefix)]
                    if matching_regions:
                        regions = matching_regions
                    else:
                        regions = all_regions
                else:
                    regions = all_regions
                
                # Find best match in each region
                best_region_option = None
                
                for region in regions:
                    # Query for closest matching configuration
                    # For databases: require equal or MORE RAM (managed services often have better specs)
                    # Allow less storage (20%) since Selectel uses local NVMe SSD vs Yandex network HDD
                    match = ProviderPrice.query.filter(
                        ProviderPrice.provider == 'selectel',
                        ProviderPrice.resource_type == 'postgresql-cluster',
                        ProviderPrice.region == region,
                        ProviderPrice.cpu_cores == total_vcpus,
                        ProviderPrice.ram_gb >= total_ram_gb,  # Equal or more RAM
                        ProviderPrice.storage_gb >= total_storage_gb * 0.8  # Allow 20% less storage (SSD vs HDD)
                    ).order_by(ProviderPrice.monthly_cost).first()
                    
                    if match:
                        # This is per-node cost in Selectel, multiply by node count to match Yandex
                        total_cost = float(match.monthly_cost) * total_hosts
                        
                        if best_region_option is None or total_cost < best_region_option['total_cost']:
                            best_region_option = {
                                'provider': 'selectel',
                                'region': region,
                                'total_cost': total_cost,
                                'provider_sku': match.provider_sku,
                                'config': f"{match.cpu_cores}c/{match.ram_gb:.0f}GB/{match.storage_gb:.0f}GB SSD",
                                'per_node_cost': float(match.monthly_cost),
                                'total_nodes': total_hosts
                            }
                
                if best_region_option:
                    savings = current_monthly - best_region_option['total_cost']
                    savings_pct = (savings / current_monthly * 100) if current_monthly > 0 else 0
                    
                    alternatives.append({
                        **best_region_option,
                        'savings': savings,
                        'savings_pct': savings_pct
                    })
            
            elif target_provider == 'beget':
                # Get available regions for Beget
                all_regions_query = ProviderPrice.query.filter_by(
                    provider='beget',
                    resource_type='postgresql-cluster'
                ).with_entities(ProviderPrice.region).distinct()
                
                all_regions = [r[0] for r in all_regions_query.all()]
                
                # Prioritize matching geographic regions
                regions = []
                if cluster_geo_prefix:
                    matching_regions = [r for r in all_regions if r.startswith(cluster_geo_prefix)]
                    if matching_regions:
                        regions = matching_regions
                    else:
                        regions = all_regions
                else:
                    regions = all_regions
                
                # Find best match in each region
                best_region_option = None
                
                for region in regions:
                    # Query for closest matching configuration
                    # Beget also uses local NVMe SSD, similar matching logic as Selectel
                    match = ProviderPrice.query.filter(
                        ProviderPrice.provider == 'beget',
                        ProviderPrice.resource_type == 'postgresql-cluster',
                        ProviderPrice.region == region,
                        ProviderPrice.cpu_cores == total_vcpus,
                        ProviderPrice.ram_gb >= total_ram_gb,  # Equal or more RAM
                        ProviderPrice.storage_gb >= total_storage_gb * 0.8  # Allow 20% less storage (SSD vs HDD)
                    ).order_by(ProviderPrice.monthly_cost).first()
                    
                    if match:
                        # Beget pricing is per-node like Selectel
                        total_cost = float(match.monthly_cost) * total_hosts
                        
                        if best_region_option is None or total_cost < best_region_option['total_cost']:
                            best_region_option = {
                                'provider': 'beget',
                                'region': region,
                                'total_cost': total_cost,
                                'provider_sku': match.provider_sku,
                                'config': f"{match.cpu_cores}c/{match.ram_gb:.0f}GB/{match.storage_gb:.0f}GB NVMe",
                                'per_node_cost': float(match.monthly_cost),
                                'total_nodes': total_hosts
                            }
                
                if best_region_option:
                    savings = current_monthly - best_region_option['total_cost']
                    savings_pct = (savings / current_monthly * 100) if current_monthly > 0 else 0
                    
                    alternatives.append({
                        **best_region_option,
                        'savings': savings,
                        'savings_pct': savings_pct
                    })
            
            # Add support for other providers here in the future
            # elif target_provider == 'yandex':
            #     ...
        
        if not alternatives:
            logger.info(
                "pg_price_check: no alternatives found | res_id=%s",
                getattr(resource, 'id', None)
            )
            return []
        
        # Sort by savings and pick the best
        alternatives.sort(key=lambda x: x['savings'], reverse=True)
        best = alternatives[0]
        
        # Check if meets minimum thresholds
        min_abs = float(current_app.config.get('PRICE_CHECK_MIN_SAVINGS_RUB', 0) or 0)
        min_pct = float(current_app.config.get('PRICE_CHECK_MIN_SAVINGS_PERCENT', 0) or 0)
        
        if current_monthly > 0 and min_pct > 0:
            min_abs = max(min_abs, current_monthly * (min_pct / 100.0))
        
        if best['savings'] <= min_abs:
            logger.info(
                "pg_price_check: skip (below threshold) | res_id=%s savings=%.2f min=%.2f",
                getattr(resource, 'id', None),
                best['savings'],
                min_abs
            )
            return []
        
        # Create recommendation
        cluster_name = getattr(resource, 'resource_name', 'кластер')
        
        title = "Доступен более дешёвый managed PostgreSQL у другого провайдера"
        
        desc = (
            f"PostgreSQL кластер '{cluster_name}' ({total_vcpus} vCPU, {total_ram_gb:.0f} GB RAM, {total_storage_gb:.0f} GB) "
            f"можно разместить дешевле у провайдера {best['provider']} в регионе {best['region']}. "
            f"Текущая стоимость ~{current_monthly:.0f} RUB/мес ({total_hosts} нод), "
            f"альтернатива ~{best['total_cost']:.0f} RUB/мес ({best['total_nodes']} нод). "
            f"⚠️ Обратите внимание: Selectel использует local NVMe SSD, Yandex — network HDD/SSD."
        )
        
        rec = RecommendationOutput(
            recommendation_type="price_compare_cross_provider",
            title=title,
            description=desc,
            category=RuleCategory.COST,
            severity="medium",
            source=self.id,
            estimated_monthly_savings=round(best['savings'], 2),
            currency=getattr(resource, 'currency', 'RUB') or 'RUB',
            confidence_score=0.75,  # Slightly lower due to storage type differences
            metrics_snapshot={
                'similarity': 0.9,  # High but not perfect due to storage type
                'target_monthly': round(best['total_cost'], 2),
                'current_monthly': round(current_monthly, 2),
                'per_node_cost_target': round(best['per_node_cost'], 2),
                'per_node_cost_current': round(current_monthly / total_hosts, 2) if total_hosts > 0 else 0,
            },
            insights={
                'recommended_provider': best['provider'],
                'recommended_sku': best['provider_sku'],
                'recommended_region': best['region'],
                'recommended_config': best['config'],
                'total_nodes': best['total_nodes'],
                'storage_note': 'Selectel uses local NVMe SSD vs Yandex network HDD/SSD',
                'alternatives': [
                    {
                        'provider': alt['provider'],
                        'region': alt['region'],
                        'monthly': round(alt['total_cost'], 2),
                        'savings': round(alt['savings'], 2),
                        'savings_pct': round(alt['savings_pct'], 1),
                        'config': alt['config']
                    }
                    for alt in alternatives[:3]
                ]
            }
        )
        
        logger.info(
            "pg_price_check: recommendation | res_id=%s target=%s savings=%.2f (%.1f%%)",
            getattr(resource, 'id', None), best['provider'], best['savings'], best['savings_pct']
        )
        
        return [rec]


RULES = [PostgreSQLClusterPriceCheckRule]

