#!/usr/bin/env python3
"""
Analyze last Cloud.ru snapshot for standalone volumes that might be groupable.

A standalone volume = Resource with resource_type/display_type volume, and either:
- Single component (just the volume)
- No server in components

We list these and suggest heuristic patterns to add for grouping.
"""

import sys
import os
import json
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.core.models.provider import CloudProvider
from app.core.models.resource import Resource
from app.core.models.complete_sync import CompleteSync, ProviderSyncReference


def extract_base_for_grouping(name: str, resource_type: str) -> str:
    """Mirror of cloud_ru._extract_base_name_for_grouping for testing."""
    if not name or resource_type not in ('server', 'volume'):
        return name or ''
    name_lower = name.lower()
    base = name
    if resource_type == 'volume':
        if name_lower.startswith('vm-') and '-volume' in name_lower:
            idx = name_lower.index('-volume')
            if idx > 0:
                base = name[:idx].rstrip('-')
        elif name_lower.endswith('-infra-infra'):
            base = name[:-6].rstrip('-')
        else:
            for pattern in [
                r'-volume$', r'-volume-\d+$', r'-volume-\w+$', r'-volume_\w+$',
                r'-disk-\d+$', r'-disk-\w+$', r'-disk_[a-f0-9-]+$',
                r'-data\d+$', r'-data-\d+$',
            ]:
                m = re.search(pattern, name_lower)
                if m:
                    base = name[:m.start()].rstrip('-')
                    break
        if base.lower().endswith('-infra-infra'):
            base = base[:-6].rstrip('-')
    return base


def main():
    app = create_app()
    with app.app_context():
        provider = CloudProvider.query.filter_by(provider_type='cloud-ru').first()
        if not provider:
            print("No Cloud.ru provider found")
            return 1

        # Get last successful complete sync
        refs = (
            ProviderSyncReference.query
            .filter_by(provider_id=provider.id, sync_status='success')
            .order_by(ProviderSyncReference.id.desc())
            .limit(1)
            .all()
        )
        if not refs:
            # Fallback: get resources directly for this provider
            refs = []

        # Get all active Cloud.ru resources from last sync
        resources = Resource.query.filter_by(
            provider_id=provider.id,
            organization_id=provider.organization_id,
            is_active=True
        ).all()

        # Collect servers (for matching) - resource_name of server cards + component names
        server_names = set()
        volume_resources = []
        for r in resources:
            cfg = r.get_provider_config() or {}
            rtype = (r.resource_type or '').lower()
            comps = cfg.get('components') or []
            comp_types = [c.get('type', '') for c in comps if isinstance(c, dict)]

            if 'server' in comp_types or rtype in ('server', 'compute', 'vm'):
                server_names.add(r.resource_name.strip().lower())
                for c in comps:
                    if isinstance(c, dict) and c.get('type') == 'server':
                        n = (c.get('resource_name') or c.get('name') or '').strip()
                        if n:
                            server_names.add(n.lower())

            # Standalone volume: resource_type is volume AND no server in components
            is_volume_card = rtype == 'volume' or (r.service_name or '').lower() == 'block storage'
            has_server = 'server' in comp_types
            if is_volume_card and not has_server:
                volume_resources.append(r)

        # Deduplicate by (resource_name, resource_id) - same volume may appear in different forms
        seen = set()
        unique_volumes = []
        for r in volume_resources:
            key = (r.resource_name or '', r.resource_id or '')
            if key in seen:
                continue
            seen.add(key)
            unique_volumes.append(r)

        print(f"Cloud.ru provider: {provider.connection_name} (id={provider.id})")
        print(f"Total active resources: {len(resources)}")
        print(f"Server names (for matching): {sorted(server_names)}")
        print(f"Standalone volumes: {len(unique_volumes)}")
        print()

        if not unique_volumes:
            print("No standalone volumes found.")
            return 0

        groupable = []
        purely_standalone = []
        for r in unique_volumes:
            name = r.resource_name or r.resource_id or ''
            base = extract_base_for_grouping(name, 'volume')
            base_l = base.lower()
            matches = (
                base_l in server_names or
                f"vm-{base_l}" in server_names or
                (base_l and any(base_l in s or s.endswith(f"-{base_l}") for s in server_names))
            )
            daily = float(r.daily_cost or 0)
            if matches:
                groupable.append((r, base, daily))
            else:
                purely_standalone.append((r, base, daily))

        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"  Groupable (have matching server): {len(groupable)}")
        print(f"  Purely standalone (no server match): {len(purely_standalone)}")
        print()

        if groupable:
            print("=" * 70)
            print("GROUPABLE VOLUMES (will merge into server card after next sync)")
            print("=" * 70)
            for r, base, daily in groupable:
                name = r.resource_name or r.resource_id or ''
                print(f"  • {name}")
                print(f"    base -> {base}  (daily: {daily:.2f} ₽)")

        if purely_standalone:
            print("\n" + "=" * 70)
            print("PURELY STANDALONE VOLUMES (orphans - no server to attach to)")
            print("=" * 70)
            for r, base, daily in purely_standalone:
                name = r.resource_name or r.resource_id or ''
                print(f"  • {name}")
                print(f"    base: {base}  (daily: {daily:.2f} ₽)")

        return 0


if __name__ == '__main__':
    sys.exit(main())
