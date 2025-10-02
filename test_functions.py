#!/usr/bin/env python3
"""Test the resource functions directly"""

from app import create_app
from app.web.main import get_real_user_resources, get_real_user_providers

app = create_app()

with app.app_context():
    # First, let's see what user_ids exist in the database
    from app.core.models.provider import CloudProvider
    all_providers = CloudProvider.query.all()
    print(f"All providers in database:")
    for provider in all_providers:
        print(f"  Provider ID: {provider.id}, User ID: {provider.user_id}, String: '{str(provider.user_id)}'")
    
    user_id = '106509284268867883869'
    print(f"\nTesting with user_id: {user_id}")
    
    # Test providers
    providers = get_real_user_providers(user_id)
    print(f"Found {len(providers)} providers")
    for provider in providers:
        print(f"  Provider: {provider}")
    
    # Test resources
    resources = get_real_user_resources(user_id)
    print(f"Found {len(resources)} resources")
    for i, resource in enumerate(resources[:3]):
        print(f"  Resource {i+1}: {resource.resource_name} ({resource.resource_type})")
