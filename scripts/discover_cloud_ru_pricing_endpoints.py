#!/usr/bin/env python3
"""
Discover Cloud.ru pricing endpoints by exploring the API.

This script:
1. Uses an existing Cloud.ru connection from the database
2. Authenticates and gets product list
3. Tries common pricing endpoint patterns for each product
4. Documents all discovered pricing endpoints
"""

import sys
import os
import json
import requests
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.core.models.provider import CloudProvider
from app.providers.cloud_ru.client import CloudRuClient


def get_product_list(client: CloudRuClient, project_id: str) -> List[Dict[str, Any]]:
    """Get list of all available products."""
    # Based on HAR file, this endpoint requires query parameters
    url = f"https://console.cloud.ru/u-api/bff-console/v1/project/{project_id}/aggregated-available-products"
    # Multiple platformIntNames parameters (requests handles this automatically with list)
    params = {
        'platformIntNames': ['evolution', 'ai_cloud', 'crossplatform', 'private_hybrid']
    }
    
    try:
        response = client.session.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('products', [])
    except Exception as e:
        print(f"Error getting product list: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text[:500]}")
        return []


def try_pricing_endpoints(client: CloudRuClient, project_id: str, product_int_name: str) -> List[Dict[str, Any]]:
    """Try common pricing endpoint patterns for a product."""
    base_url = "https://console.cloud.ru"
    discovered = []
    
    # Common pricing endpoint patterns
    patterns = [
        # Pattern 1: /u-api/{product}/v*/billing/calculate-price
        f"/u-api/{product_int_name.lower()}/v1/billing/calculate-price",
        f"/u-api/{product_int_name.lower()}/v2/billing/calculate-price",
        f"/u-api/{product_int_name.lower()}/v1/billing/calculate-price-ext",
        f"/u-api/{product_int_name.lower()}/v2/billing/calculate-price-ext",
        
        # Pattern 2: /u-api/{product}/v*/price-calculation
        f"/u-api/{product_int_name.lower()}/v1/price-calculation",
        f"/u-api/{product_int_name.lower()}/v2/price-calculation",
        f"/u-api/{product_int_name.lower()}/v1/projects/{project_id}/price-calculation",
        f"/u-api/{product_int_name.lower()}/v2/projects/{project_id}/price-calculation",
        
        # Pattern 3: /u-api/{product}-bff/v*/price-calculator
        f"/u-api/{product_int_name.lower()}-bff/v1/price-calculator",
        f"/u-api/{product_int_name.lower()}-bff/api/v1/price-calculator",
        f"/u-api/{product_int_name.lower()}-bff/api/v1/price-calculator/sku-list",
        
        # Pattern 4: /u-api/{product}/v*/pricing
        f"/u-api/{product_int_name.lower()}/v1/pricing",
        f"/u-api/{product_int_name.lower()}/v2/pricing",
        
        # Pattern 5: /u-api/bff-{product}/v*/pricing
        f"/u-api/bff-{product_int_name.lower()}/v1/pricing",
        
        # Pattern 6: /u-api/svp/v*/{product}/calculate-price (for SVP services)
        f"/u-api/svp/v1/{product_int_name.lower()}/calculate-price",
        f"/u-api/svp/v2/{product_int_name.lower()}/calculate-price",
    ]
    
    for pattern in patterns:
        url = base_url + pattern
        try:
            # Try GET first (most common)
            response = client.session.get(url, timeout=3)
            if response.status_code == 200:
                discovered.append({
                    'method': 'GET',
                    'endpoint': pattern,
                    'status': 200,
                    'content_type': response.headers.get('content-type', ''),
                    'response_sample': response.text[:200] if response.text else ''
                })
            elif response.status_code == 405:  # Method not allowed, try POST
                response = client.session.post(url, json={}, timeout=3)
                if response.status_code == 200:
                    discovered.append({
                        'method': 'POST',
                        'endpoint': pattern,
                        'status': 200,
                        'content_type': response.headers.get('content-type', ''),
                        'response_sample': response.text[:200] if response.text else ''
                    })
        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.RequestException:
            continue
    
    return discovered


