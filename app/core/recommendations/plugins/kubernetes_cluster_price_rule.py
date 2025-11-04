from __future__ import annotations

from typing import List, Optional, Dict, Any
import logging
from flask import current_app

from ..interfaces import BaseRule, RuleScope, RuleCategory, RecommendationOutput
from app.core.models.pricing import ProviderPrice
from app.core.models.provider import CloudProvider
from app.core.models.user_provider_preference import UserProviderPreference
from app.core.models.recommendations import OptimizationRecommendation


logger = logging.getLogger(__name__)


class KubernetesClusterPriceCheckRule(BaseRule):
    """
    Сравнивает стоимость Kubernetes кластера между провайдерами.
    
    Особенности:
    - Агрегирует стоимость control plane + worker nodes + persistent volumes
    - Учитывает различия в managed vs self-hosted K8s
    - Использует данные из cluster.provider_config.worker_vms для точного расчёта
    - Сопоставляет диски по типу (HDD/SSD) для честного сравнения
    """
    
    @property
    def id(self) -> str:
        return "cost.price_check.kubernetes_cluster"

    @property
    def name(self) -> str:
        return "Сравнение цен на Kubernetes кластер"

    @property
    def description(self) -> str:
        return (
            "Сравнивает стоимость Kubernetes кластера между провайдерами. "
            "Агрегирует затраты на control plane, worker nodes и persistent volumes. "
            "Учитывает тип дисков (HDD/SSD) для точного сопоставления конфигураций."
        )

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COST

    @property
    def scope(self) -> RuleScope:
        return RuleScope.RESOURCE

    @property
    def resource_types(self):
        return {"kubernetes-cluster", "kubernetes_cluster"}

    def applies(self, resource, context) -> bool:
        """Применяется только к Kubernetes кластерам."""
        try:
            rtype = getattr(resource, 'resource_type', None) or getattr(resource, 'type', None)
        except Exception:
            rtype = None
        if rtype is None:
            return False
        rtype = str(rtype).lower().replace('-', '_')
        return rtype in {"kubernetes_cluster"}

    def evaluate(self, resource, context) -> List[RecommendationOutput]:
        """
        Сравнивает стоимость кластера с альтернативами в других провайдерах.
        """
        # Get current cluster cost
        current_monthly = 0.0
        try:
            if getattr(resource, 'effective_cost', 0) and getattr(resource, 'billing_period', '') == 'monthly':
                current_monthly = float(resource.effective_cost or 0.0)
            elif getattr(resource, 'daily_cost', 0):
                current_monthly = float(resource.daily_cost or 0.0) * 30.0
        except Exception:
            current_monthly = 0.0
        
        if current_monthly <= 0:
            logger.info(
                "k8s_price_check: skip (no cost data) | res_id=%s",
                getattr(resource, 'id', None)
            )
            return []
        
        # Extract cluster configuration
        try:
            cfg = resource.get_provider_config() if hasattr(resource, 'get_provider_config') else None
            if not isinstance(cfg, dict):
                logger.info(
                    "k8s_price_check: skip (no config) | res_id=%s",
                    getattr(resource, 'id', None)
                )
                return []
            
            worker_vms = cfg.get('worker_vms', [])
            cost_breakdown = cfg.get('cost_breakdown', {})
            
            if not worker_vms:
                logger.info(
                    "k8s_price_check: skip (no worker VMs) | res_id=%s",
                    getattr(resource, 'id', None)
                )
                return []
            
        except Exception as e:
            logger.warning("k8s_price_check: error reading config | err=%s", e)
            return []
        
        # Get current provider and user preferences
        provider: Optional[CloudProvider] = CloudProvider.query.get(resource.provider_id) if resource.provider_id else None
        provider_code = provider.provider_type if provider else None
        user_id = provider.user_id if provider else None
        
        if not provider_code or not user_id:
            return []
        
        # Get enabled alternative providers for price comparison
        prefs = UserProviderPreference.query.filter_by(
            user_id=user_id,
            is_enabled=True
        ).all()
        
        enabled_provider_codes = {p.provider_type for p in prefs}
        
        # Remove current provider from alternatives
        if provider_code in enabled_provider_codes:
            enabled_provider_codes.remove(provider_code)
        
        if not enabled_provider_codes:
            logger.info(
                "k8s_price_check: no alternative providers enabled | res_id=%s",
                getattr(resource, 'id', None)
            )
            return []
        
        # Check for dismissed recommendations to implement progressive disclosure
        dismissed_providers = set()
        try:
            existing_dismissed = OptimizationRecommendation.query.filter_by(
                resource_id=getattr(resource, 'id', None),
                source=self.id,
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
                "k8s_price_check: all alternatives dismissed | res_id=%s",
                getattr(resource, 'id', None)
            )
            return []
        
        # Calculate cost for each alternative provider
        # Prioritize regions matching the cluster's geographic location
        alternatives = []
        
        # Extract cluster's geographic region (e.g., 'ru' from 'ru-central1-b')
        cluster_zone = getattr(resource, 'region', '') or ''
        cluster_geo_prefix = cluster_zone.split('-')[0] if cluster_zone else None
        
        for target_provider in candidate_providers:
            # Estimate control plane cost based on provider
            control_plane_cost = self._estimate_control_plane_cost(
                target_provider, 
                cfg.get('etcdClusterSize', '1')
            )
            
            if control_plane_cost is None:
                # Provider doesn't support managed K8s
                continue
            
            # Get all available regions for this provider
            all_regions = self._get_available_regions(target_provider)
            
            # Prioritize matching geographic regions
            regions = []
            if cluster_geo_prefix:
                # First, try regions matching the geographic prefix
                matching_regions = [r for r in all_regions if r.startswith(cluster_geo_prefix)]
                if matching_regions:
                    regions = matching_regions
                else:
                    # Fall back to all regions if no geographic match
                    regions = all_regions
            else:
                regions = all_regions
            
            # Calculate worker nodes cost for each region and find the best
            best_region_option = None
            
            for region in regions:
                worker_nodes_cost = self._calculate_worker_nodes_cost(
                    target_provider,
                    worker_vms,
                    region=region
                )
                
                if worker_nodes_cost is None:
                    # Can't match all worker nodes in this region
                    continue
                
                # Estimate persistent volumes cost (~4 RUB/GB/month average)
                volumes_cost = len(cfg.get('csi_volumes', [])) * 4.0 * 10  # Rough estimate
                
                # Estimate load balancer cost (same across providers for equivalent services)
                # K8s load balancers are created for LoadBalancer-type services, cost is similar across providers
                # Yandex: ~40.44 ₽/day per LB = ~1,213 ₽/month
                # Selectel: Similar pricing for NLB (public IP + LB service charge)
                k8s_lb_count = cfg.get('k8s_lb_count', 0)
                lb_cost_daily = k8s_lb_count * 40.44  # Per LB cost
                lb_cost_monthly = lb_cost_daily * 30.0
                
                # Total alternative cost for this region
                total_alternative = control_plane_cost + worker_nodes_cost + volumes_cost + lb_cost_monthly
                
                if best_region_option is None or total_alternative < best_region_option['total_cost']:
                    best_region_option = {
                        'region': region,
                        'control_plane_cost': control_plane_cost,
                        'worker_nodes_cost': worker_nodes_cost,
                        'volumes_cost': volumes_cost,
                        'load_balancers_cost': lb_cost_monthly,
                        'total_cost': total_alternative
                    }
            
            # If we found a valid configuration in any region, add it
            if best_region_option:
                savings = current_monthly - best_region_option['total_cost']
                savings_pct = (savings / current_monthly * 100) if current_monthly > 0 else 0
                
                alternatives.append({
                    'provider': target_provider,
                    'region': best_region_option['region'],
                    'control_plane_cost': best_region_option['control_plane_cost'],
                    'worker_nodes_cost': best_region_option['worker_nodes_cost'],
                    'volumes_cost': best_region_option['volumes_cost'],
                    'total_cost': best_region_option['total_cost'],
                    'savings': savings,
                    'savings_pct': savings_pct
                })
        
        if not alternatives:
            logger.info(
                "k8s_price_check: no viable alternatives | res_id=%s",
                getattr(resource, 'id', None)
            )
            return []
        
        # Find the cheapest alternative
        best = min(alternatives, key=lambda x: x['total_cost'])
        
        # Skip if alternative is more expensive
        if best['savings'] <= 0:
            logger.info(
                "k8s_price_check: skip (alternative more expensive) | res_id=%s alternative=%.2f current=%.2f",
                getattr(resource, 'id', None), best['total_cost'], current_monthly
            )
            return []
        
        # Apply thresholds
        try:
            min_abs = float(current_app.config.get('PRICE_CHECK_MIN_SAVINGS_RUB', 0) or 0)
            min_pct = float(current_app.config.get('PRICE_CHECK_MIN_SAVINGS_PERCENT', 0) or 0)
        except Exception:
            min_abs, min_pct = 0.0, 0.0
        
        if current_monthly > 0 and min_pct > 0:
            min_abs = max(min_abs, current_monthly * (min_pct / 100.0))
        
        if best['savings'] < min_abs:
            logger.info(
                "k8s_price_check: skip (below threshold) | res_id=%s savings=%.2f min_required=%.2f",
                getattr(resource, 'id', None), best['savings'], min_abs
            )
            return []
        
        # Create recommendation
        cluster_name = getattr(resource, 'resource_name', 'кластер')
        total_nodes = cfg.get('total_nodes', len(worker_vms))
        total_vcpus = cfg.get('total_vcpus', sum(vm.get('vcpu', 0) for vm in worker_vms))
        total_ram = cfg.get('total_ram_gb', sum(vm.get('ram_gb', 0) for vm in worker_vms))
        
        title = "Доступен более дешёвый managed Kubernetes у другого провайдера"
        
        # Get load balancer count for display
        k8s_lb_count = cfg.get('k8s_lb_count', 0)
        lb_text = f", {k8s_lb_count} LB" if k8s_lb_count > 0 else ""
        
        desc = (
            f"Kubernetes кластер '{cluster_name}' ({total_nodes} нод, {total_vcpus} vCPU, {total_ram:.0f} GB RAM{lb_text}) "
            f"можно разместить дешевле у провайдера {best['provider']} в регионе {best['region']}. "
            f"Текущая стоимость ~{current_monthly:.0f} RUB/мес, альтернатива ~{best['total_cost']:.0f} RUB/мес. "
            f"⚠️ Миграция кластера требует тщательного планирования."
        )
        
        rec = RecommendationOutput(
            recommendation_type="price_compare_cross_provider",
            title=title,
            description=desc,
            category=RuleCategory.COST,
            severity="low",
            source=self.id,
            estimated_monthly_savings=round(best['savings'], 2),
            currency=getattr(resource, 'currency', 'RUB') or 'RUB',
            confidence_score=0.7,  # Lower confidence due to migration complexity
            metrics_snapshot={
                'similarity': 1.0,
                'target_monthly': round(best['total_cost'], 2),
                'current_monthly': round(current_monthly, 2),
                'control_plane_cost': round(best['control_plane_cost'], 2),
                'worker_nodes_cost': round(best['worker_nodes_cost'], 2),
                'volumes_cost': round(best['volumes_cost'], 2),
            },
            insights={
                'recommended_provider': best['provider'],
                'recommended_sku': 'managed-k8s-cluster',
                'recommended_region': best['region'],
                'recommended_type': 'managed_kubernetes',
                'total_nodes': total_nodes,
                'total_vcpus': total_vcpus,
                'total_ram_gb': total_ram,
                'migration_complexity': 'high',
                'alternatives': [
                    {
                        'provider': alt['provider'],
                        'region': alt['region'],
                        'monthly': round(alt['total_cost'], 2),
                        'savings': round(alt['savings'], 2),
                        'savings_pct': round(alt['savings_pct'], 1)
                    }
                    for alt in sorted(alternatives, key=lambda x: x['total_cost'])[:3]
                ]
            }
        )
        
        logger.info(
            "k8s_price_check: recommendation | res_id=%s target=%s savings=%.2f (%.1f%%)",
            getattr(resource, 'id', None), best['provider'], best['savings'], best['savings_pct']
        )
        
        return [rec]
    
    def _estimate_control_plane_cost(self, provider: str, etcd_cluster_size: str) -> Optional[float]:
        """
        Оценивает стоимость control plane для провайдера.
        
        Возвращает None если провайдер не поддерживает managed K8s.
        """
        if provider == 'selectel':
            # Selectel managed K8s pricing (verified from UI)
            # Basic (1 master): ~5,307 RUB/month
            # HA (3 masters): ~15,228 RUB/month
            try:
                masters = int(etcd_cluster_size)
            except (ValueError, TypeError):
                masters = 1
            
            if masters >= 3:
                return 15228.0  # HA configuration
            else:
                return 5307.0  # Basic configuration
        
        elif provider == 'yandex':
            # Yandex managed K8s pricing (observed)
            # Single zonal master: ~7,572 RUB/month
            # Regional HA: not commonly available in basic tier
            return 7572.0
        
        elif provider == 'beget':
            # Beget doesn't offer managed K8s
            return None
        
        else:
            # Unknown provider - no managed K8s assumption
            return None
    
    def _get_available_regions(self, provider: str) -> List[str]:
        """
        Получает список доступных регионов для провайдера.
        """
        regions = ProviderPrice.query.filter_by(
            provider=provider
        ).with_entities(ProviderPrice.region).distinct().all()
        
        return [r[0] for r in regions if r[0]]
    
    def _calculate_worker_nodes_cost(self, provider: str, worker_vms: List[Dict[str, Any]], 
                                     region: Optional[str] = None) -> Optional[float]:
        """
        Рассчитывает стоимость worker nodes в целевом провайдере и регионе.
        
        Возвращает None если не удаётся подобрать конфигурации.
        """
        total_cost = 0.0
        matched_count = 0
        
        for vm in worker_vms:
            vcpu = vm.get('vcpu')
            ram_gb = vm.get('ram_gb')
            disk_gb = vm.get('disk_gb')
            disk_type_raw = vm.get('disk_type', 'network-ssd')
            
            if not vcpu or not ram_gb or not disk_gb:
                continue
            
            # Normalize disk type for matching
            # 'network-hdd' → 'hdd'
            # 'network-ssd' → 'network_ssd'
            if 'hdd' in disk_type_raw.lower():
                normalized_type = 'hdd'
            elif 'ssd' in disk_type_raw.lower():
                normalized_type = 'network_ssd'
            else:
                normalized_type = 'network_ssd'  # Default
            
            # Find matching SKU in target provider and region
            # Use >= for storage to ensure sufficient capacity
            query = ProviderPrice.query.filter(
                ProviderPrice.provider == provider,
                ProviderPrice.cpu_cores == vcpu,
                ProviderPrice.ram_gb >= ram_gb * 0.9,
                ProviderPrice.ram_gb <= ram_gb * 1.1,
                ProviderPrice.storage_gb >= disk_gb,
                ProviderPrice.storage_type == normalized_type
            )
            
            # Filter by region if specified
            if region:
                query = query.filter(ProviderPrice.region == region)
            
            match = query.order_by(ProviderPrice.monthly_cost).first()
            
            if not match:
                # Can't match this node configuration
                logger.debug(
                    "k8s_price_check: no match for worker | provider=%s region=%s vcpu=%s ram=%s disk=%s type=%s",
                    provider, region, vcpu, ram_gb, disk_gb, normalized_type
                )
                return None  # Can't build complete alternative
            
            total_cost += float(match.monthly_cost)
            matched_count += 1
        
        if matched_count != len(worker_vms):
            # Couldn't match all nodes
            return None
        
        return total_cost


RULES = [KubernetesClusterPriceCheckRule]

