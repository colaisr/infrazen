from __future__ import annotations

from typing import List, Optional
import re
from ..interfaces import BaseRule, RuleScope, RuleCategory, RecommendationOutput
from ..normalization import normalize_resource
from app.core.models.pricing import ProviderPrice
from app.core.models.provider import CloudProvider


class CpuUnderuseDownsizeRule(BaseRule):
    @property
    def id(self) -> str:
        return "cost.rightsize.cpu_underuse"

    @property
    def name(self) -> str:
        return "Оптимизация: уменьшение размера при низкой загрузке CPU"

    @property
    def description(self) -> str:
        return (
            "Рекомендует уменьшить размер инстанса при низкой средней загрузке CPU (<10%). "
            "Определяет текущий vCPU (теги/атрибуты/provider_config), пропускает инстансы с ≤1 vCPU, "
            "оценивает экономию по каталогу провайдера, подбирая ближайший тариф с vCPU на 1 ступень ниже "
            "с сопоставимой RAM (±25%) в том же регионе. Рекомендация создаётся только при реальной экономии."
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

    def applies(self, resource, context) -> bool:
        """Restrict strictly to servers/VMs regardless of registry or aliases."""
        try:
            rtype = getattr(resource, 'resource_type', None) or getattr(resource, 'type', None)
        except Exception:
            rtype = None
        if rtype is None:
            return False
        # Normalize to lowercase for safety
        rtype = str(rtype).lower()
        return rtype in {"server", "vm"}

    def evaluate(self, resource, context) -> List[RecommendationOutput]:
        # Expect CPU avg usage tag in percent (string). Fallback to 0.
        try:
            tags = {t.tag_key: t.tag_value for t in getattr(resource, 'tags', [])}
        except Exception:
            tags = {}
        
        # Skip resources that are part of aggregated services (e.g., Kubernetes nodes, CSI volumes)
        # These should be optimized at the cluster/service level, not individually
        if tags.get('is_kubernetes_node') == 'true' or tags.get('is_kubernetes_node') is True:
            return []
        
        resource_name = getattr(resource, 'resource_name', '') or ''
        
        # Skip Kubernetes CSI volumes
        if resource_name.startswith('k8s-csi-'):
            return []
        
        # Skip any resource with kubernetes cluster tag
        if tags.get('kubernetes_cluster_id'):
            return []
        
        cpu_str = tags.get('cpu_avg_usage')
        cpu_avg = 0.0
        try:
            if cpu_str is not None:
                cpu_avg = float(str(cpu_str).replace('%', '').strip())
        except (TypeError, ValueError):
            cpu_avg = 0.0

        # Threshold: < 10% monthly average considered underused (MVP)
        if cpu_avg >= 10.0:
            return []

        # Parse current vCPU count from resource/tags/provider_config; skip if 1 or less
        current_vcpu: Optional[int] = None
        # Try tag-based hint first
        try:
            if 'vcpu' in tags:
                current_vcpu = int(str(tags['vcpu']).strip())
        except Exception:
            current_vcpu = None
        # Fallback to resource attribute
        if current_vcpu is None:
            try:
                attr_vcpu = getattr(resource, 'cpu_cores', None) or getattr(resource, 'vcpu', None)
                if attr_vcpu is not None:
                    current_vcpu = int(attr_vcpu)
            except Exception:
                current_vcpu = None
        # Fallback to provider_config like "4 vCPU"
        if current_vcpu is None:
            try:
                cfg = resource.get_provider_config() if hasattr(resource, 'get_provider_config') else None
                if isinstance(cfg, dict):
                    cpu_field = cfg.get('cpu') or cfg.get('vcpu') or cfg.get('cores') or cfg.get('cpu_cores')
                    if cpu_field:
                        m = re.search(r"(\d+)", str(cpu_field))
                        if m:
                            current_vcpu = int(m.group(1))
            except Exception:
                current_vcpu = None
        if current_vcpu is not None and current_vcpu <= 1:
            return []

        # Estimate savings from provider catalog: downgrade CPU by one tier within same provider/region
        # Determine current monthly baseline
        current_monthly = 0.0
        try:
            if getattr(resource, 'effective_cost', 0) and getattr(resource, 'billing_period', '') == 'monthly':
                current_monthly = float(resource.effective_cost or 0.0)
            elif getattr(resource, 'daily_cost', 0):
                current_monthly = float(resource.daily_cost or 0.0) * 30.0
            else:
                # fallback to provider_config monthly_cost if available
                try:
                    cfg = resource.get_provider_config() if hasattr(resource, 'get_provider_config') else None
                    if isinstance(cfg, dict) and cfg.get('monthly_cost'):
                        current_monthly = float(cfg.get('monthly_cost') or 0.0)
                except Exception:
                    pass
        except Exception:
            current_monthly = 0.0

        # Query provider catalog for a cheaper instance with one fewer vCPU
        provider = CloudProvider.query.get(resource.provider_id) if getattr(resource, 'provider_id', None) else None
        provider_code = provider.provider_type if provider else None
        norm = normalize_resource(resource)
        region = getattr(resource, 'region', None)
        # Treat 'global' as no strict region filter; otherwise use region prefix
        region_prefix = None if (isinstance(region, str) and region.lower() == 'global') else ((region or '')[:2] if region else None)

        estimated_savings = 0.0
        if current_vcpu and current_vcpu > 1 and provider_code:
            target_vcpu = max(1, current_vcpu - 1)
            q = ProviderPrice.query.filter(
                ProviderPrice.provider == provider_code,
                ProviderPrice.cpu_cores == target_vcpu,
            )
            # keep RAM roughly the same (±25%, but not exceeding current)
            mem = norm.memory_gib or None
            if mem is not None:
                low = max(0.5, mem * 0.75)
                high = mem * 1.05
                q = q.filter(ProviderPrice.ram_gb.between(low, high))
            if region_prefix:
                q = q.filter(ProviderPrice.region.startswith(region_prefix))
            q = q.order_by((ProviderPrice.monthly_cost==None).asc(), ProviderPrice.monthly_cost.asc())
            candidate = q.first()
            if candidate and candidate.monthly_cost:
                rec_monthly = float(candidate.monthly_cost)
                if current_monthly > 0 and rec_monthly < current_monthly:
                    estimated_savings = round(current_monthly - rec_monthly, 2)

        # Suppress when we couldn't find a cheaper catalog option
        if estimated_savings <= 0:
            return []

        title = "Уменьшить размер инстанса из‑за низкой загрузки CPU"
        desc = (
            f"Средняя загрузка CPU составляет {cpu_avg:.1f}%. "
            f"Найден более дешёвый тариф у текущего провайдера при уменьшении vCPU."
        )

        return [
            RecommendationOutput(
                recommendation_type="rightsizing_cpu",
                title=title,
                description=desc,
                category=RuleCategory.COST,
                severity="medium",
                source=self.id,
                estimated_monthly_savings=estimated_savings,
                currency=getattr(resource, 'currency', 'RUB') or 'RUB',
                confidence_score=0.7,
                metrics_snapshot={"cpu_avg_percent": cpu_avg, "current_vcpu": current_vcpu},
                insights={"current_monthly_cost": current_monthly, "suggested_reduction": 0.5},
            )
        ]


RULES = [CpuUnderuseDownsizeRule]




