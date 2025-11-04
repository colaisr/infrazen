#!/usr/bin/env python3
"""
Fetch Beget Managed Database (Cloud Databases) pricing and store in provider_prices table.

Beget offers managed MySQL and PostgreSQL databases through their Cloud Databases service.
This script fetches all available configurations and pricing.

Usage:
    python beget_dbaas_pricing_fetch.py
"""

import sys
import os
import json
from typing import List, Dict, Any
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.core.models.pricing import ProviderPrice
from app.core.models.provider_admin_credentials import ProviderAdminCredentials
from app.core.database import db
from app.providers.beget.beget_client import BegetAPIClient

import requests


class BegetDBaaSPricingClient:
    """Client for fetching Beget Managed Database pricing."""
    
    API_BASE = "https://api.beget.com/v1"
    CLOUD_CONFIG_ENDPOINT = "/cloud/configuration"
    
    def __init__(self):
        """Initialize the client."""
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "InfraZenPricing/1.0",
        })
    
    def fetch_cloud_configurations(self) -> Dict[str, Any]:
        """
        Fetch cloud database configurations from Beget API.
        
        Returns:
            Dict containing all available database configurations
        """
        url = f"{self.API_BASE}{self.CLOUD_CONFIG_ENDPOINT}"
        
        print(f"Fetching Beget Cloud DB configurations from: {url}")
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        return data
    
    def _map_db_type_to_resource_type(self, db_type: str) -> str:
        """
        Map Beget database type to our resource_type taxonomy.
        
        Args:
            db_type: Beget type (e.g., 'MYSQL5', 'POSTGRESQL14')
            
        Returns:
            Normalized resource type
        """
        if 'MYSQL' in db_type.upper():
            return 'mysql-cluster'
        elif 'POSTGRESQL' in db_type.upper():
            return 'postgresql-cluster'
        elif 'REDIS' in db_type.upper():
            return 'redis-cluster'
        else:
            return 'database-cluster'
    
    def _extract_config_specs(self, config: Dict[str, Any], db_type: str) -> Dict[str, Any]:
        """
        Extract CPU/RAM/Storage specs from configuration object.
        
        Args:
            config: Configuration dict
            db_type: Database type (e.g., 'MYSQL5', 'POSTGRESQL14')
            
        Returns:
            Dict with cpu_count, ram_gb, disk_gb, version
        """
        # The key name in the config varies by type
        # MYSQL5 -> mysql5, POSTGRESQL14 -> postgresql14, etc.
        config_key = db_type.lower()
        db_config = config.get(config_key, {})
        
        if not db_config:
            return None
        
        cpu_count = db_config.get('cpu_count', 0)
        memory_mb = db_config.get('memory', 0)
        disk_mb = db_config.get('disk_size', 0)
        version = db_config.get('version', '') or db_config.get('display_version', '')
        
        return {
            'cpu_count': cpu_count,
            'ram_gb': memory_mb / 1024,
            'disk_gb': disk_mb / 1024,
            'version': version
        }
    
    def parse_configurations(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse cloud configurations into pricing records.
        
        Args:
            data: Raw API response
            
        Returns:
            List of pricing records
        """
        configurations = data.get('configuration', [])
        
        records = []
        skipped_types = set()
        
        for config in configurations:
            config_id = config.get('id')
            db_type = config.get('type', '')
            region = config.get('region', 'unknown')
            price_day = config.get('price_day')
            price_month = config.get('price_month')
            
            # Skip non-database types (S_3, CDN, etc.)
            if db_type in ['S_3', 'CDN']:
                skipped_types.add(db_type)
                continue
            
            # Extract specs
            specs = self._extract_config_specs(config, db_type)
            
            if not specs:
                print(f"Warning: Could not extract specs for {config_id} (type={db_type})")
                continue
            
            # Map to our resource type
            resource_type = self._map_db_type_to_resource_type(db_type)
            
            # Generate provider SKU
            provider_sku = config_id
            
            # Create pricing record
            records.append({
                "provider": "beget",
                "resource_type": resource_type,
                "provider_sku": provider_sku,
                "region": region,
                "cpu_cores": specs['cpu_count'],
                "ram_gb": specs['ram_gb'],
                "storage_gb": specs['disk_gb'],
                "storage_type": "local_nvme",  # Beget uses local NVMe for managed DBs
                "extended_specs": {
                    "database_type": db_type,
                    "database_version": specs['version'],
                    "pricing_method": "cloud_config_api",
                },
                "hourly_cost": None,
                "monthly_cost": float(price_month) if price_month else 0.0,
                "currency": "RUB",
                "source": "beget_cloud_api",
                "notes": f"Beget Managed {db_type} v{specs['version']} with local NVMe SSD",
            })
        
        if skipped_types:
            print(f"Skipped non-database types: {', '.join(skipped_types)}")
        
        return records
    
    def get_dbaas_prices(self) -> List[Dict[str, Any]]:
        """
        Fetch and parse Beget managed database pricing.
        
        Returns:
            List of pricing records ready for database insertion
        """
        print("Fetching Beget Managed Database configurations...")
        data = self.fetch_cloud_configurations()
        
        print("Parsing configurations...")
        records = self.parse_configurations(data)
        
        print(f"Generated {len(records)} Beget managed DB pricing records")
        return records


def sync_dbaas_prices():
    """Sync Beget Managed DB pricing to database."""
    client = BegetDBaaSPricingClient()
    
    try:
        # Fetch pricing records
        records = client.get_dbaas_prices()
        
        if not records:
            print("No pricing records generated")
            return 0
        
        # Delete existing Beget managed DB pricing
        deleted_mysql = ProviderPrice.query.filter(
            ProviderPrice.provider == "beget",
            ProviderPrice.resource_type == "mysql-cluster"
        ).delete()
        
        deleted_pg = ProviderPrice.query.filter(
            ProviderPrice.provider == "beget",
            ProviderPrice.resource_type == "postgresql-cluster"
        ).delete()
        
        deleted_total = deleted_mysql + deleted_pg
        
        if deleted_total > 0:
            print(f"Deleted {deleted_total} existing Beget managed DB pricing records")
        
        # Insert new records
        inserted_count = 0
        for record in records:
            price = ProviderPrice(
                provider=record["provider"],
                resource_type=record["resource_type"],
                provider_sku=record["provider_sku"],
                region=record["region"],
                cpu_cores=record["cpu_cores"],
                ram_gb=record["ram_gb"],
                storage_gb=record["storage_gb"],
                storage_type=record["storage_type"],
                extended_specs=json.dumps(record["extended_specs"]),
                hourly_cost=record["hourly_cost"],
                monthly_cost=record["monthly_cost"],
                currency=record["currency"],
                source=record["source"],
                notes=record["notes"],
                last_updated=datetime.utcnow()
            )
            db.session.add(price)
            inserted_count += 1
        
        db.session.commit()
        print(f"✅ Successfully inserted {inserted_count} managed DB pricing records")
        
        # Print summary by type
        from collections import Counter
        type_counts = Counter(r['resource_type'] for r in records)
        print()
        print("Summary by database type:")
        for db_type, count in type_counts.items():
            print(f"  • {db_type}: {count} configs")
        
        return inserted_count
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error syncing Beget managed DB prices: {e}")
        raise


def main():
    """Main entry point."""
    app = create_app()
    
    with app.app_context():
        print("=" * 80)
        print("BEGET MANAGED DATABASES (Cloud Databases) PRICING SYNC")
        print("=" * 80)
        print()
        
        # Get Beget credentials and authenticate
        admin_creds = ProviderAdminCredentials.query.filter_by(
            provider_type='beget'
        ).first()
        
        if not admin_creds:
            print("❌ ERROR: No admin credentials found for Beget")
            print()
            print("Please configure Beget admin credentials in the database")
            sys.exit(1)
        
        credentials = admin_creds.get_credentials()
        username = credentials.get('username')
        password = credentials.get('password')
        
        if not username or not password:
            print("❌ ERROR: No username/password found in Beget credentials")
            sys.exit(1)
        
        print(f"Authenticating as Beget user: {username}")
        
        # Authenticate with Beget API
        beget_client = BegetAPIClient(username, password)
        
        if not beget_client.authenticate():
            print("❌ ERROR: Failed to authenticate with Beget API")
            sys.exit(1)
        
        if not beget_client.access_token:
            print("❌ ERROR: No access token received from Beget")
            sys.exit(1)
        
        print("✅ Authenticated successfully")
        print()
        
        try:
            # Update client session with auth token
            client = BegetDBaaSPricingClient()
            client.session.headers['Authorization'] = f'Bearer {beget_client.access_token}'
            
            # Fetch and sync pricing
            records = client.get_dbaas_prices()
            
            if not records:
                print("No pricing records generated")
                return
            
            # Delete existing Beget managed DB pricing
            deleted_mysql = ProviderPrice.query.filter(
                ProviderPrice.provider == "beget",
                ProviderPrice.resource_type == "mysql-cluster"
            ).delete()
            
            deleted_pg = ProviderPrice.query.filter(
                ProviderPrice.provider == "beget",
                ProviderPrice.resource_type == "postgresql-cluster"
            ).delete()
            
            deleted_total = deleted_mysql + deleted_pg
            
            if deleted_total > 0:
                print(f"Deleted {deleted_total} existing Beget managed DB pricing records")
            
            # Insert new records
            inserted_count = 0
            for record in records:
                price = ProviderPrice(
                    provider=record["provider"],
                    resource_type=record["resource_type"],
                    provider_sku=record["provider_sku"],
                    region=record["region"],
                    cpu_cores=record["cpu_cores"],
                    ram_gb=record["ram_gb"],
                    storage_gb=record["storage_gb"],
                    storage_type=record["storage_type"],
                    extended_specs=json.dumps(record["extended_specs"]),
                    hourly_cost=record["hourly_cost"],
                    monthly_cost=record["monthly_cost"],
                    currency=record["currency"],
                    source=record["source"],
                    notes=record["notes"],
                    last_updated=datetime.utcnow()
                )
                db.session.add(price)
                inserted_count += 1
            
            db.session.commit()
            print(f"✅ Successfully inserted {inserted_count} managed DB pricing records")
            
            # Print summary by type
            from collections import Counter
            type_counts = Counter(r['resource_type'] for r in records)
            print()
            print("Summary by database type:")
            for db_type, count in type_counts.items():
                print(f"  • {db_type}: {count} configs")
            
            print()
            print("=" * 80)
            print(f"✅ SUCCESS: Synced {inserted_count} Beget managed DB pricing records")
            print("=" * 80)
            
        except Exception as e:
            print()
            print("=" * 80)
            print(f"❌ FAILED: {e}")
            print("=" * 80)
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()

