"""
Selectel provider plugin
Wraps existing Selectel functionality in the new plugin architecture
"""
import logging
from typing import Dict, List, Any
from datetime import datetime

import requests
import requests

from ..plugin_system import ProviderPlugin, SyncResult
from ..selectel.client import SelectelClient
from ..resource_registry import resource_registry, ProviderResource

logger = logging.getLogger(__name__)


class SelectelPricingClient:
    """Collect Selectel VPC pricing via public billing API."""

    BASE_URL = "https://api.selectel.ru/v2/billing"

    def __init__(self, api_key: str):
        self.api_key = api_key

    @staticmethod
    def _map_resource_type(resource_key: str) -> str:
        """Map Selectel billing resource keys to our taxonomy resource_type."""
        if not resource_key:
            return "unknown"

        rk = resource_key.lower()
        # Compute / VM related
        if rk.startswith("compute_"):
            return "server"
        # Block/File storage
        if rk.startswith("volume_") or rk.startswith("share_"):
            return "volume"
        if rk.startswith("snapshot_") or rk.startswith("volume_backup"):
            return "snapshot"
        # Databases
        if rk.startswith("dbaas_"):
            return "database"
        # Kubernetes
        if rk.startswith("mks_") or rk.startswith("k8s_"):
            return "kubernetes"
        # Network
        if rk.startswith("network_") or rk.startswith("exttraffic") or rk.startswith("floatingip"):
            return "network"
        # Load balancers
        if rk.startswith("load_balancer") or rk.startswith("load_balancers_"):
            return "load_balancer"
        # Images / Licenses / Software
        if rk.startswith("image_"):
            return "image"
        if rk.startswith("license_"):
            return "license"
        # AI/inference
        if rk.startswith("inference_"):
            return "ai_service"
        return "unknown"

    def get_vpc_prices(self) -> List[Dict[str, Any]]:
        response = requests.get(
            f"{self.BASE_URL}/vpc/prices",
            headers={
                "X-Token": self.api_key,
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "InfraZenPricing/1.0",
            },
            params={"currency": "rub"},
            timeout=90,
        )
        response.raise_for_status()
        data = response.json()
        prices = []
        for item in data.get("prices", []):
            resource_key = item.get("resource", "")
            mapped_type = self._map_resource_type(resource_key)
            prices.append(
                {
                    "provider": "selectel",
                    "resource_type": mapped_type,
                    "provider_sku": f"{resource_key}:{item.get('group')}",
                    "region": item.get("group"),
                    "cpu_cores": None,
                    "ram_gb": None,
                    "storage_gb": None,
                    "storage_type": None,
                    "extended_specs": {
                        "resource": resource_key,
                        "unit": item.get("unit"),
                    },
                    "hourly_cost": None,
                    "monthly_cost": item.get("value"),
                    "currency": data.get("currency", "rub").upper(),
                    "source": "selectel_vpc_api",
                    "notes": "Selectel VPC billing price entry",
                }
            )
        return prices


