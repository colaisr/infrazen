#!/usr/bin/env python3
"""
Test S3 storage sync in Beget billing-first implementation
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.providers.plugins.beget import BegetProviderPlugin
import json
from datetime import datetime

def test_s3_sync():
    """Test that S3 storage is now included in sync"""

    # Real credentials from database
    credentials = {
        'username': "colaiswv",
        'password': "Kok5489103",
        'api_url': "https://api.beget.com"
    }

    print(f"Testing S3 storage sync for user: {credentials['username']}")
    print("=" * 60)

    # Create plugin instance
    plugin = BegetProviderPlugin(
        provider_id=1,
        credentials=credentials,
        config={'connection_name': 'Beget- cola'}
    )

    try:
        # Perform billing-first sync with S3 storage
        print("\n1. PERFORMING BILLING-FIRST SYNC WITH S3 STORAGE...")
        
        sync_result = plugin.sync_resources()

        print(f"\nSYNC RESULT: {'SUCCESS' if sync_result.success else 'FAILED'}")
        print(f"Message: {sync_result.message}")
        print(f"Resources synced: {sync_result.resources_synced}")

        if sync_result.success:
            sync_data = sync_result.data
            resources = sync_data.get('resources', [])
            
            print(f"\nRESOURCES FOUND:")
            s3_resources = []
            for resource in resources:
                resource_data = resource.to_dict() if hasattr(resource, 'to_dict') else resource
                resource_name = resource_data.get('resource_name', 'Unknown')
                resource_type = resource_data.get('resource_type', 'unknown')
                effective_cost = resource_data.get('effective_cost', 0)
                
                print(f"  {resource_name} ({resource_type}): {effective_cost:.2f} RUB/day")
                
                if resource_type == 'storage':
                    s3_resources.append(resource_data)

            # Check specifically for S3 storage
            print(f"\nS3 STORAGE RESOURCES:")
            if s3_resources:
                for s3_resource in s3_resources:
                    print(f"  ✓ {s3_resource.get('resource_name')} - {s3_resource.get('effective_cost', 0):.2f} RUB/day")
                    
                    # Check provider config for S3 details
                    provider_config = s3_resource.get('provider_config', {})
                    s3_config = provider_config.get('s3_config', {})
                    
                    print(f"    Access Key: {s3_config.get('access_key', 'N/A')[:10]}...")
                    print(f"    Public: {s3_config.get('public', False)}")
                    print(f"    Quota Used: {s3_config.get('quota_used_size', 0)} bytes")
            else:
                print("  ✗ No S3 storage resources found")

            # Summary
            print(f"\nSUMMARY:")
            print(f"  Total resources: {len(resources)}")
            print(f"  S3 storage resources: {len(s3_resources)}")
            
            # Check if "Talented Justus" is included
            talented_justus = [r for r in resources if 'talented' in r.to_dict().get('resource_name', '').lower()]
            if talented_justus:
                print(f"  ✓ 'Talented Justus' S3 storage found!")
            else:
                print(f"  ✗ 'Talented Justus' S3 storage not found")
            
        else:
            print(f"Sync failed with errors: {sync_result.errors}")

    except Exception as e:
        print(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_s3_sync()
