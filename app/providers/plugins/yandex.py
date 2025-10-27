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
        """Get complete pricing data for Yandex Cloud resources using individual SKU calls"""
        try:
            from ..yandex.client import YandexClient
            import time
            import requests
            
            self.logger.info("Starting complete Yandex Cloud pricing sync...")
            
            client = YandexClient(self.credentials)
            
            # Step 1: Get all SKU IDs from list API (fast)
            self.logger.info("Fetching SKU list...")
            all_sku_ids = []
            page_token = None
            page_num = 1
            
            while True:
                self.logger.info(f"Fetching SKU list page {page_num}...")
                result = client.list_skus(page_size=1000, page_token=page_token)
                
                if not result or 'skus' not in result:
                    break
                
                skus = result.get('skus', [])
                if not skus:
                    break
                
                # Collect all SKU IDs (including zero-price ones)
                for sku in skus:
                    all_sku_ids.append(sku.get('id'))
                
                self.logger.info(f"Page {page_num}: Collected {len(skus)} SKU IDs (total: {len(all_sku_ids)})")
                
                page_token = result.get('nextPageToken')
                if not page_token:
                    break
                
                page_num += 1
            
            self.logger.info(f"Collected {len(all_sku_ids)} total SKU IDs")
            
            # Step 2: Fetch individual SKU details (with progress tracking)
            pricing_data = []
            successful_fetches = 0
            failed_fetches = 0
            start_time = time.time()
            timeout_seconds = 20 * 60  # 20 minutes
            
            headers = client._get_headers()
            
            for i, sku_id in enumerate(all_sku_ids):
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    self.logger.warning(f"Timeout reached after {elapsed:.1f}s. Processed {i}/{len(all_sku_ids)} SKUs")
                    break
                
                try:
                    # Fetch individual SKU details
                    url = f'{client.billing_url}/skus/{sku_id}'
                    response = requests.get(url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        sku_data = response.json()
                        
                        # Extract pricing information
                        pricing_versions = sku_data.get('pricingVersions', [])
                        if not pricing_versions:
                            continue
                        
                        # Get the latest pricing version (most recent effectiveTime)
                        latest_pricing = max(pricing_versions, key=lambda x: x.get('effectiveTime', ''))
                        
                        # Extract rates
                        pricing_expressions = latest_pricing.get('pricingExpressions', [])
                        if not pricing_expressions:
                            continue
                        
                        rates_data = pricing_expressions[0]
                        rates = rates_data.get('rates', [])
                        if not rates:
                            continue
                        
                        first_rate = rates[0]
                        unit_price = float(first_rate.get('unitPrice', 0))
                        
                        # Skip zero-price SKUs
                        if unit_price == 0:
                            continue
                        
                        # Parse pricing unit to determine resource specs
                        pricing_unit = sku_data.get('pricingUnit', '')
                        cpu_cores = None
                        ram_gb = None
                        storage_gb = None
                        notes = f"Price per {pricing_unit}"
                        
                        if 'core*hour' in pricing_unit or 'core*month' in pricing_unit:
                            cpu_cores = 1
                        elif 'gbyte*hour' in pricing_unit or 'gbyte*month' in pricing_unit:
                            ram_gb = 1
                        elif 'gbyte' in pricing_unit and 'storage' in sku_data.get('name', '').lower():
                            storage_gb = 1
                        elif 'server*month' in pricing_unit:
                            # BareMetal servers - treat as complete server
                            cpu_cores = 1  # Will be overridden by name parsing
                            ram_gb = 1
                        
                        # Parse SKU name for additional specs
                        sku_name = sku_data.get('name', '')
                        if 'vCPU' in sku_name or 'CPU' in sku_name:
                            cpu_cores = 1
                        elif 'RAM' in sku_name or 'memory' in sku_name:
                            ram_gb = 1
                        elif 'storage' in sku_name.lower() or 'disk' in sku_name.lower():
                            storage_gb = 1
                        
                        # Calculate monthly cost based on pricing unit
                        if 'month' in pricing_unit:
                            monthly_cost = unit_price
                            hourly_cost = unit_price / 730  # Approximate
                        else:  # hour
                            hourly_cost = unit_price
                            monthly_cost = unit_price * 730  # Approximate
                        
                        pricing_data.append({
                            'provider': 'yandex',
                            'provider_sku': sku_id,
                            'resource_type': self._categorize_sku(sku_name),
                            'cpu_cores': cpu_cores,
                            'ram_gb': ram_gb,
                            'storage_gb': storage_gb,
                            'hourly_cost': hourly_cost,
                            'monthly_cost': monthly_cost,
                            'currency': first_rate.get('currency', 'RUB'),
                            'source': 'billing_api',
                            'notes': notes,
                            'extended_specs': {
                                'sku_id': sku_id,
                                'sku_name': sku_name,
                                'service_id': sku_data.get('serviceId'),
                                'pricing_unit': pricing_unit,
                                'pricing_type': latest_pricing.get('type', 'STREET_PRICE'),
                                'effective_time': latest_pricing.get('effectiveTime'),
                                'description': sku_data.get('description', '')
                            }
                        })
                        
                        successful_fetches += 1
                        
                        # Log progress every 50 SKUs
                        if successful_fetches % 50 == 0:
                            elapsed = time.time() - start_time
                            rate = successful_fetches / elapsed if elapsed > 0 else 0
                            remaining = (len(all_sku_ids) - i) / rate if rate > 0 else 0
                            self.logger.info(f"Progress: {successful_fetches} SKUs with prices, {i+1}/{len(all_sku_ids)} total, {rate:.1f} SKUs/sec, ~{remaining/60:.1f}min remaining")
                    
                    else:
                        failed_fetches += 1
                        if failed_fetches <= 5:  # Log first 5 failures
                            self.logger.warning(f"Failed to fetch SKU {sku_id}: {response.status_code}")
                    
                    # Small delay to avoid rate limiting
                    time.sleep(0.1)
                    
                except Exception as e:
                    failed_fetches += 1
                    if failed_fetches <= 5:
                        self.logger.warning(f"Exception fetching SKU {sku_id}: {e}")
            
            elapsed = time.time() - start_time
            self.logger.info(f"Complete pricing sync finished: {successful_fetches} SKUs with prices, {failed_fetches} failures, {elapsed:.1f}s elapsed")
            
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

