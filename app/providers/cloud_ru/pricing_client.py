"""
Cloud.ru Pricing Client
Fetches pricing data for all Cloud.ru services
"""
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CloudRuPricingClient:
    """Collect Cloud.ru pricing via various pricing endpoints."""
    
    BASE_URL = "https://console.cloud.ru"
    
    def __init__(self, access_token: str, project_id: str):
        """
        Initialize Cloud.ru pricing client
        
        Args:
            access_token: Cloud.ru access token
            project_id: Cloud.ru project ID
        """
        self.access_token = access_token
        self.project_id = project_id
        self.session = self._create_session()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def _create_session(self):
        """Create HTTP session with authentication"""
        session = requests.Session()
        session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'InfraZenPricing/1.0'
        })
        return session
    
    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET request helper"""
        url = f"{self.BASE_URL}{endpoint}"
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def _post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """POST request helper"""
        url = f"{self.BASE_URL}{endpoint}"
        response = self.session.post(url, json=json_data, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def get_vm_prices(self) -> List[Dict[str, Any]]:
        """
        Get VM pricing by fetching flavors and calculating prices
        
        Returns standardized pricing records
        """
        pricing_records: List[Dict[str, Any]] = []
        
        try:
            # Fetch available flavors
            flavors_response = self._get(
                '/u-api/svp/svc/v1/flavors',
                params={
                    'project_id': self.project_id,
                    'limit': 100,
                    'offset': 0,
                    'type': 'general'
                }
            )
            
            flavors = flavors_response.get('items', [])
            self.logger.info(f"Found {len(flavors)} VM flavors")
            
            # Fetch disk types for storage pricing
            disk_types = self._get(
                '/u-api/svp/svc/v1/disk-types',
                params={'project_id': self.project_id}
            )
            
            # Get a default disk type (SSD) for VM pricing
            default_disk = next((dt for dt in disk_types if dt.get('name') == 'SSD'), disk_types[0] if disk_types else None)
            default_disk_size = 20  # GB
            
            # Calculate price for each flavor
            for flavor in flavors:
                try:
                    # Calculate price for this flavor
                    price_response = self._post(
                        f'/u-api/svp/svc/v1/projects/{self.project_id}/price-calculation',
                        json_data={
                            'total_count': 1,
                            'flavor_id': flavor.get('id'),
                            'disks': [{
                                'disk_type_id': default_disk.get('id') if default_disk else None,
                                'size': default_disk_size
                            }] if default_disk else []
                        }
                    )
                    
                    cpu = flavor.get('cpu', 0)
                    ram = flavor.get('ram', 0)
                    monthly_cost = price_response.get('total_price_month', 0.0)
                    hourly_cost = price_response.get('total_price_hour', 0.0)
                    
                    # Extract flavor name for identification
                    flavor_name = flavor.get('name', 'unknown')
                    oversubscription = flavor.get('oversubscription', '1:1')
                    
                    pricing_records.append({
                        'provider': 'cloud-ru',
                        'resource_type': 'server',
                        'flavor_id': flavor.get('id'),
                        'flavor_name': flavor_name,
                        'cpu_cores': cpu,
                        'ram_gb': ram,
                        'storage_gb': default_disk_size,
                        'hourly_cost': hourly_cost,
                        'monthly_cost': monthly_cost,
                        'oversubscription': oversubscription,
                        'region': 'ru',  # Cloud.ru is Russia-based
                        'currency': 'RUB',
                        'updated_at': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    self.logger.warning(f"Failed to get price for flavor {flavor.get('name')}: {e}")
                    continue
            
            self.logger.info(f"Collected {len(pricing_records)} VM pricing records")
            
        except Exception as e:
            self.logger.error(f"Failed to fetch VM prices: {e}", exc_info=True)
        
        return pricing_records
    
    def get_kubernetes_prices(self) -> List[Dict[str, Any]]:
        """
        Get Kubernetes pricing by fetching K8s flavors and calculating prices
        
        Returns standardized pricing records
        """
        pricing_records: List[Dict[str, Any]] = []
        
        try:
            # Fetch Kubernetes product configuration (flavors)
            k8s_config = self._get(
                '/u-api/mk8s-bff/v1/productConfiguration',
                params={'projectId': self.project_id}
            )
            
            # Extract flavors from configuration
            flavors = []
            if 'flavors' in k8s_config:
                flavors = k8s_config['flavors']
            elif 'data' in k8s_config and 'flavors' in k8s_config['data']:
                flavors = k8s_config['data']['flavors']
            
            self.logger.info(f"Found {len(flavors)} Kubernetes flavors")
            
            # Calculate price for each flavor (master node)
            for flavor in flavors:
                try:
                    flavor_id = flavor.get('flavorId') or flavor.get('id')
                    if not flavor_id:
                        continue
                    
                    # Calculate master node price
                    price_response = self._post(
                        '/u-api/mk8s/v2/billing/calculate-price-ext',
                        json_data={
                            'projectId': self.project_id,
                            'master': {
                                'count': 1,
                                'flavorId': flavor_id
                            },
                            'nodePoolPrices': [],
                            'volumePrices': []
                        }
                    )
                    
                    master_price = price_response.get('masterPrice', {})
                    price_info = master_price.get('price', {})
                    
                    # Extract hourly price (with VAT)
                    hourly_cost = price_info.get('streetPriceWithVatPerHour', 0.0)
                    # Calculate monthly (hourly * 730 hours)
                    monthly_cost = hourly_cost * 730
                    
                    cpu = flavor.get('cpu', 0)
                    ram = flavor.get('ram', 0)
                    resource_code = master_price.get('resourceCode', '')
                    
                    pricing_records.append({
                        'provider': 'cloud-ru',
                        'resource_type': 'kubernetes',
                        'flavor_id': flavor_id,
                        'flavor_name': flavor.get('name', 'unknown'),
                        'cpu_cores': cpu,
                        'ram_gb': ram,
                        'storage_gb': 0,  # K8s storage is separate
                        'hourly_cost': hourly_cost,
                        'monthly_cost': monthly_cost,
                        'resource_code': resource_code,
                        'region': 'ru',
                        'currency': 'RUB',
                        'updated_at': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    self.logger.warning(f"Failed to get price for K8s flavor {flavor.get('name')}: {e}")
                    continue
            
            self.logger.info(f"Collected {len(pricing_records)} Kubernetes pricing records")
            
        except Exception as e:
            self.logger.error(f"Failed to fetch Kubernetes prices: {e}", exc_info=True)
        
        return pricing_records
    
    def get_load_balancer_prices(self) -> List[Dict[str, Any]]:
        """
        Get Load Balancer pricing
        
        Note: Requires product_instance_id which we may not have.
        For now, we'll try common configurations.
        """
        pricing_records: List[Dict[str, Any]] = []
        
        try:
            # Load balancer pricing requires product_instance_id
            # We'll need to discover this or use a default configuration
            # For now, try with common availability zone count (3)
            # Note: This may fail if product_instance_id is required
            
            # Common configurations to try
            configs = [
                {'availability_zone_count': 3, 'with_external_address': True},
                {'availability_zone_count': 3, 'with_external_address': False},
                {'availability_zone_count': 1, 'with_external_address': True},
            ]
            
            # Try to get product instance ID from product list (if available)
            # For now, we'll skip if we can't get it
            # This is a limitation - we may need to get product_instance_id from resource discovery
            
            self.logger.warning("Load balancer pricing requires product_instance_id - skipping for now")
            # TODO: Implement when we have product_instance_id from resource discovery
            
        except Exception as e:
            self.logger.error(f"Failed to fetch Load Balancer prices: {e}", exc_info=True)
        
        return pricing_records
    
    def get_database_prices(self) -> List[Dict[str, Any]]:
        """
        Get Database pricing (PostgreSQL, Redis, MySQL, Kafka, etc.)
        
        Uses SKU-based pricing endpoint
        """
        pricing_records: List[Dict[str, Any]] = []
        
        try:
            # Database types to fetch
            db_types = [
                {'name': 'postgres', 'sku_prefix': 'paas_postgres'},
                {'name': 'redis', 'sku_prefix': 'paas_redis'},
                {'name': 'mysql', 'sku_prefix': 'paas_mysql'},
                {'name': 'kafka', 'sku_prefix': 'paas_kafka'},
            ]
            
            # Common SKU resources and tiers
            sku_resources = ['cpu', 'ram', 'storage']
            sku_tiers = ['standard', 'premium']
            sku_platforms = ['evolution']
            
            # We need product_instance_id for each database type
            # For now, we'll try to construct SKU codes and fetch prices
            # This is a simplified approach - in production, we'd need actual product_instance_ids
            
            for db_type in db_types:
                try:
                    # Construct SKU list
                    sku_list = []
                    for resource in sku_resources:
                        for tier in sku_tiers:
                            for platform in sku_platforms:
                                sku_code = f"{db_type['sku_prefix']}.{resource}#{tier}#{platform}"
                                sku_list.append(sku_code)
                    
                    # Try to get pricing (this may fail without product_instance_id)
                    # We'll need to discover product_instance_id from resource discovery
                    # For now, log that we need this
                    self.logger.debug(f"Database pricing for {db_type['name']} requires product_instance_id")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to get prices for {db_type['name']}: {e}")
                    continue
            
            self.logger.warning("Database pricing requires product_instance_id - skipping for now")
            # TODO: Implement when we have product_instance_id from resource discovery
            
        except Exception as e:
            self.logger.error(f"Failed to fetch Database prices: {e}", exc_info=True)
        
        return pricing_records
    
    def get_container_registry_prices(self) -> List[Dict[str, Any]]:
        """
        Get Container Registry pricing (tariff-based)
        
        Returns standardized pricing records
        """
        pricing_records: List[Dict[str, Any]] = []
        
        try:
            # Fetch tariffs
            tariffs = self._get(
                f'/u-api/container-registry/v1/api/v3/{self.project_id}/tariffs/'
            )
            
            # Tariffs are typically a list or dict with tariff plans
            tariff_list = []
            if isinstance(tariffs, list):
                tariff_list = tariffs
            elif isinstance(tariffs, dict):
                if 'tariffs' in tariffs:
                    tariff_list = tariffs['tariffs']
                elif 'items' in tariffs:
                    tariff_list = tariffs['items']
                else:
                    # Try to extract from dict values
                    tariff_list = list(tariffs.values()) if tariffs else []
            
            self.logger.info(f"Found {len(tariff_list)} Container Registry tariffs")
            
            for tariff in tariff_list:
                try:
                    tariff_name = tariff.get('name') or tariff.get('tariff_name', 'unknown')
                    price_str = tariff.get('price') or tariff.get('monthly_price') or tariff.get('price_per_month', '0')
                    
                    # Parse price string (may contain "≈" or other symbols)
                    # Remove non-numeric characters except decimal point
                    import re
                    price_match = re.search(r'[\d.]+', str(price_str))
                    monthly_cost = float(price_match.group()) if price_match else 0.0
                    
                    # Container Registry is typically flat-rate pricing
                    pricing_records.append({
                        'provider': 'cloud-ru',
                        'resource_type': 'container_registry',
                        'tariff_name': tariff_name,
                        'cpu_cores': 0,  # Not applicable
                        'ram_gb': 0,  # Not applicable
                        'storage_gb': 0,  # May be included in tariff
                        'hourly_cost': monthly_cost / 730,  # Approximate
                        'monthly_cost': monthly_cost,
                        'region': 'ru',
                        'currency': 'RUB',
                        'updated_at': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process Container Registry tariff: {e}")
                    continue
            
            self.logger.info(f"Collected {len(pricing_records)} Container Registry pricing records")
            
        except Exception as e:
            self.logger.error(f"Failed to fetch Container Registry prices: {e}", exc_info=True)
        
        return pricing_records
    
    def get_s3_prices(self) -> List[Dict[str, Any]]:
        """
        Get S3 Object Storage pricing
        
        S3 has no pricing API endpoint, so we use static unit prices from documentation
        """
        pricing_records: List[Dict[str, Any]] = []
        
        try:
            # Static pricing from Cloud.ru documentation
            # https://cloud.ru/docs/s3e/ug/topics/pricing
            # These are unit prices per GB/month for storage
            
            # Storage pricing (per GB/month)
            storage_price_per_gb_month = 1.5  # RUB per GB/month (approximate, from docs)
            
            # Traffic pricing (per GB)
            traffic_price_per_gb = 0.5  # RUB per GB (approximate, from docs)
            
            # Operations pricing (per 1000 requests)
            operations_price_per_1k = 0.01  # RUB per 1000 requests (approximate)
            
            # Create pricing records for different storage sizes
            storage_sizes = [10, 50, 100, 500, 1000, 5000, 10000]  # GB
            
            for size_gb in storage_sizes:
                monthly_cost = storage_price_per_gb_month * size_gb
                
                pricing_records.append({
                    'provider': 'cloud-ru',
                    'resource_type': 'object_storage',
                    'storage_gb': size_gb,
                    'cpu_cores': 0,  # Not applicable
                    'ram_gb': 0,  # Not applicable
                    'hourly_cost': monthly_cost / 730,
                    'monthly_cost': monthly_cost,
                    'unit_price_storage_per_gb_month': storage_price_per_gb_month,
                    'unit_price_traffic_per_gb': traffic_price_per_gb,
                    'unit_price_operations_per_1k': operations_price_per_1k,
                    'region': 'ru',
                    'currency': 'RUB',
                    'updated_at': datetime.now().isoformat(),
                    'note': 'Static pricing from documentation - actual costs vary by usage'
                })
            
            self.logger.info(f"Collected {len(pricing_records)} S3 pricing records (static)")
            
        except Exception as e:
            self.logger.error(f"Failed to fetch S3 prices: {e}", exc_info=True)
        
        return pricing_records
    
    def get_all_prices(self) -> List[Dict[str, Any]]:
        """
        Get all pricing data from Cloud.ru
        
        Returns combined list of all pricing records
        """
        all_prices: List[Dict[str, Any]] = []
        
        # VM pricing
        try:
            vm_prices = self.get_vm_prices()
            all_prices.extend(vm_prices)
        except Exception as e:
            self.logger.error(f"Failed to get VM prices: {e}")
        
        # Kubernetes pricing
        try:
            k8s_prices = self.get_kubernetes_prices()
            all_prices.extend(k8s_prices)
        except Exception as e:
            self.logger.error(f"Failed to get Kubernetes prices: {e}")
        
        # Load Balancer pricing (skipped for now - needs product_instance_id)
        # try:
        #     lb_prices = self.get_load_balancer_prices()
        #     all_prices.extend(lb_prices)
        # except Exception as e:
        #     self.logger.error(f"Failed to get Load Balancer prices: {e}")
        
        # Database pricing (skipped for now - needs product_instance_id)
        # try:
        #     db_prices = self.get_database_prices()
        #     all_prices.extend(db_prices)
        # except Exception as e:
        #     self.logger.error(f"Failed to get Database prices: {e}")
        
        # Container Registry pricing
        try:
            registry_prices = self.get_container_registry_prices()
            all_prices.extend(registry_prices)
        except Exception as e:
            self.logger.error(f"Failed to get Container Registry prices: {e}")
        
        # S3 pricing (static)
        try:
            s3_prices = self.get_s3_prices()
            all_prices.extend(s3_prices)
        except Exception as e:
            self.logger.error(f"Failed to get S3 prices: {e}")
        
        self.logger.info(f"Collected total of {len(all_prices)} pricing records")
        return all_prices

