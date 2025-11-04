from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
import re


@dataclass
class NormalizedSKU:
    provider: str
    region: Optional[str]
    sku_id: Optional[str]

    vcpu: Optional[int]
    memory_gib: Optional[float]

    family_hint: Optional[str] = None  # general|compute|memory|gpu|storage
    cpu_baseline_type: Optional[str] = None  # standard|burstable
    storage_type: Optional[str] = None  # none|local_ssd|network_ssd|hdd
    storage_included_gib: Optional[float] = None
    network_bandwidth_gbps: Optional[float] = None

    gpu_count: Optional[int] = None
    gpu_mem_gib: Optional[float] = None
    tenancy: Optional[str] = None

    monthly_cost: Optional[float] = None
    currency: Optional[str] = None


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_price_row(price_row: Any) -> NormalizedSKU:
    """Normalize a ProviderPrice ORM row into a NormalizedSKU.

    Expects fields similar to app.core.models.pricing.ProviderPrice
    """
    ext_raw = getattr(price_row, 'extended_specs', None) or {}
    # Handle JSON string (MySQL JSON column might return as string)
    if isinstance(ext_raw, str):
        import json
        try:
            ext = json.loads(ext_raw) if ext_raw else {}
        except (json.JSONDecodeError, TypeError):
            ext = {}
    elif isinstance(ext_raw, dict):
        ext = ext_raw
    else:
        ext = {}
    storage_type = (getattr(price_row, 'storage_type', None) or '').lower() or None
    storage_type_norm = None
    if storage_type:
        if 'nvme' in storage_type or 'ssd' in storage_type:
            storage_type_norm = 'network_ssd'
        elif 'hdd' in storage_type:
            storage_type_norm = 'hdd'
    return NormalizedSKU(
        provider=getattr(price_row, 'provider', None),
        region=getattr(price_row, 'region', None),
        sku_id=getattr(price_row, 'provider_sku', None),
        vcpu=_to_int(getattr(price_row, 'cpu_cores', None)),
        memory_gib=_to_float(getattr(price_row, 'ram_gb', None)),
        family_hint=ext.get('family') or ext.get('family_hint'),
        cpu_baseline_type=(ext.get('cpu_baseline') or ext.get('burstable')) and 'burstable' or 'standard',
        storage_type=storage_type_norm,
        storage_included_gib=_to_float(getattr(price_row, 'storage_gb', None)),
        network_bandwidth_gbps=_to_float(ext.get('network_gbps')),
        gpu_count=_to_int(ext.get('gpu_count')),
        gpu_mem_gib=_to_float(ext.get('gpu_mem_gib')),
        tenancy=ext.get('tenancy'),
        monthly_cost=_to_float(getattr(price_row, 'monthly_cost', None)),
        currency=getattr(price_row, 'currency', None),
    )


def normalize_resource(resource: Any) -> NormalizedSKU:
    """Normalize a resource row into a NormalizedSKU-like shape for comparison."""
    provider = getattr(resource, 'provider', None)
    if provider and hasattr(provider, 'provider_type'):
        provider_code = provider.provider_type
    else:
        provider_code = getattr(resource, 'provider_type', None)
    provider_region = None
    cfg = None
    try:
        cfg = resource.get_provider_config() if hasattr(resource, 'get_provider_config') else None
    except Exception:
        cfg = None
    if isinstance(cfg, dict):
        provider_region = cfg.get('region') or cfg.get('zone')

    # Fallback to resource.region when config lacks region
    if not provider_region:
        try:
            provider_region = getattr(resource, 'region', None)
        except Exception:
            provider_region = None
    # Treat 'global' as no specific region filter
    if isinstance(provider_region, str) and provider_region.lower() == 'global':
        provider_region = None

    ext = getattr(resource, 'extended_specs', None) or {}

    # Parse CPU/RAM from provider_config if missing
    vcpu_val: Optional[int] = None
    mem_val: Optional[float] = None
    try:
        if isinstance(cfg, dict):
            cpu_field = cfg.get('cpu') or cfg.get('vcpu') or cfg.get('vcpus') or cfg.get('cores') or cfg.get('cpu_cores')
            if cpu_field:
                m = re.search(r"(\d+)", str(cpu_field))
                if m:
                    vcpu_val = int(m.group(1))
            mem_field = cfg.get('memory') or cfg.get('ram') or cfg.get('ram_gb') or cfg.get('ram_mb')
            if mem_field:
                m2 = re.search(r"(\d+)", str(mem_field))
                if m2:
                    # Convert MB to GiB when needed
                    mem_num = float(m2.group(1))
                    if 'mb' in str(mem_field).lower() or (isinstance(mem_num, (int, float)) and mem_num > 64 and mem_num % 1024 == 0):
                        mem_val = mem_num / 1024.0
                    else:
                        mem_val = mem_num
    except Exception:
        pass

    # Extract storage from various possible fields
    storage_gib = None
    storage_type_raw = None
    
    if isinstance(cfg, dict):
        # Use total_storage_gb for accurate total across all disks
        storage_gib = (
            cfg.get('total_storage_gb') or 
            cfg.get('storage_gb') or 
            cfg.get('disk_gb') or 
            ext.get('storage_gb')
        )
        
        # Extract storage type from attached_disks (Yandex format)
        # For mixed storage (e.g., SSD boot + HDD data), use BOOT disk type
        # as it determines VM performance characteristics for comparison
        if cfg.get('attached_disks') and isinstance(cfg.get('attached_disks'), list) and len(cfg['attached_disks']) > 0:
            # Prefer boot disk for storage type (most relevant for performance)
            boot_disk = None
            first_disk = None
            
            for disk in cfg['attached_disks']:
                if isinstance(disk, dict):
                    if first_disk is None:
                        first_disk = disk
                    if disk.get('is_boot') or disk.get('auto_delete'):
                        boot_disk = disk
                        break
            
            # Use boot disk type, fallback to first disk
            disk = boot_disk or first_disk
            if disk and disk.get('type'):
                storage_type_raw = disk['type']  # e.g., 'network-hdd', 'network-ssd'
    
    if storage_gib is None:
        storage_gib = ext.get('storage_gb')
    
    # Normalize storage type
    storage_type_normalized = None
    if storage_type_raw:
        storage_type_lower = str(storage_type_raw).lower()
        if 'nvme' in storage_type_lower or 'ssd' in storage_type_lower:
            storage_type_normalized = 'network_ssd'
        elif 'hdd' in storage_type_lower:
            storage_type_normalized = 'hdd'
    elif ext.get('storage_type'):
        storage_type_normalized = ext.get('storage_type')
    
    return NormalizedSKU(
        provider=provider_code,
        region=provider_region,
        sku_id=getattr(resource, 'resource_name', None),
        vcpu=_to_int(getattr(resource, 'cpu_cores', None) or getattr(resource, 'cpu', None) or ext.get('cpu_cores') or vcpu_val),
        memory_gib=_to_float(getattr(resource, 'ram_gb', None) or getattr(resource, 'memory_gb', None) or ext.get('ram_gb') or mem_val),
        family_hint=ext.get('family') or ext.get('family_hint'),
        cpu_baseline_type=ext.get('cpu_baseline') or 'standard',
        storage_type=storage_type_normalized,
        storage_included_gib=_to_float(storage_gib),
        network_bandwidth_gbps=_to_float(ext.get('network_gbps')),
        gpu_count=_to_int(ext.get('gpu_count')),
        gpu_mem_gib=_to_float(ext.get('gpu_mem_gib')),
        tenancy=ext.get('tenancy'),
        monthly_cost=None,
        currency=None,
    )


