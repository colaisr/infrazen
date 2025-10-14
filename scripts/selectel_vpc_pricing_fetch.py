"""Explore Selectel VPC pricing using the configurator endpoints captured in HAR."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

import requests

from app import create_app
from app.core.models import ProviderAdminCredentials
from app.providers.selectel.client import SelectelClient


def obtain_token_and_headers() -> Optional[Dict[str, str]]:
    creds = load_admin_credentials()
    if not creds:
        print('No Selectel admin credentials configured.')
        return None

    test_client = SelectelClient(creds)
    test_result = test_client.test_connection()
    if not test_result.get('success'):
        print('Selectel credential test failed:', test_result.get('message', 'unknown error'))
        return None

    account_info = test_result.get('account_info', {})
    account_id = account_info.get('name') or account_info.get('id')
    if not account_id:
        print('Could not determine account ID from test response.')
        return None

    session = requests.Session()
    session.headers.update({'Content-Type': 'application/json', 'Accept': 'application/json'})

    auth_payload = {
        "auth": {
            "identity": {
                "methods": ["password"],
                "password": {
                    "user": {
                        "domain": {"name": account_id},
                        "name": creds.get('service_username'),
                        "password": creds.get('service_password'),
                    }
                },
            }
        }
    }

    response = session.post(
        'https://cloud.api.selcloud.ru/identity/v3/auth/tokens',
        json=auth_payload,
        timeout=30,
    )
    if response.status_code != 201:
        print(f'Failed to obtain IAM token: {response.status_code} {response.text}')
        return None

    token = response.headers.get('X-Subject-Token')
    if not token:
        print('IAM token response missing X-Subject-Token header')
        return None

    return {
        'X-Auth-Token': token,
        'Openstack-Api-Version': 'compute latest',
        'Accept': 'application/json',
        'User-Agent': 'InfraZenPricing/1.0',
    }


HAR_PATH = Path('haar/my.selectel.ru.har')


@dataclass
class SelectelPrice:
    resource: str
    group: str
    value: float
    unit: str


def load_admin_credentials() -> Optional[Dict[str, str]]:
    app = create_app()
    with app.app_context():
        creds = ProviderAdminCredentials.query.filter_by(provider_type='selectel').first()
        if not creds:
            return None
        data = creds.get_credentials()
        return data


def build_session(token: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            'X-Token': token,
            'User-Agent': 'InfraZenPricing/1.0',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://my.selectel.ru',
            'Referer': 'https://my.selectel.ru/',
        }
    )
    return session


def fetch_vpc_prices(session: requests.Session, currency: str = 'rub') -> List[SelectelPrice]:
    response = session.get(
        f'https://api.selectel.ru/v2/billing/vpc/prices',
        params={'currency': currency},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    prices = []
    for entry in payload.get('prices', []):
        value = entry.get('value')
        if value is None:
            continue
        prices.append(
            SelectelPrice(
                resource=entry.get('resource', ''),
                group=entry.get('group', ''),
                value=value,
                unit=entry.get('unit', ''),
            )
        )
    return prices


def fetch_flavors(headers: Dict[str, str], base_url: str) -> List[Dict[str, Any]]:
    response = requests.get(
        f'{base_url}/compute/v2.1/flavors/detail',
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get('flavors', [])


def fetch_volume_types(headers: Dict[str, str], base_url: str) -> List[Dict[str, Any]]:
    vol_headers = headers.copy()
    vol_headers['Openstack-Api-Version'] = 'volume latest'
    response = requests.get(
        f'{base_url}/volume/v3/volumes/detail',
        headers=vol_headers,
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get('volumes', [])


def fetch_price_map(api_key: str) -> Dict[str, Dict[str, Any]]:
    response = requests.get(
        'https://api.selectel.ru/v2/billing/vpc/prices',
        headers={'X-Token': api_key},
        params={'currency': 'rub'},
        timeout=30,
    )
    response.raise_for_status()
    prices = response.json().get('prices', [])
    price_map: Dict[str, Dict[str, Any]] = {}
    for price in prices:
        key = f"{price.get('resource')}:{price.get('group')}"
        price_map[key] = price
    return price_map


def calculate_vm_monthly_cost(
    flavor: Dict[str, Any],
    price_map: Dict[str, Dict[str, Any]],
    region: str,
) -> Optional[Dict[str, Any]]:
    vcpus = flavor.get('vcpus', 0)
    ram_mb = flavor.get('ram', 0)
    disk_gb = flavor.get('disk', 0)
    extra_specs = flavor.get('extra_specs', {})
    gpu_name = extra_specs.get('capabilities:gpu_name')
    gpu_count = extra_specs.get('capabilities:gpu_count')

    def price_for(resource: str, unit_multiplier: float = 1.0) -> float:
        entry = price_map.get(f"{resource}:{region}")
        if not entry:
            return 0.0
        return entry.get('value', 0.0) * unit_multiplier

    core_cost = price_for('compute_cores', vcpus)
    ram_cost = price_for('compute_ram', ram_mb)
    storage_cost = price_for('volume_gigabytes_universal', disk_gb)

    gpu_cost = 0.0
    if gpu_name and gpu_count:
        resource_key = f"compute_pci_gpu_{gpu_name.lower()}"
        gpu_cost = price_for(resource_key, float(gpu_count))

    total_cost = core_cost + ram_cost + storage_cost + gpu_cost

    return {
        'vcpus': vcpus,
        'ram_mb': ram_mb,
        'disk_gb': disk_gb,
        'core_cost': core_cost,
        'ram_cost': ram_cost,
        'storage_cost': storage_cost,
        'gpu_cost': gpu_cost,
        'total_monthly_cost': total_cost,
    }


def aggregate_vm_offers(
    flavors: List[Dict[str, Any]],
    price_map: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    offers = []
    for flavor in flavors:
        availability = flavor.get('availability_zones', [])
        if not availability:
            continue
        region = availability[0]
        cost_components = calculate_vm_monthly_cost(flavor, price_map, region)
        if not cost_components:
            continue

        offers.append(
            {
                'flavor_id': flavor.get('id'),
                'name': flavor.get('name'),
                'vcpus': flavor.get('vcpus'),
                'ram_mb': flavor.get('ram'),
                'disk_gb': flavor.get('disk'),
                'availability_zones': availability,
                'cost': cost_components,
                'extra_specs': flavor.get('extra_specs', {}),
            }
        )
    return offers


def main():
    headers = obtain_token_and_headers()
    if not headers:
        return

    creds = load_admin_credentials()
    api_key = creds.get('api_key') if creds else None
    if not api_key:
        print('Admin credentials missing api_key.')
        return

    base_url = 'https://ru-3.cloud.api.selcloud.ru'
    flavors = fetch_flavors(headers, base_url)
    prices = fetch_price_map(api_key)
    offers = aggregate_vm_offers(flavors, prices)

    Path('selectel_vm_offers.json').write_text(json.dumps(offers, indent=2, ensure_ascii=False))
    print(f'Saved {len(offers)} VM offers to selectel_vm_offers.json')


if __name__ == '__main__':
    main()

