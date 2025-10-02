#!/usr/bin/env python3
"""Test what data is being passed to the template"""

from app import create_app
from app.web.main import get_real_user_resources, get_real_user_providers, get_latest_snapshot_metadata

app = create_app()

with app.app_context():
    user_id = '106509284268867883869'
    
    # Get the data
    resources = get_real_user_resources(user_id)
    providers = get_real_user_providers(user_id)
    snapshot_metadata = get_latest_snapshot_metadata(user_id)
    
    # Group resources by provider
    resources_by_provider = {}
    for resource in resources:
        provider_id = resource.provider.id
        if provider_id not in resources_by_provider:
            resources_by_provider[provider_id] = []
        resources_by_provider[provider_id].append(resource)
    
    print(f"Resources: {len(resources)}")
    print(f"Providers: {len(providers)}")
    print(f"Resources by provider: {len(resources_by_provider)}")
    print(f"Resources by provider keys: {list(resources_by_provider.keys())}")
    print(f"Snapshot metadata: {len(snapshot_metadata)}")
    
    # Check if the condition would pass
    if resources_by_provider:
        print("✅ resources_by_provider is truthy")
    else:
        print("❌ resources_by_provider is falsy")
    
    if providers:
        print("✅ providers is truthy")
    else:
        print("❌ providers is falsy")
