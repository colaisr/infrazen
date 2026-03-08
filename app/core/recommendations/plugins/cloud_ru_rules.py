"""
Cloud.ru-specific FinOps recommendation rules.

Uses CES metrics stored as tags during sync:
  cpu_avg_usage, cpu_max_usage   — ECS (VM) CPU utilization over 24 h
  net_in_avg_bps, net_out_avg_bps — ECS network throughput (bytes/sec)
  memory_usage_percent            — RDS memory utilization
  disk_util_percent               — RDS disk utilization
  storage_used_percent            — SFS Turbo storage fill %
"""
from __future__ import annotations

from typing import List, Optional
from ..interfaces import BaseRule, RuleScope, RuleCategory, RecommendationOutput


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_tags(resource) -> dict:
    try:
        return {t.tag_key: t.tag_value for t in getattr(resource, "tags", [])}
    except Exception:
        return {}


def _is_cloud_ru(resource) -> bool:
    """
    True if this resource was synced from Cloud.ru.
    Cloud.ru sync always stamps the tag cloud_ru_unified='true' on every resource
    (see cloud_ru.py plugin, _create_unified_resources_by_name).
    We use this tag instead of provider_type because the Resource DB model does
    not have a provider_type column — it lives on CloudProvider.
    """
    tags = _get_tags(resource)
    return tags.get("cloud_ru_unified") == "true"


def _get_cfg(resource) -> dict:
    try:
        cfg = resource.get_provider_config() if hasattr(resource, "get_provider_config") else None
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def _monthly_cost(resource) -> float:
    try:
        if getattr(resource, "billing_period", "") == "monthly":
            return float(getattr(resource, "effective_cost", 0) or 0)
        cost = getattr(resource, "effective_cost", None) or getattr(resource, "daily_cost", None)
        if cost:
            return float(cost) * 30.0
    except Exception:
        pass
    return 0.0


def _float_tag(tags: dict, key: str) -> Optional[float]:
    val = tags.get(key)
    if val is None:
        return None
    try:
        return float(str(val).replace("%", "").strip())
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Rule 1: CPU Oversized (avg < 5 %)
# ---------------------------------------------------------------------------

