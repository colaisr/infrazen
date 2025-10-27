"""Utility script to fetch Yandex Cloud SKU pricing catalog.

This script fetches the complete SKU pricing catalog from Yandex Cloud Billing API
and saves it to a JSON file for use in cost estimation.

The SKU catalog contains pricing for ALL Yandex Cloud services:
- Compute (VMs, vCPUs, RAM, disks)
- Managed Kubernetes
- Managed Databases (PostgreSQL, MySQL, MongoDB, ClickHouse, Redis)
- VPC, DNS, S3, etc.

Usage:
    python3 scripts/yandex_pricing_fetch.py

Output:
    Writes `yandex_cloud_prices.json` in the project root containing:
    - All SKUs with pricing
    - Service mapping
    - Regional pricing (if applicable)
    - Effective dates

Notes:
    - Requires valid Yandex Cloud connection with billing viewer role
    - API is paginated (fetches all SKUs automatically)
    - Pricing is in RUB (Russian Rubles)
    - Updates pricing dynamically from Yandex API
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from app import create_app
from app.core.models import CloudProvider
from app.providers.yandex.client import YandexClient

logger = logging.getLogger("yandex_pricing_fetch")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def load_yandex_connection() -> Optional[tuple[CloudProvider, YandexClient]]:
    """Load a Yandex Cloud connection with billing access."""
    app = create_app()
    with app.app_context():
        providers = CloudProvider.query.filter_by(provider_type='yandex').all()
        
        if not providers:
            logger.error("No Yandex Cloud connections found")
            return None
        
        # Try each provider until we find one with billing access
        for provider in providers:
            try:
                credentials = provider.get_credentials()
                client = YandexClient(credentials)
                
                # Test if we can fetch SKUs
                logger.info(f"Testing connection: {provider.connection_name} (ID: {provider.id})")
                test_result = client.list_skus(page_size=1)
                
                if test_result and 'skus' in test_result:
                    logger.info(f"✅ Using connection: {provider.connection_name} (ID: {provider.id})")
                    return provider, client
                else:
                    logger.warning(f"❌ Connection {provider.connection_name} cannot access billing SKUs")
            
            except Exception as e:
                logger.warning(f"❌ Connection {provider.connection_name} failed: {e}")
                continue
        
        logger.error("No Yandex connections with billing access found")
        return None


def fetch_all_skus(client: YandexClient) -> List[Dict]:
    """Fetch all SKUs from Yandex Cloud Billing API (handles pagination)."""
    all_skus = []
    page_token = None
    page_num = 1
    
    logger.info("Fetching SKU pricing catalog from Yandex Cloud...")
    
    while True:
        logger.info(f"Fetching page {page_num}...")
        
        result = client.list_skus(page_size=1000, page_token=page_token)
        
        if not result:
            logger.warning(f"Empty result on page {page_num}")
            break
        
        skus = result.get('skus', [])
        if not skus:
            logger.info(f"No more SKUs on page {page_num}")
            break
        
        all_skus.extend(skus)
        logger.info(f"Page {page_num}: Fetched {len(skus)} SKUs (total: {len(all_skus)})")
        
        page_token = result.get('nextPageToken')
        if not page_token:
            logger.info("No more pages (nextPageToken is empty)")
            break
        
        page_num += 1
    
    logger.info(f"✅ Fetched {len(all_skus)} total SKUs")
    return all_skus


def categorize_skus(skus: List[Dict]) -> Dict[str, List[Dict]]:
    """Categorize SKUs by service type for easier lookup."""
    categories = {
        'compute': [],           # VMs, vCPUs, RAM
        'storage': [],          # Disks (HDD, SSD, NVMe)
        'kubernetes': [],       # Managed Kubernetes
        'postgresql': [],       # Managed PostgreSQL
        'mysql': [],           # Managed MySQL
        'mongodb': [],         # Managed MongoDB
        'clickhouse': [],      # Managed ClickHouse
        'redis': [],           # Managed Redis
        'kafka': [],           # Managed Kafka
        'vpc': [],             # VPC, networking
        'dns': [],             # Cloud DNS
        's3': [],              # Object Storage
        'kms': [],             # Key Management Service
        'load_balancer': [],   # Load Balancers
        'container_registry': [],  # Container Registry
        'other': []            # Everything else
    }
    
    logger.info("Categorizing SKUs by service type...")
    
    for sku in skus:
        name = sku.get('name', '').lower()
        sku_id = sku.get('id', '')
        
        # Categorize by SKU name keywords
        if any(kw in name for kw in ['compute', 'vcpu', 'ram', 'memory', 'instance', 'vm']):
            categories['compute'].append(sku)
        elif any(kw in name for kw in ['disk', 'storage', 'hdd', 'ssd', 'nvme']):
            categories['storage'].append(sku)
        elif 'kubernetes' in name or 'k8s' in name:
            categories['kubernetes'].append(sku)
        elif 'postgresql' in name or 'postgres' in name:
            categories['postgresql'].append(sku)
        elif 'mysql' in name:
            categories['mysql'].append(sku)
        elif 'mongodb' in name or 'mongo' in name:
            categories['mongodb'].append(sku)
        elif 'clickhouse' in name:
            categories['clickhouse'].append(sku)
        elif 'redis' in name:
            categories['redis'].append(sku)
        elif 'kafka' in name:
            categories['kafka'].append(sku)
        elif 'vpc' in name or 'network' in name or 'subnet' in name or 'router' in name:
            categories['vpc'].append(sku)
        elif 'dns' in name:
            categories['dns'].append(sku)
        elif 'object storage' in name or 's3' in name:
            categories['s3'].append(sku)
        elif 'kms' in name or 'key management' in name:
            categories['kms'].append(sku)
        elif 'load balancer' in name or 'balancer' in name:
            categories['load_balancer'].append(sku)
        elif 'container registry' in name or 'registry' in name:
            categories['container_registry'].append(sku)
        else:
            categories['other'].append(sku)
    
    # Print summary
    logger.info("SKU Categorization Summary:")
    for category, sku_list in categories.items():
        if sku_list:
            logger.info(f"  {category:20s}: {len(sku_list):5d} SKUs")
    
    return categories


def extract_pricing_data(sku: Dict) -> Dict:
    """Extract relevant pricing data from a SKU."""
    pricing_versions = sku.get('pricingVersions', [])
    
    # Get latest pricing (usually first in list)
    latest_pricing = pricing_versions[0] if pricing_versions else {}
    
    pricing_expressions = latest_pricing.get('pricingExpressions', [])
    rates_data = pricing_expressions[0] if pricing_expressions else {}
    rates = rates_data.get('rates', [])
    
    # Get first rate (usually the base rate)
    first_rate = rates[0] if rates else {}
    
    return {
        'sku_id': sku.get('id'),
        'name': sku.get('name'),
        'service_id': sku.get('serviceId'),
        'unit_price': float(first_rate.get('unitPrice', 0)),
        'currency': first_rate.get('currency', 'RUB'),
        'pricing_type': latest_pricing.get('type', 'STREET_PRICE'),
        'effective_time': latest_pricing.get('effectiveTime'),
        'pricing_unit': rates_data.get('pricingUnit', 'hour'),
        'all_rates': rates  # Keep all rate tiers for tiered pricing
    }


def main():
    """Main execution function."""
    logger.info("=" * 80)
    logger.info("Yandex Cloud SKU Pricing Fetch")
    logger.info("=" * 80)
    
    # Load Yandex connection
    connection = load_yandex_connection()
    if not connection:
        logger.error("❌ Cannot proceed without valid Yandex connection with billing access")
        return
    
    provider, client = connection
    
    # Fetch all SKUs
    all_skus = fetch_all_skus(client)
    if not all_skus:
        logger.error("❌ No SKUs fetched")
        return
    
    # Categorize SKUs
    categorized = categorize_skus(all_skus)
    
    # Process and extract pricing data
    logger.info("Extracting pricing data...")
    processed_skus = []
    
    for sku in all_skus:
        pricing_data = extract_pricing_data(sku)
        processed_skus.append(pricing_data)
    
    # Build output structure
    output = {
        'provider': 'yandex',
        'fetched_at': provider.updated_at.isoformat() if provider.updated_at else None,
        'total_skus': len(all_skus),
        'categories': {
            category: len(sku_list) 
            for category, sku_list in categorized.items() 
            if sku_list
        },
        'skus': processed_skus,
        'categorized_skus': {
            category: [extract_pricing_data(sku) for sku in sku_list]
            for category, sku_list in categorized.items()
            if sku_list
        }
    }
    
    # Save to file
    output_path = Path("yandex_cloud_prices.json")
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    logger.info(f"✅ Pricing data written to {output_path.resolve()}")
    
    # Print summary
    logger.info("=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total SKUs fetched: {len(all_skus)}")
    logger.info(f"Output file: {output_path.resolve()}")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Review yandex_cloud_prices.json")
    logger.info("2. Update YandexService to use SKU-based pricing")
    logger.info("3. Map resource specs to appropriate SKUs")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()

