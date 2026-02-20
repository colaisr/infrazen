#!/usr/bin/env python3
"""
Test script to discover Cloud.ru volume-to-server attachment APIs.

Purpose: Find API endpoints that return volume attachment info (which server a volume
belongs to) instead of relying on name heuristics for grouping.

Example: Volume vm-21sch-hq-gitlab-01-infra-infra should group with server vm-21sch-hq-gitlab-01-infra.
The Cloud.ru console shows "Servers: vm-21sch-hq-gitlab-01-infra" when viewing the volume.

APIs to try:
1. EVS (Huawei/Advanced): GET /v2/{project_id}/volumes/detail - returns attachments[].server_id
2. ECS (Huawei/Advanced): GET /v1/{project_id}/cloudservers/detail - may include volume attachments
3. SVP/Evolution: /u-api/svp/svc/v1/... - servers, volumes, product-instances
4. BFF product-instances: May list volumes with parent server info
"""

import sys
import json
import requests
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.core.models.provider import CloudProvider
from app.providers.cloud_ru.client import CloudRuClient


def try_endpoint(
    session: requests.Session,
    method: str,
    url: str,
    params: Optional[Dict] = None,
    json_data: Optional[Dict] = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    """Try an API endpoint and return result summary."""
    result = {
        'url': url,
        'method': method,
        'status': None,
        'ok': False,
        'error': None,
        'sample': None,
        'attachments_found': False,
        'volumes_with_server': [],
    }
    try:
        if method == 'GET':
            r = session.get(url, params=params, timeout=timeout)
        else:
            r = session.post(url, json=json_data or {}, timeout=timeout)
        result['status'] = r.status_code
        result['ok'] = r.ok
        if r.ok:
            try:
                data = r.json()
                result['sample'] = json.dumps(data, indent=2, ensure_ascii=False)[:2000]
                # Check for volume attachment info
                if isinstance(data, dict):
                    volumes = data.get('volumes', data.get('items', []))
                    if isinstance(volumes, list):
                        for v in volumes:
                            if isinstance(v, dict):
                                att = v.get('attachments', [])
                                if att:
                                    result['attachments_found'] = True
                                    for a in att:
                                        sid = a.get('server_id') or a.get('serverId')
                                        if sid:
                                            result['volumes_with_server'].append({
                                                'volume_id': v.get('id', v.get('volume_id', '')),
                                                'volume_name': v.get('name', ''),
                                                'server_id': sid,
                                            })
                elif isinstance(data, list):
                    for v in data:
                        if isinstance(v, dict) and v.get('attachments'):
                            result['attachments_found'] = True
                            break
            except Exception:
                result['sample'] = r.text[:1000] if r.text else None
        else:
            result['error'] = r.text[:500] if r.text else str(r.reason)
    except Exception as e:
        result['error'] = str(e)
    return result


def main():
    """Discover volume attachment APIs."""
    app = create_app()
    with app.app_context():
        provider = CloudProvider.query.filter_by(provider_type='cloud-ru').first()
        if not provider:
            print("❌ No Cloud.ru connection found. Add a connection first.")
            return 1

        print(f"✅ Using: {provider.connection_name} (ID: {provider.id})\n")
        creds = json.loads(provider.credentials)
        client = CloudRuClient(creds)

        if not client._ensure_authenticated():
            print("❌ Authentication failed")
            return 1

        project_id = client.project_id
        agreement_id = client.agreement_id
        if not project_id:
            projects = client.get_projects()
            project_id = (projects[0].get('id') or projects[0].get('project_id')) if projects else None
        if not project_id:
            print("❌ No project_id available")
            return 1

        print(f"Project ID: {project_id}")
        if agreement_id:
            print(f"Agreement ID: {agreement_id}")
        print()

        # Target volume from user's example (for validation)
        target_volume_id = "076ba225-0677-4a83-a3d1-4da371f1d140"
        target_volume_name = "vm-21sch-hq-gitlab-01-infra-infra"
        expected_server = "vm-21sch-hq-gitlab-01-infra"

        endpoints = []

        # 1. EVS (Huawei/Advanced) - standard OpenStack Cinder API
        evs_base = "https://evs.ru-moscow-1.hc.sbercloud.ru"
        endpoints.append(('EVS volumes/detail (Advanced)', 'GET', f"{evs_base}/v2/{project_id}/volumes/detail", None, None))
        endpoints.append(('EVS volumes/detail limit=10', 'GET', f"{evs_base}/v2/{project_id}/volumes/detail", {'limit': 10}, None))

        # 2. ECS (Huawei/Advanced) - servers with volumes
        ecs_base = "https://ecs.ru-moscow-1.hc.sbercloud.ru"
        endpoints.append(('ECS cloudservers/detail', 'GET', f"{ecs_base}/v1/{project_id}/cloudservers/detail", None, None))

        # 3. Evolution/SVP - console.cloud.ru u-api
        console_base = "https://console.cloud.ru"
        # SVP product instances / servers
        endpoints.append(('SVP product-instances', 'GET',
            f"{console_base}/u-api/bff-console/v1/projects/{project_id}/product-instances", None, None))
        endpoints.append(('SVP servers (guess)', 'GET',
            f"{console_base}/u-api/svp/svc/v1/projects/{project_id}/servers", None, None))
        endpoints.append(('SVP volumes (guess)', 'GET',
            f"{console_base}/u-api/svp/svc/v1/projects/{project_id}/volumes", None, None))
        endpoints.append(('SVP volumes/detail (guess)', 'GET',
            f"{console_base}/u-api/svp/svc/v1/projects/{project_id}/volumes/detail", None, None))
        # EVS under u-api
        endpoints.append(('u-api EVS volumes', 'GET',
            f"{console_base}/u-api/evs/v1/projects/{project_id}/volumes", None, None))
        endpoints.append(('u-api EVS volumes/detail', 'GET',
            f"{console_base}/u-api/evs/v2/{project_id}/volumes/detail", None, None))
        # EIV (Evolution Compute)
        endpoints.append(('u-api EIV servers', 'GET',
            f"{console_base}/u-api/eiv/v1/projects/{project_id}/servers", None, None))

        # 4. Agreement-scoped product instances (may have more data)
        if agreement_id:
            endpoints.append(('BFF agreements product-instances', 'GET',
                f"{console_base}/u-api/bff-console/v1/agreements/{agreement_id}/product-instances", None, None))

        # 5. Inspect product-instances response (it returns 200)
        print("=" * 60)
        print("Fetching product-instances structure...")
        print("=" * 60)
        pi_url = f"{console_base}/u-api/bff-console/v1/projects/{project_id}/product-instances"
        try:
            r = client.session.get(pi_url, timeout=15)
            if r.status_code == 200:
                data = r.json()
                items = data if isinstance(data, list) else data.get('items', data.get('product_instances', data.get('instances', [])))
                if isinstance(items, list) and items:
                    print(f"Found {len(items)} product instances")
                    sample = items[0]
                    print(f"First item keys: {list(sample.keys())}")
                    for k, v in list(sample.items())[:15]:
                        val_str = str(v)[:80] if v is not None else 'null'
                        print(f"  {k}: {val_str}")
                    # Look for volumes/servers with attachment info
                    for item in items:
                        name = item.get('name', item.get('resource_name', ''))
                        if 'volume' in str(name).lower() or 'disk' in str(name).lower():
                            print(f"\nVolume-like instance: {name}")
                            print(f"  Keys: {list(item.keys())}")
                            for k in ['server_id', 'parent_id', 'attached_to', 'server', 'parent', 'meta']:
                                if k in item and item[k]:
                                    print(f"  {k}: {item[k]}")
            else:
                print(f"product-instances returned {r.status_code}")
        except Exception as e:
            print(f"Error: {e}")

        print("\n" + "=" * 60)
        print("Testing volume attachment API endpoints")
        print("=" * 60)

        found_attachments = []
        for name, method, url, params, body in endpoints:
            print(f"\n📡 {name}")
            print(f"   {method} {url}")
            result = try_endpoint(client.session, method, url, params, body)
            if result['status']:
                status_icon = "✅" if result['ok'] else "❌"
                print(f"   {status_icon} Status: {result['status']}")
                if result['error']:
                    print(f"   Error: {result['error'][:200]}")
                if result['attachments_found']:
                    print(f"   🎯 ATTACHMENTS FOUND! Volumes with server_id:")
                    for v in result['volumes_with_server'][:5]:
                        print(f"      - {v.get('volume_name', v.get('volume_id'))} -> server_id: {v.get('server_id')}")
                    found_attachments.append((name, result))
                elif result['ok'] and result['sample']:
                    # Show structure hint
                    sample = result['sample']
                    if 'attachments' in sample or 'server' in sample.lower():
                        print(f"   📋 Response may contain attachment info (sample):")
                        print(f"      {sample[:300]}...")
            else:
                print(f"   ⚠️ Request failed: {result.get('error', 'unknown')}")

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        if found_attachments:
            print("\n✅ Endpoints with volume attachment info:")
            for name, res in found_attachments:
                print(f"   - {name}")
                print(f"     URL: {res['url']}")
                for v in res.get('volumes_with_server', [])[:3]:
                    print(f"     Example: {v.get('volume_name')} attached to server_id={v.get('server_id')}")
        else:
            print("\n❌ No endpoints returned volume attachment data in this run.")
            print("   Possible reasons:")
            print("   - Evolution platform uses different API paths than Advanced (hc.sbercloud.ru)")
            print("   - Service account may not have EVS/ECS read permissions")
            print("   - Product-instances may need different filters")
            print("\n   Recommendation: Capture HAR when opening a volume in Cloud.ru console")
            print("   and look for the API call that loads 'Servers' section.")

        # Also try to get consumption data and check for any parent/attachment fields
        print("\n" + "-" * 60)
        print("Checking consumption API for attachment metadata...")
        try:
            billing = client.get_billing_data(days=1)
            consumptions = billing.get('consumptions', [])
            # Look for volume records with extra fields
            volume_records = [c for c in consumptions if 'disk' in str(c.get('servname', '')).lower()
                         or 'volume' in str(c.get('resource_name', '')).lower()]
            if volume_records:
                sample = volume_records[0]
                print(f"   Consumption record keys: {list(sample.keys())}")
                for key in ['parent_id', 'parent_resource_id', 'server_id', 'instance_id', 'attached_to', 'meta']:
                    if key in sample and sample[key]:
                        print(f"   - {key}: {str(sample[key])[:100]}")
                if 'meta' in sample and isinstance(sample['meta'], dict):
                    print(f"   - meta keys: {list(sample['meta'].keys())}")
        except Exception as e:
            print(f"   Error: {e}")

        return 0


if __name__ == '__main__':
    sys.exit(main())