def main():
    """Main discovery function."""
    app = create_app()
    
    with app.app_context():
        # Find a Cloud.ru connection
        cloud_ru_provider = CloudProvider.query.filter_by(provider_type='cloud-ru').first()
        
        if not cloud_ru_provider:
            print("❌ No Cloud.ru connection found in database")
            print("   Please add a Cloud.ru connection first")
            return
        
        print(f"✅ Using Cloud.ru connection: {cloud_ru_provider.connection_name} (ID: {cloud_ru_provider.id})")
        
        # Initialize client
        credentials = json.loads(cloud_ru_provider.credentials)
        client = CloudRuClient(credentials)
        
        # Get project_id (will be extracted from token)
        try:
            # Force token refresh to get project_id
            client._get_access_token()
            project_id = client.project_id
            
            if not project_id:
                print("❌ Could not extract project_id from token")
                return
            
            print(f"✅ Project ID: {project_id}\n")
            
            # Get product list (may fail due to permissions)
            print("📋 Getting product list...")
            products = get_product_list(client, project_id)
            
            if not products:
                print("⚠️  Could not get product list (permissions issue)")
                print("   Using known products from HAR file analysis instead\n")
                # Use known products from HAR analysis
                known_products = [
                    {'int_name': 'S3E', 'name': 'Evolution Object Storage'},
                    {'int_name': 'ARTIFACT_REGISTRY', 'name': 'Evolution Artifact Registry'},
                    {'int_name': 'CDN', 'name': 'CDN'},
                    {'int_name': 'MONAAS', 'name': 'Cloud Monitoring'},
                    {'int_name': 'LOGGING_AS_A_SERVICE', 'name': 'Logging'},
                    {'int_name': 'AGENT_BACKUP', 'name': 'Evolution Agent Backup'},
                    {'int_name': 'SERVERLESS_CONTAINER', 'name': 'Evolution Container Apps'},
                    {'int_name': 'EIV', 'name': 'Evolution Compute'},
                    {'int_name': 'MK8S', 'name': 'Evolution Managed Kubernetes'},
                    {'int_name': 'NLB', 'name': 'Evolution Load Balancer'},
                    {'int_name': 'DBAAS_POSTGRESQL', 'name': 'Evolution Managed PostgreSQL'},
                    {'int_name': 'PAAS_REDIS', 'name': 'Evolution Managed Redis'},
                    {'int_name': 'PAAS_KAFKA', 'name': 'Evolution Managed Kafka'},
                ]
                products = known_products
            else:
                print(f"✅ Found {len(products)} products\n")
            
            # Filter to active products only (or use all if we don't have status)
            active_products = [p for p in products if p.get('status', 'PRODUCT_STATUS_ACTIVE') == 'PRODUCT_STATUS_ACTIVE'] if products and 'status' in products[0] else products
            print(f"📊 Products to check: {len(active_products)}\n")
            
            # Try pricing endpoints for each product
            print("="*70)
            print("DISCOVERING PRICING ENDPOINTS")
            print("="*70)
            
            all_discovered = []
            
            for product in active_products:
                int_name = product.get('int_name', '')
                name = product.get('name', 'Unknown')
                
                print(f"\n🔍 Checking: {int_name} ({name})")
                discovered = try_pricing_endpoints(client, project_id, int_name)
                
                if discovered:
                    print(f"   ✅ Found {len(discovered)} pricing endpoint(s):")
                    for endpoint_info in discovered:
                        print(f"      {endpoint_info['method']} {endpoint_info['endpoint']}")
                    all_discovered.extend(discovered)
                else:
                    print(f"   ❌ No pricing endpoints found")
            
            # Save results
            print("\n" + "="*70)
            print("DISCOVERY RESULTS")
            print("="*70)
            print(f"Total pricing endpoints discovered: {len(all_discovered)}")
            
            if all_discovered:
                output_file = 'Docs/cloud_ru_discovered_pricing_endpoints.json'
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(all_discovered, f, indent=2, ensure_ascii=False)
                print(f"\n✅ Results saved to: {output_file}")
            
            # Print summary
            print("\n" + "="*70)
            print("SUMMARY")
            print("="*70)
            for endpoint_info in all_discovered:
                print(f"{endpoint_info['method']:6} {endpoint_info['endpoint']}")
        
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()

