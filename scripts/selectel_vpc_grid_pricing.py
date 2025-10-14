"""
Selectel VPS pricing sampler (grid-based)

Builds a matrix of VM configurations per region using the public VPC billing
price matrix (cores, RAM, storage) and computes monthly totals. No OpenStack
IAM token required.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any

import requests

from app import create_app
from app.core.models import ProviderAdminCredentials


def load_admin_credentials() -> Dict[str, Any]:
    app = create_app()
    with app.app_context():
        creds = ProviderAdminCredentials.query.filter_by(provider_type='selectel').first()
        return creds.get_credentials() if creds else {}


def fetch_price_map(api_key: str) -> Dict[str, Dict[str, Any]]:
    resp = requests.get(
        'https://api.selectel.ru/v2/billing/vpc/prices',
        headers={'X-Token': api_key},
        params={'currency': 'rub'},
        timeout=30,
    )
    resp.raise_for_status()
    prices = resp.json().get('prices', [])
    idx: Dict[str, Dict[str, Any]] = {}
    for p in prices:
        idx[f"{p.get('resource')}:{p.get('group')}"] = p
    return idx


def regions_from_prices(price_map: Dict[str, Dict[str, Any]]) -> List[str]:
    regions = set()
    for key in price_map.keys():
        if key.startswith('compute_cores:'):
            regions.add(key.split(':', 1)[1])
    return sorted(regions)


def get_price(price_map: Dict[str, Dict[str, Any]], resource: str, region: str, multiplier: float = 1.0) -> float:
    entry = price_map.get(f"{resource}:{region}")
    if not entry:
        return 0.0
    return float(entry.get('value', 0.0)) * multiplier


def build_grid(price_map: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    regions = regions_from_prices(price_map)

    # Sampled values (balanced breadth vs volume)
    vcpus_list = [1, 2, 4, 8, 16, 32]
    ram_gb_list = [1, 2, 4, 8, 16, 32, 64]
    disk_gb_list = [10, 50, 100, 200]

    for region in regions:
        for vcpus in vcpus_list:
            for ram_gb in ram_gb_list:
                for disk_gb in disk_gb_list:
                    cpu_cost = get_price(price_map, 'compute_cores', region, vcpus)
                    ram_cost = get_price(price_map, 'compute_ram', region, ram_gb * 1024)
                    storage_cost = get_price(price_map, 'volume_gigabytes_universal', region, disk_gb)
                    total = cpu_cost + ram_cost + storage_cost

                    results.append(
                        {
                            'provider': 'selectel',
                            'region': region,
                            'vcpus': vcpus,
                            'ram_gb': ram_gb,
                            'disk_gb': disk_gb,
                            'currency': 'RUB',
                            'monthly_cost': round(total, 2),
                            'components': {
                                'cpu_monthly': round(cpu_cost, 2),
                                'ram_monthly': round(ram_cost, 2),
                                'storage_monthly': round(storage_cost, 2),
                            },
                            'source': 'selectel_vpc_matrix',
                        }
                    )

    return results


def main():
    creds = load_admin_credentials()
    api_key = (creds or {}).get('api_key')
    if not api_key:
        print('No Selectel admin API key configured')
        return

    price_map = fetch_price_map(api_key)
    grid = build_grid(price_map)
    out = Path('selectel_vpc_grid_prices.json')
    out.write_text(json.dumps(grid, indent=2, ensure_ascii=False))
    print(f'Saved {len(grid)} grid price entries to {out}')


if __name__ == '__main__':
    main()