class CloudRuCpuOversizedRule(BaseRule):
    """Cloud.ru VM — CPU avg < 5 % over 24 h signals oversized instance."""

    @property
    def id(self) -> str:
        return "cost.cloud_ru.rightsize.cpu_oversized"

    @property
    def name(self) -> str:
        return "Cloud.ru: инстанс с избыточными ресурсами CPU"

    @property
    def description(self) -> str:
        return (
            "Средняя загрузка CPU за последние 24 ч ниже 5 % по данным Cloud Eye (CES). "
            "Инстанс может быть избыточным — рассмотрите переход на меньший тариф для экономии."
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

    @property
    def providers(self):
        return {"cloud-ru"}

    def applies(self, resource, context) -> bool:
        rtype = str(getattr(resource, "resource_type", "") or "").lower()
        return rtype in {"server", "vm"} and _is_cloud_ru(resource)

    def evaluate(self, resource, context) -> List[RecommendationOutput]:
        tags = _get_tags(resource)

        cpu_avg = _float_tag(tags, "cpu_avg_usage")
        if cpu_avg is None:
            return []  # No CES data — skip
        if cpu_avg >= 5.0:
            return []

        cpu_max = _float_tag(tags, "cpu_max_usage") or cpu_avg
        current_monthly = _monthly_cost(resource)
        if current_monthly <= 0:
            return []

        # Conservative 25 % savings estimate (downsizing one tier typically saves 20–40 %)
        estimated_savings = round(current_monthly * 0.25, 2)

        name = getattr(resource, "resource_name", "") or "неизвестно"

        return [
            RecommendationOutput(
                recommendation_type="rightsizing_cpu_oversized",
                title="Инстанс избыточен по CPU — рекомендуется уменьшить тариф",
                description=(
                    f"VM «{name}»: средняя загрузка CPU за 24 ч — {cpu_avg:.1f}% "
                    f"(пик — {cpu_max:.1f}%). "
                    "Это значительно ниже порога эффективности (5 %). "
                    "Переход на инстанс с меньшим числом vCPU позволит сократить расходы "
                    f"приблизительно на {estimated_savings:.0f} ₽/мес."
                ),
                category=RuleCategory.COST,
                severity="medium",
                source=self.id,
                estimated_monthly_savings=estimated_savings,
                currency=getattr(resource, "currency", "RUB") or "RUB",
                confidence_score=0.75,
                metrics_snapshot={
                    "cpu_avg_percent": cpu_avg,
                    "cpu_max_percent": cpu_max,
                    "window_hours": 24,
                },
                insights={
                    "threshold_pct": 5.0,
                    "action": "downsize",
                    "current_monthly_cost": current_monthly,
                },
            )
        ]


# ---------------------------------------------------------------------------
# Rule 2: CPU Undersized (avg > 85 %)
# ---------------------------------------------------------------------------

class CloudRuCpuUndersizedRule(BaseRule):
    """Cloud.ru VM — CPU avg > 85 % signals undersized instance (reliability risk)."""

    @property
    def id(self) -> str:
        return "cost.cloud_ru.rightsize.cpu_undersized"

    @property
    def name(self) -> str:
        return "Cloud.ru: инстанс с недостаточными ресурсами CPU"

    @property
    def description(self) -> str:
        return (
            "Средняя загрузка CPU за последние 24 ч превышает 85 % по данным Cloud Eye (CES). "
            "Инстанс работает на пределе — возможны деградация производительности и сбои. "
            "Рассмотрите переход на тариф с большим числом vCPU."
        )

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.RELIABILITY

    @property
    def scope(self) -> RuleScope:
        return RuleScope.RESOURCE

    @property
    def resource_types(self):
        return {"server", "vm"}

    @property
    def providers(self):
        return {"cloud-ru"}

    def applies(self, resource, context) -> bool:
        rtype = str(getattr(resource, "resource_type", "") or "").lower()
        return rtype in {"server", "vm"} and _is_cloud_ru(resource)

    def evaluate(self, resource, context) -> List[RecommendationOutput]:
        tags = _get_tags(resource)

        cpu_avg = _float_tag(tags, "cpu_avg_usage")
        if cpu_avg is None:
            return []
        if cpu_avg < 85.0:
            return []

        cpu_max = _float_tag(tags, "cpu_max_usage") or cpu_avg
        name = getattr(resource, "resource_name", "") or "неизвестно"

        # Severity escalates when max is also very high
        severity = "critical" if cpu_max >= 95.0 else "high"

        return [
            RecommendationOutput(
                recommendation_type="rightsizing_cpu_undersized",
                title="Инстанс перегружен по CPU — риск деградации производительности",
                description=(
                    f"VM «{name}»: средняя загрузка CPU за 24 ч — {cpu_avg:.1f}% "
                    f"(пик — {cpu_max:.1f}%). "
                    "При постоянной нагрузке выше 85 % возможны задержки, таймауты "
                    "и аварийные остановки. Рекомендуется увеличить число vCPU."
                ),
                category=RuleCategory.RELIABILITY,
                severity=severity,
                source=self.id,
                estimated_monthly_savings=0.0,
                currency=getattr(resource, "currency", "RUB") or "RUB",
                confidence_score=0.85,
                metrics_snapshot={
                    "cpu_avg_percent": cpu_avg,
                    "cpu_max_percent": cpu_max,
                    "window_hours": 24,
                },
                insights={
                    "threshold_pct": 85.0,
                    "action": "upsize",
                },
            )
        ]


# ---------------------------------------------------------------------------
# Rule 3: Idle / Zombie VM (CPU < 2 % + near-zero network)
# ---------------------------------------------------------------------------

class CloudRuIdleVmRule(BaseRule):
    """
    Cloud.ru VM — CPU avg < 2 % AND network throughput ≈ 0 for 24 h.
    Indicates a zombie instance that is running but not serving any workload.
    """

    # Network threshold: < 10 KB/s considered idle
    _NET_IDLE_BPS = 10 * 1024  # 10 240 B/s

    @property
    def id(self) -> str:
        return "cost.cloud_ru.cleanup.idle_vm"

    @property
    def name(self) -> str:
        return "Cloud.ru: простаивающий (zombie) инстанс"

    @property
    def description(self) -> str:
        return (
            "VM работает, но за последние 24 ч практически не использует CPU (<2 %) "
            "и не имеет сетевого трафика (<10 КБ/с). "
            "Такие инстансы («зомби») зря расходуют бюджет — рекомендуется остановить или удалить."
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

    @property
    def providers(self):
        return {"cloud-ru"}

    def applies(self, resource, context) -> bool:
        rtype = str(getattr(resource, "resource_type", "") or "").lower()
        return rtype in {"server", "vm"} and _is_cloud_ru(resource)

    def evaluate(self, resource, context) -> List[RecommendationOutput]:
        tags = _get_tags(resource)

        cpu_avg = _float_tag(tags, "cpu_avg_usage")
        if cpu_avg is None:
            return []  # No CES data
        if cpu_avg >= 2.0:
            return []

        # Exclude k8s CCE worker nodes that weren't merged into a cluster resource.
        # Cloud.ru CCE worker VMs have '-cce-' or 'cce-mgmt' in their names.
        name = getattr(resource, "resource_name", "") or ""
        name_l = name.lower()
        if "-cce-" in name_l or "-nodepool-" in name_l or "cce-mgmt" in name_l:
            return []
        cfg = _get_cfg(resource)
        if str(cfg.get("unified_display_type", "")).lower() == "kubernetes-cluster":
            return []

        # Require network data to be present to avoid false positives on
        # VMs where we have CPU metrics but no network metrics
        net_in = _float_tag(tags, "net_in_avg_bps")
        net_out = _float_tag(tags, "net_out_avg_bps")
        if net_in is None and net_out is None:
            # No network data — still flag but with lower confidence
            confidence = 0.6
            net_desc = "сетевые метрики недоступны"
        else:
            net_in = net_in or 0.0
            net_out = net_out or 0.0
            if net_in >= self._NET_IDLE_BPS or net_out >= self._NET_IDLE_BPS:
                return []  # Has network activity — not idle
            confidence = 0.82
            net_in_kb = net_in / 1024
            net_out_kb = net_out / 1024
            net_desc = f"сеть: ↓{net_in_kb:.1f} / ↑{net_out_kb:.1f} КБ/с"

        current_monthly = _monthly_cost(resource)
        if current_monthly <= 0:
            return []

        name = getattr(resource, "resource_name", "") or "неизвестно"

        return [
            RecommendationOutput(
                recommendation_type="cleanup_idle_vm",
                title="Простаивающий инстанс — рассмотрите остановку или удаление",
                description=(
                    f"VM «{name}» работает, однако за 24 ч почти не используется: "
                    f"CPU avg {cpu_avg:.1f}%, {net_desc}. "
                    f"Это признак «zombie»-инстанса. Остановка высвободит "
                    f"~{current_monthly:.0f} ₽/мес, удаление — полностью исключит расходы."
                ),
                category=RuleCategory.COST,
                severity="high",
                source=self.id,
                estimated_monthly_savings=current_monthly,
                currency=getattr(resource, "currency", "RUB") or "RUB",
                confidence_score=confidence,
                metrics_snapshot={
                    "cpu_avg_percent": cpu_avg,
                    "net_in_avg_bps": net_in if net_in is not None else None,
                    "net_out_avg_bps": net_out if net_out is not None else None,
                    "window_hours": 24,
                },
                insights={
                    "action": "stop_or_delete",
                    "current_monthly_cost": current_monthly,
                },
            )
        ]


# ---------------------------------------------------------------------------
# Rule 4: Unattached Block Volume
# ---------------------------------------------------------------------------

class CloudRuUnattachedVolumeRule(BaseRule):
    """
    Cloud.ru Volume — standalone billing group with no server component.
    Indicates a detached EVS disk that is still incurring charges.
    """

    @property
    def id(self) -> str:
        return "cost.cloud_ru.cleanup.unattached_volume"

    @property
    def name(self) -> str:
        return "Cloud.ru: неприкреплённый диск (EVS)"

    @property
    def description(self) -> str:
        return (
            "Блочный диск (EVS) тарифицируется, но не привязан ни к одной виртуальной машине. "
            "Неиспользуемые диски рекомендуется удалить или создать снапшот и удалить."
        )

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COST

    @property
    def scope(self) -> RuleScope:
        return RuleScope.RESOURCE

    @property
    def resource_types(self):
        return {"volume"}

    @property
    def providers(self):
        return {"cloud-ru"}

    def applies(self, resource, context) -> bool:
        rtype = str(getattr(resource, "resource_type", "") or "").lower()
        return rtype == "volume" and _is_cloud_ru(resource)

    def evaluate(self, resource, context) -> List[RecommendationOutput]:
        cfg = _get_cfg(resource)

        # Only act on unified Cloud.ru resources (billing-first)
        if not cfg.get("unified"):
            return []

        # Check that every billing component is a volume type (no server)
        components = cfg.get("components", [])
        if not components:
            return []

        has_server = any(
            str(c.get("type", "")).lower() in {"server", "vm"}
            for c in components
        )
        if has_server:
            return []

        # Skip Kubernetes PVC aggregates (managed by k8s)
        grouping_key = str(cfg.get("grouping_key", ""))
        if grouping_key == "k8s-persistent-volumes" or grouping_key.startswith("k8s:"):
            return []

        # Skip file storage — SFS Turbo is a shared filesystem, not a disk
        display_type = str(cfg.get("unified_display_type", "")).lower()
        if display_type == "file_storage":
            return []

        # Skip image templates (IMS) — volumes linked to system images
        # Skip RDS storage components — these are database disks, not orphaned EVS
        all_servnames = " ".join(
            str(c.get("servname", "")).lower() for c in components
        )
        if any(kw in all_servnames for kw in ("образами", "ims", "рбд", "rds postgresql", "rds mysql")):
            return []

        # Skip resources whose name looks like an image template or RDS cluster
        rname_l = str(getattr(resource, "resource_name", "") or "").lower()
        if rname_l.endswith("-template") or "template" in rname_l:
            return []

        # Skip CCE (Kubernetes) worker node system disks — they are the OS/data disks of k8s nodes
        # and should not be treated as orphaned volumes even if they have no explicit VM component.
        # Naming pattern: *workers*-cce* (e.g. vm-sdp-workers1-cce-mgmt-shared-shared-u92rt)
        if "workers" in rname_l and "cce" in rname_l:
            return []
        # Also catch istio / any *-nodepool-* volumes that slipped through grouping
        if "-nodepool-" in rname_l or rname_l.startswith("pvc-"):
            return []

        current_monthly = _monthly_cost(resource)
        if current_monthly < 5.0:
            return []

        name = getattr(resource, "resource_name", "") or "неизвестно"

        # Try to get disk size for description
        size_info = ""
        for c in components:
            cname = str(c.get("resource_name", "") or "")
            if cname:
                size_info = f" ({cname})"
                break

        return [
            RecommendationOutput(
                recommendation_type="cleanup_unattached_volume",
                title="Неприкреплённый диск — тарифицируется без использования",
                description=(
                    f"Диск «{name}»{size_info} не привязан ни к одной VM и "
                    f"продолжает тарифицироваться (~{current_monthly:.0f} ₽/мес). "
                    "Создайте снапшот данных при необходимости, затем удалите диск."
                ),
                category=RuleCategory.COST,
                severity="medium",
                source=self.id,
                estimated_monthly_savings=current_monthly,
                currency=getattr(resource, "currency", "RUB") or "RUB",
                confidence_score=0.80,
                metrics_snapshot={
                    "component_count": len(components),
                    "has_server_component": False,
                },
                insights={
                    "action": "snapshot_and_delete",
                    "current_monthly_cost": current_monthly,
                },
            )
        ]


# ---------------------------------------------------------------------------
# Rule 5: Idle / Orphaned EIP (standalone network charge)
# ---------------------------------------------------------------------------

class CloudRuIdleEipRule(BaseRule):
    """
    Cloud.ru Network resource — standalone EIP/bandwidth charge with no
    associated VM component.  Likely an orphaned public IP or unused
    bandwidth reservation.
    """

    @property
    def id(self) -> str:
        return "cost.cloud_ru.cleanup.idle_eip"

    @property
    def name(self) -> str:
        return "Cloud.ru: неиспользуемый публичный IP / EIP"

    @property
    def description(self) -> str:
        return (
            "Зарезервированный публичный IP-адрес (EIP) или полоса пропускания тарифицируется "
            "и не ассоциирован ни с одной виртуальной машиной. "
            "Освобождение снизит расходы."
        )

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COST

    @property
    def scope(self) -> RuleScope:
        return RuleScope.RESOURCE

    @property
    def resource_types(self):
        return {"network"}

    @property
    def providers(self):
        return {"cloud-ru"}

    def applies(self, resource, context) -> bool:
        rtype = str(getattr(resource, "resource_type", "") or "").lower()
        return rtype == "network" and _is_cloud_ru(resource)

    def evaluate(self, resource, context) -> List[RecommendationOutput]:
        cfg = _get_cfg(resource)

        if not cfg.get("unified"):
            return []

        components = cfg.get("components", [])
        if not components:
            return []

        # Skip if any component has a server attached (EIP is in use)
        has_server = any(
            str(c.get("type", "")).lower() in {"server", "vm"}
            for c in components
        )
        if has_server:
            return []

        resource_name = str(getattr(resource, "resource_name", "") or "")
        rname_l = resource_name.lower()
        servname = str(cfg.get("servname", "")).lower()

        # Skip shared VPC infrastructure — these are always in use:
        # VPC bandwidth pools (vpcbw-*, VPC-*-BW), NAT Gateways, pfSense/firewall gateways
        _INFRA_PATTERNS = (
            "vpcbw-", "vpc-", "nat-gw", "nat_gw", "natgw",
            "pfsense", "firewall", "checkpoint", "gateway",
        )
        if any(rname_l.startswith(p) or p in rname_l for p in _INFRA_PATTERNS):
            return []
        # Skip VPC-* named resources (shared bandwidth pools like VPC-Dev-BW)
        if rname_l.startswith("vpc"):
            return []

        # Only flag resources that look like individual EIPs:
        # - named 'eip-*' explicitly
        # - raw UUID (unnamed/orphaned IP with no human-readable label)
        import re as _re
        is_named_eip = rname_l.startswith("eip-")
        is_uuid = bool(_re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", rname_l))
        if not (is_named_eip or is_uuid):
            return []

        # Confirm it's an EIP service charge (not a misc network line)
        is_eip_service = any(
            kw in servname
            for kw in ("eip", "доступ в интернет", "direct ip", "floating ip")
        )
        if not is_eip_service:
            return []

        current_monthly = _monthly_cost(resource)
        if current_monthly < 5.0:
            return []

        name = resource_name or "неизвестно"

        return [
            RecommendationOutput(
                recommendation_type="cleanup_idle_eip",
                title="Неиспользуемый EIP — освободите IP-адрес для экономии",
                description=(
                    f"EIP «{name}» тарифицируется (~{current_monthly:.0f} ₽/мес), "
                    "но не привязан ни к одной виртуальной машине. "
                    "Проверьте, используется ли этот адрес, и освободите его, если нет."
                ),
                category=RuleCategory.COST,
                severity="low",
                source=self.id,
                estimated_monthly_savings=current_monthly,
                currency=getattr(resource, "currency", "RUB") or "RUB",
                confidence_score=0.72,
                metrics_snapshot={
                    "component_count": len(components),
                    "has_server_component": False,
                    "servname": cfg.get("servname", ""),
                },
                insights={
                    "action": "release_eip",
                    "current_monthly_cost": current_monthly,
                },
            )
        ]


# ---------------------------------------------------------------------------
# Rule registry export
# ---------------------------------------------------------------------------

RULES = [
    CloudRuCpuOversizedRule,
    CloudRuCpuUndersizedRule,
    CloudRuIdleVmRule,
    CloudRuUnattachedVolumeRule,
    CloudRuIdleEipRule,
]
