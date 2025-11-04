#!/usr/bin/env python3
"""
Fetch Selectel Managed Database (DBaaS) pricing and store in provider_prices table.

This script fetches pricing for Selectel's Managed Database service (PostgreSQL, MySQL, etc.)
from their billing API and calculates monthly costs for various configurations.

Usage:
    python selectel_dbaas_pricing_fetch.py
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

import requests


class SelectelDBaaSPricingClient:
    """Client for fetching Selectel Managed Database pricing."""
    
    BILLING_API_BASE = "https://api.selectel.ru"
    DBAAS_PRICES_ENDPOINT = "/v2/billing/dbaas/prices"
    
    def __init__(self, api_key: str):
        """Initialize the client with API key."""
        self.api_key = api_key
        self.session = requests.Session()
    
    def fetch_pricing_data(self, currency: str = "rub") -> Dict[str, Any]:
        """
        Fetch raw pricing data from Selectel billing API.
        
        Args:
            currency: Currency code (default: rub)
            
        Returns:
            Dict containing pricing data
        """
        url = f"{self.BILLING_API_BASE}{self.DBAAS_PRICES_ENDPOINT}"
        params = {"currency": currency}
        headers = {
            "X-Token": self.api_key,
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "InfraZenPricing/1.0",
        }
        
        print(f"Fetching DBaaS pricing from: {url}")
        response = self.session.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        if data.get("status") != "ok":
            raise ValueError(f"API returned non-ok status: {data.get('status')}")
        
        return data
    
    def _calculate_monthly_cost(self, hourly_kopeks: float, quantity: float = 1.0) -> float:
        """
        Calculate monthly cost from hourly rate in kopeks.
        
        Formula: (kopeks ÷ 100) × 730 hours × quantity
        
        Args:
            hourly_kopeks: Hourly rate in kopeks (Russian cents)
            quantity: Quantity multiplier (e.g., GB, vCPU count)
            
        Returns:
            Monthly cost in rubles
        """
        return (hourly_kopeks / 100.0) * 730.0 * quantity
    
    def generate_pricing_grid(self, pricing_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate a pricing grid for common DBaaS configurations.
        
        Args:
            pricing_data: Raw pricing data from API
            
        Returns:
            List of pricing records
        """
        prices = pricing_data.get("prices", [])
        currency = pricing_data.get("currency", "rub").upper()
        
        # Organize prices by region and resource type
        pricing_map = {}
        for price_entry in prices:
            resource = price_entry["resource"]
            region = price_entry["group"]
            value = price_entry["value"]
            
            if region not in pricing_map:
                pricing_map[region] = {}
            
            pricing_map[region][resource] = value
        
        # Common database configurations to generate
        # Expanded grid to cover real-world scenarios including high-storage databases
        configs = [
            # Small configs with various storage
            {"vcpu": 2, "ram_gb": 8, "disk_gb": 64, "platform": "standard"},
            {"vcpu": 2, "ram_gb": 8, "disk_gb": 128, "platform": "standard"},
            {"vcpu": 2, "ram_gb": 8, "disk_gb": 256, "platform": "standard"},
            {"vcpu": 2, "ram_gb": 8, "disk_gb": 512, "platform": "standard"},
            
            # Medium configs with various storage
            {"vcpu": 4, "ram_gb": 16, "disk_gb": 128, "platform": "standard"},
            {"vcpu": 4, "ram_gb": 16, "disk_gb": 256, "platform": "standard"},
            {"vcpu": 4, "ram_gb": 16, "disk_gb": 512, "platform": "standard"},
            {"vcpu": 4, "ram_gb": 16, "disk_gb": 1024, "platform": "standard"},
            
            # Large configs
            {"vcpu": 6, "ram_gb": 32, "disk_gb": 256, "platform": "standard"},
            {"vcpu": 6, "ram_gb": 32, "disk_gb": 512, "platform": "standard"},
            {"vcpu": 8, "ram_gb": 64, "disk_gb": 512, "platform": "standard"},
            {"vcpu": 8, "ram_gb": 64, "disk_gb": 1024, "platform": "standard"},
            {"vcpu": 10, "ram_gb": 96, "disk_gb": 768, "platform": "standard"},
            {"vcpu": 12, "ram_gb": 128, "disk_gb": 1024, "platform": "standard"},
            {"vcpu": 12, "ram_gb": 128, "disk_gb": 2048, "platform": "standard"},
            {"vcpu": 16, "ram_gb": 160, "disk_gb": 1536, "platform": "standard"},
            {"vcpu": 20, "ram_gb": 208, "disk_gb": 2048, "platform": "standard"},
        ]
        
        records = []
        
        for region, prices_dict in pricing_map.items():
            # Skip if missing required pricing components
            if "dbaas_compute_cores" not in prices_dict:
                continue
            if "dbaas_compute_ram" not in prices_dict:
                continue
            if "dbaas_volume_gigabytes_local" not in prices_dict:
                continue
            
            cpu_kopeks = prices_dict["dbaas_compute_cores"]
            ram_kopeks_per_mb = prices_dict["dbaas_compute_ram"]
            disk_kopeks = prices_dict["dbaas_volume_gigabytes_local"]
            
            # Calculate per-unit monthly costs
            cpu_monthly = self._calculate_monthly_cost(cpu_kopeks, quantity=1)
            ram_monthly_per_gb = self._calculate_monthly_cost(ram_kopeks_per_mb, quantity=1024)
            disk_monthly = self._calculate_monthly_cost(disk_kopeks, quantity=1)
            
            for config in configs:
                vcpu = config["vcpu"]
                ram_gb = config["ram_gb"]
                disk_gb = config["disk_gb"]
                platform = config["platform"]
                
                # Calculate total monthly cost for this configuration
                total_cpu_cost = cpu_monthly * vcpu
                total_ram_cost = ram_monthly_per_gb * ram_gb
                total_disk_cost = disk_monthly * disk_gb
                
                total_monthly = total_cpu_cost + total_ram_cost + total_disk_cost
                
                # Selectel uses UNIFIED pricing for all database types
                # All these DBMS use the same hardware pricing components
                dbaas_types = [
                    ("postgresql-cluster", "PostgreSQL"),
                    ("mysql-cluster", "MySQL"),
                    ("kafka-cluster", "Kafka"),
                    ("redis-cluster", "Redis"),
                    ("opensearch-cluster", "OpenSearch"),
                    ("timescaledb-cluster", "TimescaleDB"),
                    ("postgresql-1c-cluster", "PostgreSQL 1C"),
                ]
                
                # Generate pricing record for EACH database type (same cost for all)
                for resource_type, db_name in dbaas_types:
                    db_type_short = resource_type.replace('-cluster', '')
                    provider_sku = f"{db_type_short}-{platform}-{vcpu}c-{ram_gb}g-{disk_gb}d:{region}"
                    
                    records.append({
                        "provider": "selectel",
                        "resource_type": resource_type,
                        "provider_sku": provider_sku,
                        "region": region,
                        "cpu_cores": vcpu,
                        "ram_gb": float(ram_gb),
                        "storage_gb": float(disk_gb),
                        "storage_type": "local_ssd",  # Selectel DBaaS uses local NVMe SSD
                        "extended_specs": {
                            "platform": platform,
                            "database_type": db_type_short,
                            "pricing_method": "dbaas_api",
                            "components": {
                                "cpu_monthly": round(total_cpu_cost, 2),
                                "ram_monthly": round(total_ram_cost, 2),
                                "disk_monthly": round(total_disk_cost, 2),
                            },
                            "unit_rates": {
                                "cpu_per_vcpu": round(cpu_monthly, 2),
                                "ram_per_gb": round(ram_monthly_per_gb, 2),
                                "disk_per_gb": round(disk_monthly, 2),
                            },
                        },
                        "hourly_cost": None,
                        "monthly_cost": round(total_monthly, 2),
                        "currency": currency,
                        "source": "selectel_dbaas_api",
                        "notes": f"Managed {db_name} - {platform} platform with local NVMe SSD",
                    })
        
        return records
    
    def get_dbaas_prices(self) -> List[Dict[str, Any]]:
        """
        Fetch and generate DBaaS pricing records.
        
        Returns:
            List of pricing records ready for database insertion
        """
        print("Fetching Selectel DBaaS pricing...")
        pricing_data = self.fetch_pricing_data()
        
        print("Generating pricing grid...")
        records = self.generate_pricing_grid(pricing_data)
        
        print(f"Generated {len(records)} DBaaS pricing records")
        return records


