"""
Selectel Complete VPS Pricing Collector

Fetches Selectel VPS pricing by combining:
1. OpenStack flavors (CPU/RAM configurations)
2. VPC billing prices (per-unit costs)
3. Calculated monthly costs for each flavor
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.core.models import ProviderAdminCredentials


@dataclass
class SelectelVMOffer:
    """Complete VM offer with pricing"""
    flavor_id: str
    flavor_name: str
    vcpus: int
    ram_mb: int
    disk_gb: int
    regions: List[str]
    
    # Price components (monthly RUB)
    cpu_cost: float
    ram_cost: float
    storage_cost: float
    gpu_cost: float
    total_monthly_cost: float
    
    # Optional specs
    cpu_type: str = "standard"
    gpu_name: Optional[str] = None
    gpu_count: int = 0
    is_preemptible: bool = False


def load_admin_credentials() -> Optional[Dict[str, str]]:
    """Load Selectel admin credentials from database"""
    app = create_app()
    with app.app_context():
        creds = ProviderAdminCredentials.query.filter_by(provider_type='selectel').first()
        if not creds:
            return None
        return creds.get_credentials()


def get_account_info_via_test(creds: Dict) -> Optional[Dict]:
    """Get account info using the working test endpoint"""
    try:
        response = requests.post(
            'http://localhost:5001/api/providers/selectel/test',
            json=creds,
            headers={'Content-Type': 'application/json'},
            timeout=30,
        )
        if response.status_code != 200:
            print(f"Test endpoint failed: {response.status_code}")
            return None
        data = response.json()
        return data.get('account_info', {})
    except Exception as e:
        print(f"Failed to call test endpoint: {e}")
        return None


def get_projects(api_key: str) -> List[Dict]:
    """Get available projects"""
    response = requests.get(
        'https://api.selectel.ru/vpc/resell/v2/projects',
        headers={'X-Token': api_key},
        timeout=30,
    )
    if response.status_code != 200:
        print(f"Failed to get projects: {response.status_code}")
        return []
    data = response.json()
    return data.get('projects', [])


def get_iam_token_via_client(creds: Dict) -> Optional[str]:
    """Get IAM token using existing SelectelClient"""
    from app.providers.selectel.client import SelectelClient
    
    try:
        client = SelectelClient(creds)
        # This should trigger the _get_iam_token method
        token = client._get_iam_token()
        return token
    except Exception as e:
        print(f"Failed to get IAM token via client: {e}")
        return None


def fetch_flavors_with_api_key(api_key: str, region: str = 'ru-3') -> List[Dict]:
    """Fetch OpenStack flavors using API key instead of IAM token"""
    headers = {
        'X-Token': api_key,
        'Accept': 'application/json',
        'Openstack-Api-Version': 'compute latest',
    }
    
    response = requests.get(
        f'https://{region}.cloud.api.selcloud.ru/compute/v2.1/flavors/detail',
        headers=headers,
        timeout=30,
    )
    
    if response.status_code != 200:
        print(f"Failed to fetch flavors: {response.status_code} {response.text[:200]}")
        return []
    
    data = response.json()
    return data.get('flavors', [])


def fetch_vpc_prices(api_key: str) -> Dict[str, Dict]:
    """Fetch VPC price matrix and index by resource:region"""
    response = requests.get(
        'https://api.selectel.ru/v2/billing/vpc/prices',
        headers={'X-Token': api_key},
        params={'currency': 'rub'},
        timeout=30,
    )
    
    if response.status_code != 200:
        print(f"Failed to fetch VPC prices: {response.status_code}")
        return {}
    
    data = response.json()
    prices = data.get('prices', [])
    
    # Index as resource:region -> price_entry
    price_map = {}
    for price in prices:
        key = f"{price.get('resource')}:{price.get('group')}"
        price_map[key] = price
    
    return price_map


def calculate_flavor_cost(flavor: Dict, price_map: Dict[str, Dict], region: str) -> Optional[SelectelVMOffer]:
    """Calculate monthly cost for a flavor in a specific region"""
    
    vcpus = flavor.get('vcpus', 0)
    ram_mb = flavor.get('ram', 0)
    disk_gb = flavor.get('disk', 0)
    extra_specs = flavor.get('extra_specs', {})
    
    # Determine CPU type from flavor name or specs
    flavor_name = flavor.get('name', '').lower()
    is_preemptible = 'preemptible' in extra_specs.get('capabilities:instance_type', '')
    
    # Determine CPU resource type
    if 'high_freq' in flavor_name or 'hifreq' in flavor_name:
        cpu_resource = 'compute_cores_high_freq'
    elif 'percent_10' in flavor_name:
        cpu_resource = 'compute_cores_percent_10'
    elif 'percent_20' in flavor_name:
        cpu_resource = 'compute_cores_percent_20'
    elif 'percent_50' in flavor_name:
        cpu_resource = 'compute_cores_percent_50'
    else:
        cpu_resource = 'compute_cores'
    
    if is_preemptible and cpu_resource != 'compute_cores':
        cpu_resource += '_preemptible'
    elif is_preemptible:
        cpu_resource = 'compute_cores_preemptible'
    
    # Determine RAM resource type
    if 'high_freq' in flavor_name or 'hifreq' in flavor_name:
        ram_resource = 'compute_ram_high_freq'
    else:
        ram_resource = 'compute_ram'
    
    if is_preemptible and ram_resource != 'compute_ram':
        ram_resource += '_preemptible'
    elif is_preemptible:
        ram_resource = 'compute_ram_preemptible'
    
    # Storage resource
    storage_resource = 'volume_gigabytes_universal'
    if is_preemptible:
        storage_resource = 'volume_gigabytes_local_preemptible'
    
    # Get prices
    def get_price(resource: str, multiplier: float = 1.0) -> float:
        key = f"{resource}:{region}"
        entry = price_map.get(key)
        if not entry:
            return 0.0
        return entry.get('value', 0.0) * multiplier
    
    cpu_cost = get_price(cpu_resource, vcpus)
    ram_cost = get_price(ram_resource, ram_mb)
    storage_cost = get_price(storage_resource, disk_gb) if disk_gb > 0 else 0.0
    
    # GPU detection and pricing
    gpu_name = None
    gpu_count = 0
    gpu_cost = 0.0
    
    gpu_capability = extra_specs.get('capabilities:gpu_name')
    if gpu_capability:
        gpu_name = gpu_capability
        gpu_count = int(extra_specs.get('capabilities:gpu_count', 1))
        gpu_resource = f"compute_pci_gpu_{gpu_name.lower()}"
        if is_preemptible:
            gpu_resource += '_preemptible'
        gpu_cost = get_price(gpu_resource, gpu_count)
    
    total_cost = cpu_cost + ram_cost + storage_cost + gpu_cost
    
    # Determine CPU type label
    if 'high_freq' in flavor_name:
        cpu_type = "high_frequency"
    elif 'percent' in flavor_name:
        cpu_type = "shared"
    else:
        cpu_type = "standard"
    
    return SelectelVMOffer(
        flavor_id=flavor.get('id'),
        flavor_name=flavor.get('name'),
        vcpus=vcpus,
        ram_mb=ram_mb,
        disk_gb=disk_gb,
        regions=flavor.get('availability_zones', [region]),
        cpu_cost=round(cpu_cost, 2),
        ram_cost=round(ram_cost, 2),
        storage_cost=round(storage_cost, 2),
        gpu_cost=round(gpu_cost, 2),
        total_monthly_cost=round(total_cost, 2),
        cpu_type=cpu_type,
        gpu_name=gpu_name,
        gpu_count=gpu_count,
        is_preemptible=is_preemptible,
    )


def main():
    print("🔍 Loading Selectel admin credentials...")
    creds = load_admin_credentials()
    if not creds:
        print("❌ No Selectel admin credentials configured.")
        return
    
    api_key = creds.get('api_key')
    service_username = creds.get('service_username')
    service_password = creds.get('service_password')
    
    if not all([api_key, service_username, service_password]):
        print("❌ Missing required credentials (api_key, service_username, service_password)")
        return
    
    print("📋 Fetching account info via test endpoint...")
    account_info = get_account_info_via_test(creds)
    if not account_info:
        print("❌ Failed to get account info")
        return
    
    account_id = str(account_info.get('name', '478587'))
    print(f"✅ Account ID: {account_id}")
    
    print("📁 Fetching projects...")
    projects = get_projects(api_key)
    if not projects:
        print("❌ No projects found")
        return
    
    # Use first project
    project = projects[0]
    project_id = project.get('id')
    print(f"✅ Using project: {project.get('name')} ({project_id})")
    
    print("💰 Fetching VPC price matrix...")
    price_map = fetch_vpc_prices(api_key)
    print(f"✅ Loaded {len(price_map)} price entries")
    
    # Fetch flavors for each major region using API key
    regions = ['ru-3', 'ru-7', 'ru-8', 'ru-9']
    all_offers = []
    
    for region in regions:
        print(f"\n🌍 Processing region: {region}")
        flavors = fetch_flavors_with_api_key(api_key, region)
        print(f"  Found {len(flavors)} flavors")
        
        for flavor in flavors:
            # Calculate for first availability zone of this flavor
            zones = flavor.get('availability_zones', [])
            if not zones:
                continue
            
            zone = zones[0]  # e.g., 'ru-3a'
            
            offer = calculate_flavor_cost(flavor, price_map, zone)
            if offer and offer.total_monthly_cost > 0:
                all_offers.append(offer)
    
    print(f"\n✅ Generated {len(all_offers)} VM pricing offers")
    
    # Save to JSON
    output_data = [
        {
            'flavor_id': offer.flavor_id,
            'flavor_name': offer.flavor_name,
            'vcpus': offer.vcpus,
            'ram_gb': round(offer.ram_mb / 1024, 2),
            'ram_mb': offer.ram_mb,
            'disk_gb': offer.disk_gb,
            'regions': offer.regions,
            'cpu_type': offer.cpu_type,
            'is_preemptible': offer.is_preemptible,
            'gpu_name': offer.gpu_name,
            'gpu_count': offer.gpu_count,
            'pricing': {
                'cpu_cost_monthly': offer.cpu_cost,
                'ram_cost_monthly': offer.ram_cost,
                'storage_cost_monthly': offer.storage_cost,
                'gpu_cost_monthly': offer.gpu_cost,
                'total_monthly': offer.total_monthly_cost,
                'currency': 'RUB'
            }
        }
        for offer in all_offers
    ]
    
    output_file = Path('selectel_vps_complete_pricing.json')
    output_file.write_text(json.dumps(output_data, indent=2, ensure_ascii=False))
    print(f"\n💾 Saved complete pricing to: {output_file}")
    
    # Print sample
    print("\n📊 Sample offers:")
    for offer in sorted(all_offers, key=lambda x: x.total_monthly_cost)[:5]:
        print(f"  {offer.flavor_name}: {offer.vcpus}vCPU, {offer.ram_mb}MB RAM = {offer.total_monthly_cost} RUB/month")


if __name__ == '__main__':
    main()

