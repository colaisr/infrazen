"""
Yandex Cloud provider plugin
Wraps existing Yandex Cloud functionality in the plugin architecture
"""
import logging
from typing import Dict, List, Any
from datetime import datetime

from ..plugin_system import ProviderPlugin, SyncResult

logger = logging.getLogger(__name__)


class YandexProviderPlugin(ProviderPlugin):
    """Yandex Cloud provider plugin implementation"""

    __version__ = "1.0.0"

    def __init__(self, provider_id: int, credentials: Dict[str, Any], config: Dict[str, Any] = None):
        super().__init__(provider_id, credentials, config)

    def get_provider_type(self) -> str:
        return "yandex"

    def get_provider_name(self) -> str:
        return "Yandex Cloud"

    def get_required_credentials(self) -> List[str]:
        return ['service_account_key']

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            'supports_resources': True,
            'supports_metrics': True,  # CPU metrics via Monitoring API
            'supports_cost_data': True,  # Cost estimation (billing API future)
            'supports_logs': False,
            'supports_vms': True,
            'supports_volumes': True,
            'supports_kubernetes': False,  # Not implemented yet
            'supports_databases': False,  # Not implemented yet
            'supports_s3': False,  # Not implemented yet
            'supports_load_balancers': False,  # Not implemented yet
            'api_endpoints': ['compute', 'vpc', 'resource_manager', 'monitoring', 'iam'],
            'regions': ['ru-central1-a', 'ru-central1-b', 'ru-central1-c', 'ru-central1-d'],
            'billing_model': 'pay-as-you-go',
            'sync_method': 'resource_discovery'
        }

    def get_resource_mappings(self) -> Dict[str, Any]:
        return {
            'server': {
                'type': 'server',
                'service': 'Compute Cloud',
                'category': 'infrastructure'
            },
            'volume': {
                'type': 'volume',
                'service': 'Block Storage',
                'category': 'storage'
            },
            'network': {
                'type': 'network',
                'service': 'VPC',
                'category': 'networking'
            },
            'subnet': {
                'type': 'subnet',
                'service': 'VPC',
                'category': 'networking'
            }
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Yandex Cloud APIs"""
        try:
            from ..yandex.client import YandexClient
            
            client = YandexClient(self.credentials)
            result = client.test_connection()

            return {
                'success': result.get('success', False),
                'message': result.get('message', 'Connection test completed'),
                'account_info': result.get('account_info', {}),
                'api_status': 'connected' if result.get('success') else 'failed',
                'timestamp': datetime.now().isoformat(),
                'clouds': result.get('clouds', []),
                'folders': result.get('folders', [])
            }

        except Exception as e:
            self.logger.error(f"Yandex Cloud connection test failed: {e}")
            return {
                'success': False,
                'message': f'Connection test failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }

    def sync_resources(self) -> SyncResult:
        """Perform resource discovery sync for Yandex Cloud"""
        result = SyncResult(success=False, message="Sync not started", provider_type=self.get_provider_type())

        try:
            self.logger.info(f"Starting Yandex Cloud resource sync for provider {self.provider_id}")

            # Use the existing YandexService sync method
            from ..yandex.service import YandexService
            from app.core.models.provider import CloudProvider

            # Get provider instance
            provider = CloudProvider.query.get(self.provider_id)
            if not provider:
                result.message = f"Provider {self.provider_id} not found"
                result.errors = ["Provider not found in database"]
                return result

            # Create service instance
            service = YandexService(provider)

            # Perform sync
            sync_result = service.sync_resources()

            # Convert to plugin result format
            result.success = sync_result.get('success', False)
            result.message = sync_result.get('message', 'Sync completed')
            result.resources_synced = sync_result.get('resources_synced', 0)
            
            # Handle different cost field names
            result.total_cost = (
                sync_result.get('total_cost') or 
                sync_result.get('estimated_daily_cost') or 
                sync_result.get('total_daily_cost') or 
                0.0
            )
            
            result.errors = sync_result.get('errors', [])

            # Add sync data
            result.data = {
                'sync_details': sync_result,
                'sync_snapshot_id': sync_result.get('sync_snapshot_id'),
                'total_instances': sync_result.get('total_instances', 0),
                'total_disks': sync_result.get('total_disks', 0),
                'cpu_stats_collected': sync_result.get('cpu_stats_collected', False),
                'sync_timestamp': datetime.now().isoformat()
            }

            self.logger.info(f"Yandex Cloud sync completed: {result.resources_synced} resources, {result.total_cost:.2f} RUB/day")

        except Exception as e:
            error_msg = f"Yandex Cloud sync failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            result.message = error_msg
            result.errors = [str(e)]

        return result

    def get_pricing_data(self) -> List[Dict[str, Any]]:
        """Get pricing data for Yandex Cloud resources from SKU catalog"""
        try:
            from ..yandex.client import YandexClient
            
            self.logger.info("Fetching Yandex Cloud SKU pricing catalog...")
            
            # Create client with credentials
            client = YandexClient(self.credentials)
            
            # Fetch all SKUs (paginated)
            all_skus = []
            page_token = None
            page_num = 1
            
            while True:
                self.logger.info(f"Fetching SKU page {page_num}...")
                result = client.list_skus(page_size=1000, page_token=page_token)
                
                if not result or 'skus' not in result:
                    break
                
                skus = result.get('skus', [])
                if not skus:
                    break
                
                all_skus.extend(skus)
                self.logger.info(f"Page {page_num}: Fetched {len(skus)} SKUs (total: {len(all_skus)})")
                
                page_token = result.get('nextPageToken')
                if not page_token:
                    break
                
                page_num += 1
            
            self.logger.info(f"Fetched {len(all_skus)} total SKUs from Yandex Cloud")
            
            # Convert SKUs to pricing format
            pricing_data = []
            for sku in all_skus:
                pricing_versions = sku.get('pricingVersions', [])
                if not pricing_versions:
                    continue
                
                # Get latest pricing
                latest_pricing = pricing_versions[0]
                pricing_expressions = latest_pricing.get('pricingExpressions', [])
                if not pricing_expressions:
                    continue
                
                rates_data = pricing_expressions[0]
                rates = rates_data.get('rates', [])
                if not rates:
                    continue
                
                first_rate = rates[0]
                unit_price = float(first_rate.get('unitPrice', 0))
                
                # Skip zero-price SKUs (they clutter the catalog)
                if unit_price == 0:
                    continue
                
                # Map to ProviderPrice model fields
                pricing_data.append({
                    'provider': 'yandex',
                    'provider_sku': sku.get('id'),  # SKU ID
                    'resource_type': self._categorize_sku(sku.get('name', '')),
                    'hourly_cost': unit_price,  # Price is per hour
                    'monthly_cost': unit_price * 730,  # Approximate hours per month
                    'currency': first_rate.get('currency', 'RUB'),
                    'source': 'billing_api',
                    'extended_specs': {
                        'sku_id': sku.get('id'),
                        'sku_name': sku.get('name'),
                        'service_id': sku.get('serviceId'),
                        'pricing_unit': rates_data.get('pricingUnit', 'hour'),
                        'pricing_type': latest_pricing.get('type', 'STREET_PRICE'),
                        'effective_time': latest_pricing.get('effectiveTime'),
                        'description': sku.get('description', '')
                    }
                })
            
            self.logger.info(f"Converted {len(pricing_data)} SKUs with prices > 0 to pricing format")
            return pricing_data
            
        except Exception as exc:
            self.logger.error("Failed to collect Yandex pricing: %s", exc, exc_info=True)
            return []
    
    def _categorize_sku(self, sku_name: str) -> str:
        """Categorize SKU by name into resource type"""
        name_lower = sku_name.lower()
        
        if any(kw in name_lower for kw in ['vcpu', 'cpu', 'core', 'processor']):
            return 'compute_cpu'
        elif any(kw in name_lower for kw in ['ram', 'memory']):
            return 'compute_ram'
        elif any(kw in name_lower for kw in ['disk', 'storage', 'hdd', 'ssd', 'nvme']):
            return 'storage'
        elif 'kubernetes' in name_lower or 'k8s' in name_lower:
            return 'kubernetes'
        elif 'postgresql' in name_lower or 'postgres' in name_lower:
            return 'database_postgresql'
        elif 'mysql' in name_lower:
            return 'database_mysql'
        elif 'mongodb' in name_lower or 'mongo' in name_lower:
            return 'database_mongodb'
        elif 'clickhouse' in name_lower:
            return 'database_clickhouse'
        elif 'redis' in name_lower or 'valkey' in name_lower:
            return 'database_redis'
        elif 'kafka' in name_lower:
            return 'database_kafka'
        elif 'vpc' in name_lower or 'network' in name_lower or 'subnet' in name_lower:
            return 'networking'
        elif 'dns' in name_lower:
            return 'dns'
        elif 's3' in name_lower or 'object storage' in name_lower:
            return 's3'
        elif 'kms' in name_lower or 'key management' in name_lower:
            return 'kms'
        elif 'load balancer' in name_lower or 'balancer' in name_lower:
            return 'load_balancer'
        elif 'container registry' in name_lower or 'registry' in name_lower:
            return 'container_registry'
        else:
            return 'other'