class SelectelGridPricingClient:
    """Build grid pricing (CPU/RAM/Disk) from Selectel VPC billing matrix."""

    BASE_URL = "https://api.selectel.ru/v2/billing"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _fetch_price_map(self) -> Dict[str, Dict[str, Any]]:
        response = requests.get(
            f"{self.BASE_URL}/vpc/prices",
            headers={
                "X-Token": self.api_key,
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "InfraZenPricing/1.0",
            },
            params={"currency": "rub"},
            timeout=90,
        )
        response.raise_for_status()
        prices = response.json().get("prices", [])
        price_map: Dict[str, Dict[str, Any]] = {}
        for p in prices:
            price_map[f"{p.get('resource')}:{p.get('group')}"] = p
        return price_map

    @staticmethod
    def _regions_from_price_map(price_map: Dict[str, Dict[str, Any]]) -> List[str]:
        regions = set()
        for key in price_map.keys():
            if key.startswith("compute_cores:"):
                regions.add(key.split(":", 1)[1])
        return sorted(regions)

    @staticmethod
    def _get_price(price_map: Dict[str, Dict[str, Any]], resource: str, region: str, multiplier: float = 1.0) -> float:
        entry = price_map.get(f"{resource}:{region}")
        if not entry:
            return 0.0
        return float(entry.get("value", 0.0)) * float(multiplier)

    def get_grid_prices(self) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []

        # Retail multiplier for Selectel "Произвольная" UI pricing.
        # The VPC matrix returns base per-unit prices; the UI applies an
        # approximately 7.3x coefficient consistently to CPU, RAM and Disk
        # components in the custom configurator. We mirror that here so our
        # stored monthly_cost reflects the retail price users see.
        import os
        try:
            retail_multiplier = float(os.getenv("SELECTEL_RETAIL_MULTIPLIER", "7.3"))
        except ValueError:
            retail_multiplier = 7.3

        price_map = self._fetch_price_map()
        regions = self._regions_from_price_map(price_map)

        # Balanced sampling grid
        # Expanded to cover real-world workloads including large storage (databases, GitLab, etc.)
        vcpus_list = [1, 2, 4, 8, 16, 32]
        ram_gb_list = [1, 2, 4, 8, 12, 16, 32, 64]  # Added 12 GB for database/app server workloads
        disk_gb_list = [10, 50, 100, 128, 200, 512, 1024]  # Added 128 GB for K8s nodes, 512 GB, 1 TB for databases

        # Selectel storage types for FinOps comparison:
        # - volume_gigabytes_basic -> HDD Базовый (cheapest HDD)
        # - volume_gigabytes_universal2 -> SSD Универсальный v2 (cheapest SSD, monthly billing)
        # 
        # Note: Skipping performance tiers (Fast SSD, v1 hourly billing) as Yandex doesn't
        # expose IOPS/performance metrics - we focus on price comparison with basic matching
        # 
        # Mapping to normalized storage types:
        # - 'hdd' matches Yandex 'network-hdd' → 'hdd'
        # - 'network_ssd' matches Yandex 'network-ssd' → 'network_ssd'
        storage_configs = [
            ("volume_gigabytes_basic", "hdd", "HDD Базовый"),
            ("volume_gigabytes_universal2", "network_ssd", "SSD Универсальный v2"),
        ]

        records: List[Dict[str, Any]] = []
        for region in regions:
            for vcpus in vcpus_list:
                for ram_gb in ram_gb_list:
                    for disk_gb in disk_gb_list:
                        cpu_cost = self._get_price(price_map, "compute_cores", region, vcpus)
                        ram_cost = self._get_price(price_map, "compute_ram", region, ram_gb * 1024)
                        
                        # Generate pricing for each storage type
                        for storage_resource, storage_type, storage_label in storage_configs:
                            storage_cost = self._get_price(price_map, storage_resource, region, disk_gb)
                            total_monthly_base = cpu_cost + ram_cost + storage_cost
                            # Apply retail multiplier to reflect UI pricing
                            total_monthly = total_monthly_base * retail_multiplier

                            # Only include if pricing is available for this storage type
                            if storage_cost > 0:
                                provider_sku = f"v{vcpus}-r{ram_gb}-d{disk_gb}-{storage_type}:{region}"

                                records.append(
                                    {
                                        "provider": "selectel",
                                        "resource_type": "server",
                                        "provider_sku": provider_sku,
                                        "region": region,
                                        "cpu_cores": vcpus,
                                        "ram_gb": float(ram_gb),
                                        "storage_gb": float(disk_gb),
                                        "storage_type": storage_type,
                                        "extended_specs": {
                                            "pricing_method": "grid_from_matrix",
                                            "storage_type_label": storage_label,
                                            "storage_resource": storage_resource,
                                            "components": {
                                                "cpu_monthly": round(cpu_cost * retail_multiplier, 2),
                                                "ram_monthly": round(ram_cost * retail_multiplier, 2),
                                                "storage_monthly": round(storage_cost * retail_multiplier, 2),
                                            },
                                            "retail_multiplier": retail_multiplier,
                                            "base_components": {
                                                "cpu_monthly": round(cpu_cost, 2),
                                                "ram_monthly": round(ram_cost, 2),
                                                "storage_monthly": round(storage_cost, 2),
                                                "total_base": round(total_monthly_base, 2),
                                            },
                                        },
                                        "hourly_cost": None,
                                        "monthly_cost": round(total_monthly, 2),
                                        "currency": "RUB",
                                        "source": "selectel_vpc_grid",
                                        "notes": f"Generated from VPC billing matrix - {storage_label}",
                                    }
                                )

        return records

