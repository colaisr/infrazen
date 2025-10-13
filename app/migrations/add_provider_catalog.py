#!/usr/bin/env python3
"""
Migration: Add Provider Catalog table and seed initial data
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from app.core.database import db
from app.core.models.provider_catalog import ProviderCatalog

def migrate():
    """Add provider_catalog table and seed initial data"""
    app = create_app()
    
    with app.app_context():
        print("Creating provider_catalog table...")
        
        # Create the table
        db.create_all()
        
        print("Seeding initial provider catalog data...")
        
        # Seed initial providers
        providers = [
            {
                'provider_type': 'beget',
                'display_name': 'Beget',
                'description': 'Russian hosting provider offering VPS, shared hosting, domains, and email services',
                'logo_url': '/static/provider_logos/beget_logo.jpeg',
                'is_enabled': True,
                'has_pricing_api': False,
                'pricing_method': 'billing',
                'website_url': 'https://beget.com',
                'documentation_url': 'https://beget.com/api',
                'supported_regions': '["moscow", "spb"]'
            },
            {
                'provider_type': 'selectel',
                'display_name': 'Selectel',
                'description': 'Russian cloud provider offering VMs, storage, databases, and managed services',
                'logo_url': '/static/provider_logos/selectel_logo.svg',
                'is_enabled': True,
                'has_pricing_api': False,
                'pricing_method': 'billing',
                'website_url': 'https://selectel.com',
                'documentation_url': 'https://docs.selectel.com',
                'supported_regions': '["ru-1", "ru-2", "ru-3", "ru-7", "ru-8", "ru-9"]'
            },
            {
                'provider_type': 'yandex',
                'display_name': 'Yandex Cloud',
                'description': 'Russian cloud platform offering compute, storage, databases, and AI services',
                'logo_url': '/static/provider_logos/yandex_logo.png',
                'is_enabled': False,  # Disabled initially - no pricing data yet
                'has_pricing_api': True,
                'pricing_method': 'api',
                'website_url': 'https://cloud.yandex.ru',
                'documentation_url': 'https://cloud.yandex.ru/docs',
                'supported_regions': '["ru-central1-a", "ru-central1-b", "ru-central1-c", "ru-central1-d"]'
            },
            {
                'provider_type': 'aws',
                'display_name': 'Amazon Web Services',
                'description': 'Global cloud platform with comprehensive services and Russian region support',
                'logo_url': '/static/provider_logos/aws_logo.png',
                'is_enabled': False,  # Disabled initially - no pricing data yet
                'has_pricing_api': True,
                'pricing_method': 'api',
                'website_url': 'https://aws.amazon.com',
                'documentation_url': 'https://docs.aws.amazon.com',
                'supported_regions': '["eu-west-1", "eu-central-1", "eu-north-1"]'
            }
        ]
        
        for provider_data in providers:
            # Check if provider already exists
            existing = ProviderCatalog.query.filter_by(
                provider_type=provider_data['provider_type']
            ).first()
            
            if not existing:
                provider = ProviderCatalog(**provider_data)
                db.session.add(provider)
                print(f"  Added {provider_data['display_name']} to catalog")
            else:
                print(f"  {provider_data['display_name']} already exists, skipping")
        
        # Commit changes
        db.session.commit()
        
        # Show final statistics
        total_providers = ProviderCatalog.query.count()
        enabled_providers = ProviderCatalog.query.filter_by(is_enabled=True).count()
        
        print(f"\nMigration completed!")
        print(f"Total providers in catalog: {total_providers}")
        print(f"Enabled providers: {enabled_providers}")
        print(f"Disabled providers: {total_providers - enabled_providers}")

def rollback():
    """Rollback migration by dropping the table"""
    app = create_app()
    
    with app.app_context():
        print("Dropping provider_catalog table...")
        db.drop_all()
        print("Rollback completed!")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        rollback()
    else:
        migrate()
