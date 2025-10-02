#!/usr/bin/env python3
"""Test script to check resources in database"""

from app import create_app
from app.core.models.provider import CloudProvider
from app.core.models.resource import Resource

app = create_app()

with app.app_context():
    # Test the query - get all providers first
    all_providers = CloudProvider.query.all()
    print(f'Found {len(all_providers)} total providers in database')
    
    for provider in all_providers:
        print(f'Provider ID: {provider.id}, User ID: {provider.user_id}, Type: {provider.provider_type}, Name: {provider.connection_name}')
        resources = Resource.query.filter_by(provider_id=provider.id).all()
        print(f'  Found {len(resources)} resources for provider {provider.id}')
        
        for i, resource in enumerate(resources[:3]):  # Show first 3 resources
            print(f'    Resource {i+1}: {resource.resource_name} ({resource.resource_type})')