class SelectelProviderPlugin(ProviderPlugin):
    """Selectel provider plugin implementation"""

    __version__ = "1.0.0"

    def __init__(self, provider_id: int, credentials: Dict[str, Any], config: Dict[str, Any] = None):
        super().__init__(provider_id, credentials, config)

        # Add account_id to credentials for OpenStack authentication
        credentials_with_account = credentials.copy()
        credentials_with_account['account_id'] = config.get('account_id') if config else None

        # Initialize Selectel client
        self.client = SelectelClient(credentials_with_account)
        self.pricing_client = SelectelPricingClient(credentials.get('api_key', ''))
        self.grid_pricing_client = SelectelGridPricingClient(credentials.get('api_key', ''))

    def get_provider_type(self) -> str:
        return "selectel"

    def get_provider_name(self) -> str:
        return "Selectel Cloud"

    def get_required_credentials(self) -> List[str]:
        return ['username', 'password', 'account_id']

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            'supports_resources': True,
            'supports_metrics': True,
            'supports_cost_data': True,
            'supports_logs': False,
            'supports_vms': True,
            'supports_volumes': True,
            'supports_kubernetes': True,
            'supports_databases': True,
            'supports_s3': True,
            'supports_load_balancers': True,
            'api_endpoints': ['billing', 'compute', 'storage', 'network'],
            'regions': ['ru-1', 'ru-2', 'ru-3', 'ru-7', 'ru-8', 'ru-9', 'kz-1'],
            'billing_model': 'pay-as-you-go',
            'sync_method': 'billing_first'
        }

    def get_resource_mappings(self) -> Dict[str, Any]:
        return {
            'server': {
                'type': 'server',
                'service': 'Compute',
                'category': 'infrastructure'
            },
            'volume': {
                'type': 'volume',
                'service': 'Block Storage',
                'category': 'storage'
            },
            'file_storage': {
                'type': 'file_storage',
                'service': 'File Storage',
                'category': 'storage'
            },
            'database': {
                'type': 'database',
                'service': 'Database',
                'category': 'data'
            },
            'kubernetes_cluster': {
                'type': 'kubernetes_cluster',
                'service': 'Kubernetes',
                'category': 'containers'
            },
            'kubernetes_nodegroup': {
                'type': 'kubernetes_nodegroup',
                'service': 'Kubernetes',
                'category': 'containers'
            },
            's3_bucket': {
                'type': 's3_bucket',
                'service': 'Object Storage',
                'category': 'storage'
            },
            'load_balancer': {
                'type': 'load_balancer',
                'service': 'Network',
                'category': 'networking'
            },
            'floating_ip': {
                'type': 'floating_ip',
                'service': 'Network',
                'category': 'networking'
            }
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Selectel APIs"""
        try:
            result = self.client.test_connection()

            return {
                'success': result.get('success', False),
                'message': result.get('message', 'Connection test completed'),
                'account_info': result.get('account_info', {}),
                'api_status': 'connected' if result.get('success') else 'failed',
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Selectel connection test failed: {e}")
            return {
                'success': False,
                'message': f'Connection test failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }

    def get_pricing_data(self) -> List[Dict[str, Any]]:
        try:
            if not self.pricing_client.api_key:
                self.logger.warning("No API key provided for Selectel pricing fetch")
                return []

            # Collect grid pricing with normalized CPU/RAM/Disk fields
            grid = self.grid_pricing_client.get_grid_prices()
            self.logger.info("Collected %d Selectel grid pricing records", len(grid))

            # Also collect raw unit prices across services (volumes, network, dbaas, etc.)
            raw = self.pricing_client.get_vpc_prices()
            self.logger.info("Collected %d Selectel raw unit price records", len(raw))

            # Collect managed database pricing (PostgreSQL, MySQL, Kafka, Redis, etc.)
            try:
                from scripts.selectel_dbaas_pricing_fetch import SelectelDBaaSPricingClient
                dbaas_client = SelectelDBaaSPricingClient(self.pricing_client.api_key)
                dbaas = dbaas_client.get_dbaas_prices()
                self.logger.info("Collected %d Selectel DBaaS pricing records", len(dbaas))
            except Exception as dbaas_error:
                self.logger.warning(f"Failed to fetch DBaaS pricing: {dbaas_error}")
                dbaas = []

            # Note: Container Registry pricing not included - resource type excluded from price comparison
            # due to lack of storage size in API and high migration complexity

            # Combine so UI can filter by resource_type across categories
            return (grid or []) + (raw or []) + (dbaas or [])
        except Exception as exc:
            self.logger.error("Failed to collect Selectel pricing: %s", exc, exc_info=True)
            return []

    def sync_resources(self) -> SyncResult:
        """Perform billing-first sync for Selectel"""
        result = SyncResult(success=False, message="Sync not started", provider_type=self.get_provider_type())

        try:
            self.logger.info(f"Starting Selectel billing-first sync for provider {self.provider_id}")

            # Use the existing SelectelService sync method
            from ..selectel.service import SelectelService
            from app.core.models.provider import CloudProvider

            # Get provider instance
            provider = CloudProvider.query.get(self.provider_id)
            if not provider:
                result.message = f"Provider {self.provider_id} not found"
                result.errors = ["Provider not found in database"]
                return result

            # Create service instance
            service = SelectelService(provider)

            # Perform sync
            sync_result = service.sync_resources()

            # Convert to plugin result format
            result.success = sync_result.get('success', False)
            result.message = sync_result.get('message', 'Sync completed')
            result.resources_synced = sync_result.get('resources_synced', 0)
            result.total_cost = sync_result.get('total_daily_cost', 0.0)
            result.errors = sync_result.get('errors', [])

            # Add sync data
            result.data = {
                'sync_details': sync_result,
                'sync_snapshot_id': sync_result.get('sync_snapshot_id'),
                'orphan_volumes': sync_result.get('orphan_volumes', 0),
                'zombie_resources': sync_result.get('zombie_resources', 0),
                'service_types': sync_result.get('service_types', []),
                'sync_timestamp': datetime.now().isoformat()
            }

            self.logger.info(f"Selectel sync completed: {result.resources_synced} resources, {result.total_cost:.2f} RUB/day")

        except Exception as e:
            error_msg = f"Selectel sync failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            result.message = error_msg
            result.errors = [str(e)]

        return result