def equivalence_score(a: NormalizedSKU, b: NormalizedSKU) -> float:
    """Compute 0..1 equivalence score using MVP weights.

    Weights:
    - vCPU exact match: 0.4 else 0.0 (MVP strict)
    - memory within ±10%: up to 0.3 linear
    - storage size match: up to 0.15 (at least 80% of original)
    - baseline compatibility: 0.1 (exact matches)
    - storage type compatibility: 0.05 (exact matches)
    Region/country preference will be applied as an external filter in queries.
    """
    score = 0.0

    # vCPU strict match (reduced from 0.5 to 0.4 to make room for storage)
    if a.vcpu is not None and b.vcpu is not None and a.vcpu == b.vcpu:
        score += 0.4

    # memory within ±10%
    if a.memory_gib and b.memory_gib:
        high = max(a.memory_gib, b.memory_gib)
        low = min(a.memory_gib, b.memory_gib)
        ratio = low / high if high else 0.0
        # ratio 1.0 => +0.3, ratio 0.9 => +0.27, less than 0.9 => scaled
        if ratio >= 0.0:
            score += 0.3 * max(0.0, min(1.0, (ratio - 0.9) / 0.1 + 1.0)) if ratio >= 0.8 else 0.0

    # storage size match (NEW - weight 0.15)
    if a.storage_included_gib and b.storage_included_gib:
        if b.storage_included_gib >= a.storage_included_gib:
            # Alternative has equal or more storage - full credit
            score += 0.15
        elif b.storage_included_gib >= a.storage_included_gib * 0.8:
            # Alternative has 80-100% of required storage - partial credit
            ratio = b.storage_included_gib / a.storage_included_gib
            score += 0.15 * ratio
        # else: less than 80% storage - no credit (major mismatch)

    # baseline compatibility
    if a.cpu_baseline_type and b.cpu_baseline_type and a.cpu_baseline_type == b.cpu_baseline_type:
        score += 0.1

    # storage type compatibility
    if a.storage_type and b.storage_type and a.storage_type == b.storage_type:
        score += 0.05

    # network similarity
    if a.network_bandwidth_gbps and b.network_bandwidth_gbps:
        high = max(a.network_bandwidth_gbps, b.network_bandwidth_gbps)
        low = min(a.network_bandwidth_gbps, b.network_bandwidth_gbps)
        if high > 0:
            ratio = low / high
            if ratio >= 0.5:
                score += 0.05

    return min(1.0, score)


def candidates_for_resource(
    normalized_resource: NormalizedSKU,
    prices: Iterable[Any],
    preferred_region: Optional[str] = None,
    region_prefix_match: bool = True,
    min_score: float = 0.8,
    limit: int = 10,
) -> List[Tuple[NormalizedSKU, float, Any]]:
    """Find top candidate price rows for the given normalized resource.

    Returns list of tuples (normalized_price, score, original_row) sorted by (score desc, monthly_cost asc).
    """
    norm_prices: List[Tuple[NormalizedSKU, Any]] = [(normalize_price_row(p), p) for p in prices]

    filtered: List[Tuple[NormalizedSKU, Any]] = []
    for ns, row in norm_prices:
        # region filtering
        if preferred_region and ns.region:
            if ns.region == preferred_region:
                pass
            elif region_prefix_match and preferred_region[:2] == ns.region[:2]:
                pass
            else:
                continue

        s = equivalence_score(normalized_resource, ns)
        if s >= min_score:
            filtered.append((ns, row, s))

    # sort by score desc, then cost asc if available
    filtered.sort(key=lambda x: (-x[2], (normalize_price_row(x[1]).monthly_cost or float('inf'))))
    return [(ns, s, row) for (ns, row, s) in filtered[:limit]]





