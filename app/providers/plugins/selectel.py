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

    def get_vpc_prices(self) -> List[Dict[str, Any]]:
        response = requests.get(
            f"{self.BASE_URL}/vpc/prices",
            headers={
                "X-Token": self.api_key,
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "InfraZenPricing/1.0",
            },
            params={"currency": "rub"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        prices = []
        for item in data.get("prices", []):
            prices.append(
                {
                    "provider": "selectel",
                    "resource_type": "server" if item.get("resource", "").startswith("compute") else "unknown",
                    "provider_sku": f"{item.get('resource')}:{item.get('group')}",
                    "region": item.get("group"),
                    "cpu_cores": None,
                    "ram_gb": None,
                    "storage_gb": None,
                    "storage_type": None,
                    "extended_specs": {
                        "resource": item.get("resource"),
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
            timeout=30,
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

        price_map = self._fetch_price_map()
        regions = self._regions_from_price_map(price_map)

        # Balanced sampling grid
        vcpus_list = [1, 2, 4, 8, 16, 32]
        ram_gb_list = [1, 2, 4, 8, 16, 32, 64]
        disk_gb_list = [10, 50, 100, 200]

        records: List[Dict[str, Any]] = []
        for region in regions:
            for vcpus in vcpus_list:
                for ram_gb in ram_gb_list:
                    for disk_gb in disk_gb_list:
                        cpu_cost = self._get_price(price_map, "compute_cores", region, vcpus)
                        ram_cost = self._get_price(price_map, "compute_ram", region, ram_gb * 1024)
                        storage_cost = self._get_price(price_map, "volume_gigabytes_universal", region, disk_gb)
                        total_monthly = cpu_cost + ram_cost + storage_cost

                        provider_sku = f"v{vcpus}-r{ram_gb}-d{disk_gb}:{region}"

                        records.append(
                            {
                                "provider": "selectel",
                                "resource_type": "server",
                                "provider_sku": provider_sku,
                                "region": region,
                                "cpu_cores": vcpus,
                                "ram_gb": float(ram_gb),
                                "storage_gb": float(disk_gb),
                                "storage_type": "universal",
                                "extended_specs": {
                                    "pricing_method": "grid_from_matrix",
                                    "components": {
                                        "cpu_monthly": round(cpu_cost, 2),
                                        "ram_monthly": round(ram_cost, 2),
                                        "storage_monthly": round(storage_cost, 2),
                                    },
                                },
                                "hourly_cost": None,
                                "monthly_cost": round(total_monthly, 2),
                                "currency": "RUB",
                                "source": "selectel_vpc_grid",
                                "notes": "Generated from VPC billing matrix",
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

            # Prefer grid pricing with normalized CPU/RAM/Disk fields
            grid = self.grid_pricing_client.get_grid_prices()
            if grid:
                self.logger.info("Collected %d Selectel grid pricing records", len(grid))
                return grid

            # Fallback to raw price matrix rows if grid failed
            return self.pricing_client.get_vpc_prices()
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