def sync_dbaas_prices(api_key: str):
    """Sync Selectel DBaaS pricing to database."""
    client = SelectelDBaaSPricingClient(api_key)
    
    try:
        # Fetch pricing records
        records = client.get_dbaas_prices()
        
        if not records:
            print("No pricing records generated")
            return 0
        
        # Delete existing Selectel DBaaS pricing for all database types
        deleted_count = ProviderPrice.query.filter(
            ProviderPrice.provider == "selectel",
            ProviderPrice.resource_type.in_([
                "postgresql-cluster", "mysql-cluster", "kafka-cluster",
                "redis-cluster", "opensearch-cluster", "timescaledb-cluster",
                "postgresql-1c-cluster"
            ])
        ).delete()
        
        if deleted_count > 0:
            print(f"Deleted {deleted_count} existing Selectel DBaaS pricing records")
        
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
        print(f"✅ Successfully inserted {inserted_count} DBaaS pricing records")
        
        return inserted_count
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error syncing DBaaS prices: {e}")
        raise


def main():
    """Main entry point."""
    app = create_app()
    
    with app.app_context():
        print("=" * 80)
        print("SELECTEL MANAGED DATABASE (DBaaS) PRICING SYNC")
        print("=" * 80)
        print()
        
        # Get API key from ProviderAdminCredentials (same as VPC pricing sync)
        admin_creds = ProviderAdminCredentials.query.filter_by(
            provider_type='selectel'
        ).first()
        
        if not admin_creds:
            print("❌ ERROR: No admin credentials found for Selectel")
            print()
            print("Please configure Selectel admin credentials in the database")
            sys.exit(1)
        
        credentials = admin_creds.get_credentials()
        api_key = credentials.get('api_key')
        
        if not api_key:
            print("❌ ERROR: No API key found in Selectel credentials")
            print()
            print("Please add 'api_key' to Selectel admin credentials")
            sys.exit(1)
        
        print(f"Using Selectel API key from ProviderAdminCredentials")
        print()
        
        try:
            count = sync_dbaas_prices(api_key)
            print()
            print("=" * 80)
            print(f"✅ SUCCESS: Synced {count} Selectel DBaaS pricing records")
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

