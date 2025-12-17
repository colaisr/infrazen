#!/usr/bin/env python3
"""
Debug script to run Cloud.ru sync and inspect all data
"""
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.core.models.provider import CloudProvider
from app.providers import sync_orchestrator
from app.providers.cloud_ru.client import CloudRuClient
from app.providers.plugins.cloud_ru import CloudRuProviderPlugin

app = create_app()

with app.app_context():
    # Find the last Cloud.ru provider
    cloud_ru_provider = CloudProvider.query.filter_by(
        provider_type='cloud-ru').order_by(CloudProvider.created_at.desc()).first()
    
    if not cloud_ru_provider:
        print("No Cloud.ru provider found!")
        sys.exit(1)
    
    print(f"Found Cloud.ru provider: ID={cloud_ru_provider.id}, Name={cloud_ru_provider.connection_name}")
    print(f"Account ID: {cloud_ru_provider.account_id}")
    print("-" * 80)
    
    # Get credentials
    credentials = cloud_ru_provider.get_credentials()
    print(f"Credentials keys: {list(credentials.keys())}")
    print("-" * 80)
    
    # Step 1: Test client and inspect VM data
    print("\n=== STEP 1: Inspecting VM Data from API ===")
    client = CloudRuClient(credentials)
    
    # Get access token
    token = client._get_access_token()
    if token:
        project_id = getattr(client, 'project_id', None)
        print(f"✓ Got access token (project_id: {project_id})")
    else:
        print("✗ Failed to get access token")
        sys.exit(1)
    
    # Get VMs
    vms = client.get_vms()
    print(f"Found {len(vms)} VMs")
    
    if vms:
        vm = vms[0]
        print(f"\nVM Data Structure:")
        print(f"  Keys: {list(vm.keys())}")
        print(f"  ID: {vm.get('id')}")
        print(f"  Name: {vm.get('name')}")
        print(f"  State: {vm.get('state')}")
        
        # Inspect flavor
        flavor = vm.get('flavor', {})
        print(f"\n  Flavor data:")
        if isinstance(flavor, dict):
            print(f"    Keys: {list(flavor.keys())}")
            for key, value in flavor.items():
                print(f"    {key}: {value} (type: {type(value).__name__})")
        else:
            print(f"    Flavor is not a dict: {type(flavor)} = {flavor}")
        
        # Inspect other fields that might contain specs
        print(f"\n  Other fields that might contain specs:")
        for key in ['vcpus', 'cpu', 'cpu_count', 'ram', 'memory', 'memory_mb', 'disk', 'disk_gb', 'storage', 'size']:
            if key in vm:
                print(f"    {key}: {vm[key]}")
        
        # Save full VM data for inspection
        with open('cloud_ru_vm_data.json', 'w') as f:
            json.dump(vm, f, indent=2, default=str)
        print(f"\n  Full VM data saved to cloud_ru_vm_data.json")
    
    # Step 2: Test billing API
    print("\n=== STEP 2: Testing Billing API ===")
    billing_data = client.get_billing_data(days=7)
    if billing_data:
        print(f"Billing API Response:")
        print(f"  Keys: {list(billing_data.keys())}")
        
        consumptions = billing_data.get('consumptions', [])
        print(f"  Found {len(consumptions)} consumption records")
        
        if consumptions:
            consumption = consumptions[0]
            print(f"\n  First consumption record:")
            print(f"    Keys: {list(consumption.keys())}")
            for key, value in consumption.items():
                if isinstance(value, (dict, list)):
                    print(f"    {key}: {type(value).__name__} with {len(value) if hasattr(value, '__len__') else 'N/A'} items")
                else:
                    print(f"    {key}: {value}")
        
        # Save full billing data
        with open('cloud_ru_billing_data.json', 'w') as f:
            json.dump(billing_data, f, indent=2, default=str)
        print(f"\n  Full billing data saved to cloud_ru_billing_data.json")
    else:
        print("✗ No billing data returned")
    
    # Step 3: Run full sync
    print("\n=== STEP 3: Running Full Sync ===")
    sync_result = sync_orchestrator.sync_provider(cloud_ru_provider.id, sync_type='manual')
    
    print(f"Sync Result:")
    print(f"  Success: {sync_result.get('success')}")
    print(f"  Message: {sync_result.get('message')}")
    print(f"  Resources synced: {sync_result.get('resources_synced', 0)}")
    print(f"  Total cost: {sync_result.get('total_cost', 0)}")
    
    if sync_result.get('error'):
        print(f"  Error: {sync_result.get('error')}")
    
    # Step 4: Check saved resource
    print("\n=== STEP 4: Checking Saved Resource ===")
    from app.core.models.resource import Resource
    
    resources = Resource.query.filter_by(provider_id=cloud_ru_provider.id).all()
    print(f"Found {len(resources)} resources in database")
    
    for resource in resources:
        print(f"\n  Resource: {resource.resource_name}")
        print(f"    Type: {resource.resource_type}")
        print(f"    Daily Cost: {resource.daily_cost}")
        print(f"    Effective Cost: {resource.effective_cost}")
        print(f"    Region: {resource.region}")
        print(f"    Status: {resource.status}")
        
        # Check provider_config
        config = resource.get_provider_config()
        if config:
            print(f"    Provider Config keys: {list(config.keys())}")
            if 'cpu_cores' in config or 'vcpus' in config:
                print(f"      CPU: {config.get('cpu_cores') or config.get('vcpus')}")
            if 'ram_mb' in config or 'memory_mb' in config:
                ram_mb = config.get('ram_mb') or config.get('memory_mb', 0)
                ram_gb = ram_mb / 1024 if ram_mb else 0
                print(f"      RAM: {ram_mb} MB ({ram_gb} GB)")
            if 'disk_gb' in config or 'total_storage_gb' in config:
                print(f"      Disk: {config.get('disk_gb') or config.get('total_storage_gb')} GB")
        
        # Save full resource data
        with open('cloud_ru_resource_data.json', 'w') as f:
            resource_dict = {
                'id': resource.id,
                'name': resource.resource_name,
                'type': resource.resource_type,
                'daily_cost': float(resource.daily_cost) if resource.daily_cost else 0,
                'effective_cost': float(resource.effective_cost) if resource.effective_cost else 0,
                'provider_config': config,
                'region': resource.region,
                'status': resource.status
            }
            json.dump(resource_dict, f, indent=2, default=str)
        print(f"    Full resource data saved to cloud_ru_resource_data.json")

