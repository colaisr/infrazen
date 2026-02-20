#!/usr/bin/env python3
"""
Diagnose Cloud.ru grouping: find resources that ended up standalone but could have been grouped.
Runs sync for specified provider and reports which volumes/servers missed their groups.
"""
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.core.models.provider import CloudProvider
from app.providers.plugins.cloud_ru import CloudRuProviderPlugin


def main():
    provider_id = int(os.environ.get('CLOUD_RU_PROVIDER_ID', '136'))
    app = create_app()
    with app.app_context():
        provider = CloudProvider.query.get(provider_id)
        if not provider or provider.provider_type != 'cloud-ru':
            print(f"Provider {provider_id} not found or not Cloud.ru")
            return 1

        creds = provider.get_credentials()
        plugin = CloudRuProviderPlugin(provider_id, creds)
        print(f"Running sync for {provider.connection_name} (id={provider_id})...")
        result = plugin.sync_resources()

        if not result.success:
            print(f"Sync failed: {result.message}")
            return 1

        resources = result.data.get('resources', [])
        print(f"\nTotal unified resources: {len(resources)}")
        print("=" * 80)

        # Find standalone volumes (single component, type volume)
        standalone_volumes = []
        standalone_servers = []
        multi_component = []
        by_type = {}

        for r in resources:
            d = r.to_dict() if hasattr(r, 'to_dict') else r
            cfg = d.get('provider_config') or {}
            if isinstance(cfg, str):
                try:
                    cfg = json.loads(cfg)
                except Exception:
                    cfg = {}
            comps = cfg.get('components') or []
            comp_types = [c.get('type', '') for c in comps if isinstance(c, dict)]
            rtype = (d.get('resource_type') or '').lower()
            name = d.get('resource_name') or d.get('resource_id', '')

            by_type[rtype] = by_type.get(rtype, 0) + 1

            if len(comps) == 1:
                ct = comp_types[0] if comp_types else ''
                if ct == 'volume' or rtype == 'volume':
                    standalone_volumes.append({
                        'name': name,
                        'type': ct or rtype,
                        'daily': d.get('daily_cost', 0),
                        'servname': (comps[0].get('servname', '') if comps else '')[:50],
                    })
                elif ct == 'server' or rtype in ('server', 'compute', 'vm'):
                    standalone_servers.append({'name': name, 'type': ct or rtype})
            else:
                multi_component.append({
                    'name': name,
                    'types': list(set(comp_types)),
                    'count': len(comps),
                })

        print("\nBY TYPE:", dict(sorted(by_type.items(), key=lambda x: -x[1])))
        print(f"\nStandalone volumes (should merge): {len(standalone_volumes)}")
        print(f"Standalone servers: {len(standalone_servers)}")
        print(f"Multi-component (grouped): {len(multi_component)}")

        if standalone_volumes:
            print("\n" + "=" * 80)
            print("STANDALONE VOLUMES (missed grouping)")
            print("=" * 80)
            for v in sorted(standalone_volumes, key=lambda x: (-x['daily'], x['name'])):
                print(f"  {v['name']}")
                print(f"    servname: {v['servname']}  |  daily: {v['daily']:.2f} ₽")

        # Suggest patterns
        print("\n" + "=" * 80)
        print("PATTERN ANALYSIS")
        print("=" * 80)
        vm_cce = [v['name'] for v in standalone_volumes if 'cce' in v['name'].lower() and v['name'].startswith('vm-')]
        vm_infra = [v['name'] for v in standalone_volumes if '-infra' in v['name'] and 'nodepool' not in v['name']]
        nfs_sfs = [v['name'] for v in standalone_volumes if any(x in v['name'].lower() for x in ['nfs', 'sfs-turbo', 'sp'])]
        data_ext4 = [v['name'] for v in standalone_volumes if 'data-' in v['name'] or 'ext4' in v['name']]
        other = [v['name'] for v in standalone_volumes if v not in vm_cce + vm_infra + nfs_sfs + data_ext4]

        if vm_cce:
            print(f"\nK8s/CCE node volumes ({len(vm_cce)}): vm-*-cce*-*")
            for n in vm_cce[:15]:
                print(f"  - {n}")
            if len(vm_cce) > 15:
                print(f"  ... and {len(vm_cce) - 15} more")
        if vm_infra:
            print(f"\nInfra volumes ({len(vm_infra)}): *-infra")
            for n in vm_infra[:5]:
                print(f"  - {n}")
        if nfs_sfs:
            print(f"\nNFS/SFS (file storage - OK standalone): {len(nfs_sfs)}")
        if data_ext4:
            print(f"\ndata-*/ext4 volumes ({len(data_ext4)}):")
            for n in data_ext4[:5]:
                print(f"  - {n}")
        if other:
            print(f"\nOther ({len(other)}):")
            for n in other[:10]:
                print(f"  - {n}")

        return 0


if __name__ == '__main__':
    sys.exit(main())
