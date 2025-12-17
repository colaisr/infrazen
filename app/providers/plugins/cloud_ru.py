"""
Cloud.ru provider plugin
Implements Cloud.ru provider integration using the plugin architecture
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..plugin_system import ProviderPlugin, SyncResult
from ..cloud_ru.client import CloudRuClient

logger = logging.getLogger(__name__)


class CloudRuProviderPlugin(ProviderPlugin):
    """Cloud.ru provider plugin implementation"""

    __version__ = "1.0.0"

    def __init__(self, provider_id: int, credentials: Dict[str, Any], config: Dict[str, Any] = None):
        super().__init__(provider_id, credentials, config)
        
        # Initialize Cloud.ru client
        self.client = CloudRuClient(credentials)

    def get_provider_type(self) -> str:
        return "cloud-ru"

    def get_provider_name(self) -> str:
        return "Cloud.ru"

    def get_required_credentials(self) -> List[str]:
        return ['api_key', 'api_secret']

    def get_capabilities(self) -> Dict[str, Any]:
        """Return Cloud.ru provider capabilities"""
        return {
            'supports_resources': True,
            'supports_metrics': False,  # To be determined during API research
            'supports_cost_data': True,  # Billing API available
            'supports_logs': False,
            'supports_vms': True,  # Virtual machines
            'supports_volumes': True,  # Block storage
            'supports_kubernetes': False,  # To be determined
            'supports_databases': False,  # To be determined
            'supports_s3': False,  # To be determined
            'supports_load_balancers': False,  # To be determined
            'api_endpoints': ['iam', 'compute', 'billing'],  # Based on initial research
            'regions': [],  # To be populated during API research
            'billing_model': 'pay-as-you-go',
            'sync_method': 'billing_first'  # Will use billing-first approach like Selectel
        }

    def get_resource_mappings(self) -> Dict[str, Any]:
        """Map Cloud.ru resource types to unified taxonomy"""
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
            'snapshot': {
                'type': 'snapshot',
                'service': 'Block Storage',
                'category': 'storage'
            },
            # Additional mappings will be added as we discover Cloud.ru resource types
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Cloud.ru API"""
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
            self.logger.error(f"Cloud.ru connection test failed: {e}")
            return {
                'success': False,
                'message': f'Connection test failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }

    def sync_resources(self) -> SyncResult:
        """
        Sync all resources from Cloud.ru using billing-first approach
        
        Returns:
            SyncResult with sync status and resource data
        """
        result = SyncResult(success=False, message="Sync not started", provider_type=self.get_provider_type())
        
        try:
            self.logger.info(f"Starting Cloud.ru billing-first resource sync for provider {self.provider_id}")
            
            # Get provider instance from database
            from app.core.models.provider import CloudProvider
            provider = CloudProvider.query.get(self.provider_id)
            if not provider:
                result.message = f"Provider {self.provider_id} not found"
                result.errors = ["Provider not found in database"]
                return result
            
            # PHASE 1: Billing Data Collection
            self.logger.info("Phase 1: Collecting billing data")
            account_billing = self._collect_account_billing()
            
            # PHASE 2: Resource Discovery
            self.logger.info("Phase 2: Discovering resources")
            resources = self._discover_resources()
            
            # PHASE 3: Resource Processing and Unification
            self.logger.info("Phase 3: Processing and unifying resources")
            unified_resources = self._process_resources(resources, account_billing)
            
            # PHASE 4: Cost Validation
            self.logger.info("Phase 4: Validating costs")
            total_calculated_cost = sum(r.effective_cost for r in unified_resources)
            billing_validation = self._validate_costs(total_calculated_cost, account_billing)
            
            # The sync orchestrator will handle saving resources to database
            result.success = True
            result.message = f"Successfully synced {len(unified_resources)} resources from Cloud.ru"
            result.resources_synced = len(unified_resources)
            result.total_cost = total_calculated_cost
            result.data = {
                'resources': [r.to_dict() for r in unified_resources],
                'account_billing': account_billing,
                'billing_validation': billing_validation,
                'sync_timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"Cloud.ru sync completed: {len(unified_resources)} resources, {total_calculated_cost:.2f} RUB/day")
            
        except Exception as e:
            error_msg = f"Cloud.ru sync failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            result.message = error_msg
            result.errors = [str(e)]
        
        return result
    
    def _collect_account_billing(self) -> Dict[str, Any]:
        """Phase 1: Collect account-level billing data"""
        try:
            account_billing = self.client.get_account_billing()
            if not account_billing:
                self.logger.warning("Failed to get account billing data")
                return {
                    'balance': 0,
                    'currency': 'RUB',
                    'status': 'unknown',
                    'note': 'Billing endpoint to be determined',
                    'daily_rate': 0,
                    'monthly_rate': 0
                }
            
            return account_billing
        except Exception as e:
            self.logger.error(f"Failed to collect account billing: {e}")
            return {
                'balance': 0,
                'currency': 'RUB',
                'status': 'unknown',
                'daily_rate': 0,
                'monthly_rate': 0
            }
    
    def _discover_resources(self) -> Dict[str, List[Dict[str, Any]]]:
        """Phase 2: Discover all resources"""
        resources = {
            'vms': [],
            'volumes': [],
            'networks': []
        }
        
        try:
            # Get VMs
            vms = self.client.get_vms()
            resources['vms'] = vms
            self.logger.info(f"Discovered {len(vms)} VMs")
            
            # Get volumes
            volumes = self.client.get_volumes()
            resources['volumes'] = volumes
            self.logger.info(f"Discovered {len(volumes)} volumes")
            
            # Get networks
            networks = self.client.get_networks()
            resources['networks'] = networks
            self.logger.info(f"Discovered {len(networks)} networks")
            
        except Exception as e:
            self.logger.error(f"Error discovering resources: {e}")
        
        return resources
    
    def _map_consumption_to_resource_type(self, consumption: Dict[str, Any]) -> str:
        """
        Map Cloud.ru consumption record to unified resource type
        Uses servname (service name) and sku to determine resource type
        """
        servname = consumption.get('servname', '').lower()
        sku = consumption.get('sku', '').lower()
        resource_name = consumption.get('resource_name', '').lower()
        
        # Check SKU first (more reliable)
        # SKU patterns: PS-COREFT10N24000F-HD1MS0 (VM), PS-COREFT10NSSDFTF-HD1MS0 (Disk), PS-GTW0PRVTNNNNNNN-HD1MS0 (IP)
        if 'coreft' in sku and 'ssd' in sku:
            return 'volume'  # Disk/Volume
        elif 'coreft' in sku:
            return 'server'  # VM
        elif 'gtw0prvt' in sku or 'gateway' in sku:
            return 'network'  # IP/Network
        
        # Check servname (service name)
        # Virtual Machines (check first before disk, as "disk" might be in VM name)
        if any(x in servname for x in ['виртуальная машина', 'virtual machine', 'vm']):
            # But exclude if it's clearly a disk
            if not any(x in servname for x in ['диск', 'disk']):
                return 'server'
        
        # Bare Metal
        if any(x in servname for x in ['bare metal', 'bare-metal', 'физический сервер']):
            return 'server'  # Treat as server type
        
        # Storage/Volumes (check after VM to avoid false positives)
        if any(x in servname for x in ['диск', 'disk', 'ssd', 'nvme']):
            return 'volume'
        
        # Networks/IPs
        if any(x in servname for x in ['direct ip', 'floating ip', 'ip адрес', 'ip address']):
            return 'network'
        if 'ip' in servname and 'direct' in servname:
            return 'network'
        
        # Check resource_name for patterns
        if 'disk' in resource_name or 'volume' in resource_name:
            return 'volume'
        if 'ip' in resource_name or 'network' in resource_name:
            return 'network'
        
        # Databases
        if any(x in servname for x in ['postgresql', 'postgres', 'mysql', 'redis', 'mongodb', 'kafka']):
            return 'database'
        
        # Kubernetes
        if any(x in servname for x in ['kubernetes', 'k8s', 'managed kubernetes']):
            return 'kubernetes'
        
        # Load Balancer
        if any(x in servname for x in ['load balancer', 'balancer', 'lb']):
            return 'load_balancer'
        
        # Object Storage
        if any(x in servname for x in ['object storage', 's3']):
            return 's3'
        
        # Default to unknown - will be handled as generic resource
        return 'unknown'
    
    def _process_resources(self, resources: Dict[str, List[Dict[str, Any]]], 
                          account_billing: Dict[str, Any]) -> List:
        """Phase 3: Process resources into unified format - BILLING-FIRST approach"""
        from app.providers.resource_registry import ProviderResource
        
        # BILLING-FIRST: Get all consumption records and create resources from them
        billing_data = {}
        billing_resources_by_type = {}  # Group by resource type for processing
        try:
            billing_response = self.client.get_billing_data(days=7)  # Get last 7 days for current costs
            if billing_response and isinstance(billing_response, dict):
                # Cloud.ru API returns: { "consumptions": [...] }
                consumptions = billing_response.get('consumptions', [])
                self.logger.info(f"Processing {len(consumptions)} consumption records from billing API")
                
                # Group consumption by resource_id and calculate daily costs
                for consumption in consumptions:
                    # Extract resource identifier
                    resource_id = consumption.get('resource_id') or consumption.get('id') or consumption.get('resource_name')
                    if not resource_id:
                        continue
                    
                    # Map to resource type based on service name/SKU
                    resource_type = self._map_consumption_to_resource_type(consumption)
                    
                    # Extract cost information
                    cost = consumption.get('cost') or consumption.get('amount') or consumption.get('price', 0)
                    daily_cost = float(cost) if cost else 0.0
                    
                    # Aggregate costs per resource
                    if resource_id not in billing_data:
                        billing_data[resource_id] = {
                            'daily_cost': 0.0,
                            'monthly_cost': 0.0,
                            'currency': consumption.get('currency', 'RUB'),
                            'consumptions': [],
                            'resource_type': resource_type,
                            'servname': consumption.get('servname', ''),
                            'sku': consumption.get('sku', ''),
                            'resource_name': consumption.get('resource_name', ''),
                            'platform': consumption.get('platform', '')
                        }
                    
                    billing_data[resource_id]['daily_cost'] += daily_cost
                    billing_data[resource_id]['consumptions'].append(consumption)
                    
                    # Group by resource type for processing
                    if resource_type not in billing_resources_by_type:
                        billing_resources_by_type[resource_type] = {}
                    billing_resources_by_type[resource_type][resource_id] = billing_data[resource_id]
                
                # Calculate monthly costs (daily * 30)
                for resource_id, cost_data in billing_data.items():
                    cost_data['monthly_cost'] = cost_data['daily_cost'] * 30.0
                
                self.logger.info(f"Mapped billing costs for {len(billing_data)} resources")
                self.logger.info(f"Resources by type: {[(k, len(v)) for k, v in billing_resources_by_type.items()]}")
        except Exception as e:
            self.logger.warning(f"Failed to get per-resource billing data: {e}", exc_info=True)
        
        unified_resources = []
        
        # Create a map of API-discovered resources by ID for enrichment
        api_resources_by_id = {}
        for vm in resources.get('vms', []):
            vm_id = vm.get('id') or vm.get('uuid')
            if vm_id:
                api_resources_by_id[vm_id] = {'type': 'server', 'data': vm}
        for volume in resources.get('volumes', []):
            vol_id = volume.get('id') or volume.get('uuid')
            if vol_id:
                api_resources_by_id[vol_id] = {'type': 'volume', 'data': volume}
        for network in resources.get('networks', []):
            net_id = network.get('id') or network.get('uuid')
            if net_id:
                api_resources_by_id[net_id] = {'type': 'network', 'data': network}
        
        # UNIFICATION: First process all VMs and store them for volume/IP matching
        unified_vms = {}  # Map of VM resource_id -> ProviderResource
        
        # Process servers (VMs and Bare Metal) first
        if 'server' in billing_resources_by_type:
            for resource_id, billing_info in billing_resources_by_type['server'].items():
                try:
                    # Try to enrich with API data if available
                    if resource_id in api_resources_by_id and api_resources_by_id[resource_id]['type'] == 'server':
                        vm_data = api_resources_by_id[resource_id]['data'].copy()
                        vm_data['billing'] = billing_info
                        unified_vm = self._create_unified_vm(vm_data, account_billing)
                    else:
                        # Create from billing data only (Bare Metal or VM not in API)
                        unified_vm = self._create_unified_resource_from_billing(
                            resource_id, billing_info, 'server', account_billing
                        )
                    if unified_vm:
                        unified_vms[resource_id] = unified_vm
                        unified_resources.append(unified_vm)
                except Exception as e:
                    self.logger.warning(f"Failed to process server {resource_id}: {e}")
        
        # Process volumes - try to unify with VMs
        if 'volume' in billing_resources_by_type:
            for resource_id, billing_info in billing_resources_by_type['volume'].items():
                try:
                    # Try to match volume to VM by name pattern (e.g., "mach1free-disk_..." -> "mach1free")
                    volume_name = billing_info.get('resource_name', '')
                    matched_vm_id = None
                    
                    # Match by name pattern: "{vm_name}-disk_..." or "{vm_name}_disk_..."
                    for vm_id, vm_resource in unified_vms.items():
                        vm_name = vm_resource.resource_name
                        # Check if volume name starts with VM name followed by "-disk" or "_disk"
                        if vm_name and (volume_name.startswith(f"{vm_name}-disk") or 
                                       volume_name.startswith(f"{vm_name}_disk") or
                                       f"-{vm_name}-" in volume_name):
                            matched_vm_id = vm_id
                            self.logger.info(f"Matched volume {volume_name} to VM {vm_name} by name pattern")
                            break
                    
                    if matched_vm_id:
                        # Unify volume into VM - add to VM's provider_config
                        self._add_volume_to_vm(unified_vms[matched_vm_id], resource_id, billing_info)
                        self.logger.info(f"Unified volume {volume_name} into VM {unified_vms[matched_vm_id].resource_name}")
                    else:
                        # Standalone volume - create separate resource
                        if resource_id in api_resources_by_id and api_resources_by_id[resource_id]['type'] == 'volume':
                            volume_data = api_resources_by_id[resource_id]['data'].copy()
                            volume_data['billing'] = billing_info
                            unified_volume = self._create_unified_volume(volume_data, account_billing)
                        else:
                            unified_volume = self._create_unified_resource_from_billing(
                                resource_id, billing_info, 'volume', account_billing
                            )
                        if unified_volume:
                            unified_resources.append(unified_volume)
                except Exception as e:
                    self.logger.warning(f"Failed to process volume {resource_id}: {e}")
        
        # Process networks/IPs - try to unify with VMs
        if 'network' in billing_resources_by_type:
            for resource_id, billing_info in billing_resources_by_type['network'].items():
                try:
                    # Try to match IP to VM by checking VM's external_ip or interfaces
                    matched_vm_id = None
                    ip_name = billing_info.get('resource_name', '')
                    
                    # Extract IP address from resource_name (e.g., "direct-ip-addr_45.151.31.50_...")
                    ip_address = None
                    if 'direct-ip-addr_' in ip_name:
                        parts = ip_name.split('_')
                        if len(parts) >= 2:
                            ip_address = parts[1]  # Extract IP from name
                    
                    # Try to match by checking VM's external IP
                    for vm_id, vm_resource in unified_vms.items():
                        # Check if VM has this IP in external_ip
                        if vm_resource.external_ip == ip_address:
                            matched_vm_id = vm_id
                            self.logger.info(f"Matched IP {ip_address} to VM {vm_resource.resource_name} by external_ip")
                            break
                        
                        # Check VM's provider_config for interfaces
                        vm_config = vm_resource.provider_config
                        if isinstance(vm_config, dict):
                            interfaces = vm_config.get('interfaces', [])
                            for interface in interfaces:
                                if isinstance(interface, dict):
                                    if interface.get('ip_address') == ip_address:
                                        matched_vm_id = vm_id
                                        self.logger.info(f"Matched IP {ip_address} to VM {vm_resource.resource_name} by interface")
                                        break
                                    floating_ip = interface.get('floating_ip', {})
                                    if isinstance(floating_ip, dict) and floating_ip.get('ip_address') == ip_address:
                                        matched_vm_id = vm_id
                                        self.logger.info(f"Matched IP {ip_address} to VM {vm_resource.resource_name} by floating_ip")
                                        break
                                if matched_vm_id:
                                    break
                        if matched_vm_id:
                            break
                    
                    if matched_vm_id:
                        # Unify IP into VM - add to VM's provider_config
                        self._add_ip_to_vm(unified_vms[matched_vm_id], resource_id, billing_info, ip_address)
                        self.logger.info(f"Unified IP {ip_address} into VM {unified_vms[matched_vm_id].resource_name}")
                    else:
                        # Standalone IP - create separate resource
                        if resource_id in api_resources_by_id and api_resources_by_id[resource_id]['type'] == 'network':
                            network_data = api_resources_by_id[resource_id]['data'].copy()
                            network_data['billing'] = billing_info
                            unified_network = self._create_unified_network(network_data, account_billing)
                        else:
                            unified_network = self._create_unified_resource_from_billing(
                                resource_id, billing_info, 'network', account_billing
                            )
                        if unified_network:
                            unified_resources.append(unified_network)
                except Exception as e:
                    self.logger.warning(f"Failed to process network {resource_id}: {e}")
        
        # Process other resource types (databases, kubernetes, load_balancer, etc.)
        other_types = [t for t in billing_resources_by_type.keys() 
                      if t not in ['server', 'volume', 'network', 'unknown']]
        for resource_type in other_types:
            for resource_id, billing_info in billing_resources_by_type[resource_type].items():
                try:
                    unified_resource = self._create_unified_resource_from_billing(
                        resource_id, billing_info, resource_type, account_billing
                    )
                    if unified_resource:
                        unified_resources.append(unified_resource)
                except Exception as e:
                    self.logger.warning(f"Failed to process {resource_type} {resource_id}: {e}")
        
        # Process unknown types as generic resources
        if 'unknown' in billing_resources_by_type:
            for resource_id, billing_info in billing_resources_by_type['unknown'].items():
                try:
                    unified_resource = self._create_unified_resource_from_billing(
                        resource_id, billing_info, 'unknown', account_billing
                    )
                    if unified_resource:
                        unified_resources.append(unified_resource)
                except Exception as e:
                    self.logger.warning(f"Failed to process unknown resource {resource_id}: {e}")
        
        return unified_resources
    
    def _create_unified_vm(self, vm_data: Dict[str, Any], account_billing: Dict[str, Any]) -> Optional:
        """Create unified VM resource from Cloud.ru VM data"""
        from app.providers.resource_registry import ProviderResource
        
        resource_id = vm_data.get('id')
        if not resource_id:
            return None
        
        resource_name = vm_data.get('name') or f"VM-{resource_id[:8]}"
        
        # Map Cloud.ru state to unified status
        cloud_ru_state = vm_data.get('state', '').lower()
        status_mapping = {
            'active': 'active',
            'running': 'active',
            'stopped': 'stopped',
            'paused': 'paused',
            'suspended': 'suspended',
            'error': 'error',
            'deleted': 'deleted'
        }
        status = status_mapping.get(cloud_ru_state, cloud_ru_state or 'unknown')
        
        # Get region/availability zone
        # Cloud.ru returns region as a dict with id, name, enabled
        region_data = vm_data.get('availability_zone') or vm_data.get('region')
        if isinstance(region_data, dict):
            region = region_data.get('name') or region_data.get('id') or 'unknown'
        elif isinstance(region_data, str):
            region = region_data
        else:
            region = 'unknown'
        
        # Extract external IP from interfaces
        # Cloud.ru interfaces structure: [{ 'ip_address': '...', 'floating_ip': {...} }]
        external_ip = None
        interfaces = vm_data.get('interfaces', [])
        if interfaces:
            for interface in interfaces:
                if isinstance(interface, dict):
                    # Cloud.ru has ip_address directly in interface
                    ip_address = interface.get('ip_address')
                    if ip_address:
                        external_ip = ip_address
                        break
                    # Also check floating_ip
                    floating_ip = interface.get('floating_ip', {})
                    if isinstance(floating_ip, dict):
                        floating_ip_addr = floating_ip.get('ip_address')
                        if floating_ip_addr:
                            external_ip = floating_ip_addr
                            break
                    # Legacy: Look for fixed_ips (OpenStack-style)
                    fixed_ips = interface.get('fixed_ips', [])
                    if fixed_ips:
                        for ip_info in fixed_ips:
                            if isinstance(ip_info, dict):
                                ip_addr = ip_info.get('ip_address')
                                if ip_addr:
                                    external_ip = ip_addr
                                    break
                    if external_ip:
                        break
        
        # Extract flavor information for hardware specs and cost estimation
        flavor = vm_data.get('flavor', {})
        if isinstance(flavor, str):
            # If flavor is just a string (ID), try to get details from VM data
            flavor = {}
        
        flavor_name = flavor.get('name', '') if isinstance(flavor, dict) else str(flavor)
        flavor_id = flavor.get('id', '') if isinstance(flavor, dict) else str(flavor)
        
        # Extract hardware specs from flavor
        # Cloud.ru flavor structure: { 'cpu': 2, 'ram': 4, ... }
        # Based on actual API response: ram is in GB, cpu is count
        cpu_cores = flavor.get('cpu') or flavor.get('vcpus') or vm_data.get('cpu') or vm_data.get('vcpus') or vm_data.get('cpu_count', 0)
        
        # RAM: Cloud.ru returns ram in GB (e.g., ram: 4 means 4 GB)
        # Convert to MB for storage in provider_config
        ram_gb = flavor.get('ram') or vm_data.get('ram', 0)
        if isinstance(ram_gb, (int, float)) and ram_gb > 0:
            # Cloud.ru flavor.ram is in GB, convert to MB
            ram_mb = int(ram_gb * 1024)
        else:
            # Try to get from memory field (might be in MB)
            ram_mb = flavor.get('memory') or vm_data.get('memory') or vm_data.get('memory_mb', 0)
            if ram_mb and ram_mb < 100:  # If less than 100, likely in GB
                ram_mb = int(ram_mb * 1024)
        
        # Disk: Cloud.ru flavor doesn't include disk size
        # Disk size is typically determined by the image or attached volumes
        # For now, we'll leave it as 0 - it can be populated from volumes if available
        disk_gb = flavor.get('disk') or vm_data.get('disk') or vm_data.get('disk_gb', 0)
        
        # If disk is in MB, convert to GB
        if disk_gb and disk_gb < 100:  # Likely in GB already, but if very small might be MB
            disk_mb = flavor.get('disk_mb') or vm_data.get('disk_mb')
            if disk_mb:
                disk_gb = disk_mb / 1024
        
        # Extract cost from VM data or billing
        # Cloud.ru may provide cost in the VM data or we need to calculate from billing
        daily_cost = 0.0
        monthly_cost = 0.0
        
        # Try to get cost from VM metadata first
        if vm_data.get('cost_per_day'):
            daily_cost = float(vm_data.get('cost_per_day', 0))
        elif vm_data.get('cost_per_month'):
            monthly_cost = float(vm_data.get('cost_per_month', 0))
            daily_cost = monthly_cost / 30.0
        elif vm_data.get('billing', {}).get('daily_cost'):
            daily_cost = float(vm_data.get('billing', {}).get('daily_cost', 0))
        elif vm_data.get('billing', {}).get('monthly_cost'):
            monthly_cost = float(vm_data.get('billing', {}).get('monthly_cost', 0))
            daily_cost = monthly_cost / 30.0
        elif vm_data.get('billing', {}).get('cost'):
            # Generic cost field - assume daily if no period specified
            cost_value = float(vm_data.get('billing', {}).get('cost', 0))
            if cost_value > 100:  # Likely monthly if > 100 RUB
                monthly_cost = cost_value
                daily_cost = monthly_cost / 30.0
            else:
                daily_cost = cost_value
        
        # Try to extract from pricing/flavor if available
        if daily_cost == 0.0 and flavor:
            if isinstance(flavor, dict):
                # Check flavor for pricing info
                flavor_price = flavor.get('price') or flavor.get('cost')
                if flavor_price:
                    price_value = float(flavor_price)
                    # Check if it's hourly, daily, or monthly based on context
                    price_unit = flavor.get('price_unit', '').lower()
                    if 'hour' in price_unit:
                        daily_cost = price_value * 24
                    elif 'day' in price_unit:
                        daily_cost = price_value
                    elif 'month' in price_unit:
                        monthly_cost = price_value
                        daily_cost = monthly_cost / 30.0
                    else:
                        # Default: assume monthly if > 100, else daily
                        if price_value > 100:
                            monthly_cost = price_value
                            daily_cost = monthly_cost / 30.0
                        else:
                            daily_cost = price_value
        
        # Log if cost is still 0 for debugging
        if daily_cost == 0.0:
            self.logger.debug(f"VM {resource_name} has no cost data - billing API integration needed")
        
        # Extract tags
        tags = {}
        if vm_data.get('tags'):
            if isinstance(vm_data['tags'], dict):
                tags = vm_data['tags']
            elif isinstance(vm_data['tags'], list):
                # Convert list of tag objects to dict
                for tag in vm_data['tags']:
                    if isinstance(tag, dict):
                        tag_key = tag.get('key') or tag.get('name')
                        tag_value = tag.get('value')
                        if tag_key:
                            tags[tag_key] = tag_value
        
        # Add Cloud.ru specific metadata to tags
        tags['cloud_ru_flavor'] = flavor_name
        tags['cloud_ru_flavor_id'] = flavor_id
        tags['cloud_ru_project_id'] = vm_data.get('project_id', '')
        
        # Enhance provider_config with hardware specs for frontend display
        enhanced_config = vm_data.copy()
        if cpu_cores:
            enhanced_config['cpu_cores'] = int(cpu_cores)
            enhanced_config['vcpus'] = int(cpu_cores)
        if ram_mb:
            enhanced_config['ram_mb'] = int(ram_mb)
            enhanced_config['memory_mb'] = int(ram_mb)
        if disk_gb:
            enhanced_config['disk_gb'] = float(disk_gb)
            enhanced_config['total_storage_gb'] = float(disk_gb)
        
        # Add cost info to config if available
        if daily_cost > 0:
            enhanced_config['daily_cost'] = daily_cost
        if monthly_cost > 0:
            enhanced_config['monthly_cost'] = monthly_cost
        
        return ProviderResource(
            resource_id=resource_id,
            resource_name=resource_name,
            resource_type='server',
            service_name='Compute',
            region=region,
            status=status,
            effective_cost=daily_cost,
            currency=account_billing.get('currency', 'RUB'),
            billing_period='daily',
            provider_config=enhanced_config,
            provider_type='cloud-ru',
            external_ip=external_ip,
            tags=tags
        )
    
    def _create_unified_volume(self, volume_data: Dict[str, Any], account_billing: Dict[str, Any]) -> Optional:
        """Create unified volume resource"""
        from app.providers.resource_registry import ProviderResource
        
        resource_id = volume_data.get('id') or volume_data.get('volume_id') or str(volume_data.get('uuid', ''))
        if not resource_id:
            return None
        
        resource_name = volume_data.get('name') or f"Volume-{resource_id[:8]}"
        status = volume_data.get('status', 'unknown')
        region = volume_data.get('region') or volume_data.get('zone') or 'unknown'
        
        # Extract cost
        daily_cost = volume_data.get('daily_cost', volume_data.get('cost_per_day', 0))
        if not daily_cost:
            hourly_cost = volume_data.get('hourly_cost', volume_data.get('cost_per_hour', 0))
            monthly_cost = volume_data.get('monthly_cost', volume_data.get('cost_per_month', 0))
            if hourly_cost:
                daily_cost = hourly_cost * 24
            elif monthly_cost:
                daily_cost = monthly_cost / 30
        
        return ProviderResource(
            resource_id=resource_id,
            resource_name=resource_name,
            resource_type='volume',
            service_name='Block Storage',
            region=region,
            status=status,
            effective_cost=daily_cost,
            currency=account_billing.get('currency', 'RUB'),
            billing_period='daily',
            provider_config=volume_data,
            provider_type='cloud-ru',
            tags=volume_data.get('tags', {})
        )
    
    def _create_unified_network(self, network_data: Dict[str, Any], account_billing: Dict[str, Any]) -> Optional:
        """Create unified network resource (only if it has costs)"""
        from app.providers.resource_registry import ProviderResource
        
        resource_id = network_data.get('id') or network_data.get('network_id') or str(network_data.get('uuid', ''))
        if not resource_id:
            return None
        
        # Only include networks with costs
        daily_cost = network_data.get('daily_cost', network_data.get('cost_per_day', 0))
        if not daily_cost:
            return None  # Skip free networks
        
        resource_name = network_data.get('name') or f"Network-{resource_id[:8]}"
        status = network_data.get('status', 'unknown')
        region = network_data.get('region') or 'unknown'
        
        return ProviderResource(
            resource_id=resource_id,
            resource_name=resource_name,
            resource_type='network',
            service_name='Network',
            region=region,
            status=status,
            effective_cost=daily_cost,
            currency=account_billing.get('currency', 'RUB'),
            billing_period='daily',
            provider_config=network_data,
            provider_type='cloud-ru',
            tags=network_data.get('tags', {})
        )
    
    def _add_volume_to_vm(self, vm_resource, volume_id: str, billing_info: Dict[str, Any]):
        """Add volume information to VM's provider_config (unification)"""
        import json
        try:
            # Get current provider_config (should be a dict, but handle string case for safety)
            provider_config = vm_resource.provider_config
            if isinstance(provider_config, str):
                provider_config = json.loads(provider_config)
            elif not isinstance(provider_config, dict):
                provider_config = {}
            else:
                # Make a copy to avoid mutating the original
                provider_config = provider_config.copy()
            
            # Initialize attached_volumes list
            if 'attached_volumes' not in provider_config:
                provider_config['attached_volumes'] = []
            
            # Extract volume size from consumption if available
            volume_size_gb = 0
            if billing_info.get('consumptions'):
                # Try to get size from consumption metadata or usefact
                for consumption in billing_info['consumptions']:
                    # usefact might represent size in GB
                    usefact = consumption.get('usefact', 0)
                    if usefact and usefact > 1:  # Likely size in GB if > 1
                        volume_size_gb = max(volume_size_gb, usefact)
            
            volume_info = {
                'id': volume_id,
                'name': billing_info.get('resource_name', ''),
                'size_gb': volume_size_gb,
                'daily_cost': billing_info.get('daily_cost', 0.0),
                'monthly_cost': billing_info.get('monthly_cost', 0.0)
            }
            
            # Check if volume already added
            existing_volumes = [v for v in provider_config['attached_volumes'] if v.get('id') == volume_id]
            if not existing_volumes:
                provider_config['attached_volumes'].append(volume_info)
                
                # Recalculate total storage
                total_storage_gb = sum(v.get('size_gb', 0) for v in provider_config['attached_volumes'])
                provider_config['total_storage_gb'] = total_storage_gb
                
                # Update VM cost to include volume cost
                vm_resource.effective_cost = (vm_resource.effective_cost or 0.0) + billing_info.get('daily_cost', 0.0)
                
                # Update provider_config
                vm_resource.provider_config = provider_config
                
                self.logger.info(f"Added volume {volume_id} to VM {vm_resource.resource_name}")
        except Exception as e:
            self.logger.error(f"Error adding volume to VM: {e}", exc_info=True)
    
    def _add_ip_to_vm(self, vm_resource, ip_id: str, billing_info: Dict[str, Any], ip_address: str = None):
        """Add IP address information to VM's provider_config (unification)"""
        import json
        try:
            # Get current provider_config (should be a dict, but handle string case for safety)
            provider_config = vm_resource.provider_config
            if isinstance(provider_config, str):
                provider_config = json.loads(provider_config)
            elif not isinstance(provider_config, dict):
                provider_config = {}
            else:
                # Make a copy to avoid mutating the original
                provider_config = provider_config.copy()
            
            # Initialize attached_ips list
            if 'attached_ips' not in provider_config:
                provider_config['attached_ips'] = []
            
            # Extract IP from resource_name if not provided
            if not ip_address:
                ip_name = billing_info.get('resource_name', '')
                if 'direct-ip-addr_' in ip_name:
                    parts = ip_name.split('_')
                    if len(parts) >= 2:
                        ip_address = parts[1]
            
            ip_info = {
                'id': ip_id,
                'ip_address': ip_address,
                'name': billing_info.get('resource_name', ''),
                'type': 'direct_ip',
                'daily_cost': billing_info.get('daily_cost', 0.0),
                'monthly_cost': billing_info.get('monthly_cost', 0.0)
            }
            
            # Check if IP already added
            existing_ips = [ip for ip in provider_config['attached_ips'] if ip.get('id') == ip_id]
            if not existing_ips:
                provider_config['attached_ips'].append(ip_info)
                
                # Update VM external_ip if not set
                if ip_address and not vm_resource.external_ip:
                    vm_resource.external_ip = ip_address
                
                # Update VM cost to include IP cost
                vm_resource.effective_cost = (vm_resource.effective_cost or 0.0) + billing_info.get('daily_cost', 0.0)
                
                # Update provider_config
                vm_resource.provider_config = provider_config
                
                self.logger.info(f"Added IP {ip_address} to VM {vm_resource.resource_name}")
        except Exception as e:
            self.logger.error(f"Error adding IP to VM: {e}", exc_info=True)
    
    def _create_unified_resource_from_billing(self, resource_id: str, billing_info: Dict[str, Any],
                                            resource_type: str, account_billing: Dict[str, Any]) -> Optional:
        """
        Create a unified resource from billing data only (billing-first approach)
        Used when resource is not found via API but appears in billing
        """
        from app.providers.resource_registry import ProviderResource
        
        resource_name = billing_info.get('resource_name') or billing_info.get('servname', '') or f"Resource-{resource_id[:8]}"
        daily_cost = billing_info.get('daily_cost', 0.0)
        monthly_cost = billing_info.get('monthly_cost', daily_cost * 30.0)
        
        # Extract region from consumption if available
        region = 'unknown'
        if billing_info.get('consumptions'):
            # Try to get region from first consumption record
            first_consumption = billing_info['consumptions'][0]
            region = first_consumption.get('region') or first_consumption.get('availability_zone') or 'unknown'
        
        # Map resource type to service name
        service_name_map = {
            'server': 'Compute',
            'volume': 'Block Storage',
            'network': 'Network',
            'database': 'Database',
            'kubernetes': 'Kubernetes',
            'load_balancer': 'Load Balancer',
            's3': 'Object Storage',
            'unknown': 'Other'
        }
        service_name = service_name_map.get(resource_type, 'Other')
        
        # Store full billing info in provider_config
        provider_config = {
            'resource_id': resource_id,
            'resource_name': resource_name,
            'servname': billing_info.get('servname', ''),
            'sku': billing_info.get('sku', ''),
            'platform': billing_info.get('platform', ''),
            'billing_source': 'consumption_api',
            'consumptions': billing_info.get('consumptions', [])
        }
        
        return ProviderResource(
            resource_id=resource_id,
            resource_name=resource_name,
            resource_type=resource_type if resource_type != 'unknown' else 'other',
            service_name=service_name,
            region=region,
            status='active',  # Assume active if being billed
            effective_cost=daily_cost,
            currency=billing_info.get('currency', 'RUB'),
            billing_period='daily',
            provider_config=provider_config,
            provider_type='cloud-ru',
            tags={}
        )
    
    def _validate_costs(self, total_calculated_cost: float, account_billing: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 4: Validate calculated costs against account billing"""
        validation = {
            'valid': False,
            'total_calculated': total_calculated_cost,
            'account_balance': account_billing.get('balance', 0),
            'note': 'Cost validation pending billing API implementation'
        }
        
        # If we have billing data, try to validate
        if account_billing.get('daily_rate'):
            account_daily = account_billing.get('daily_rate', 0)
            diff = abs(total_calculated_cost - account_daily)
            validation['account_daily_rate'] = account_daily
            validation['difference'] = diff
            validation['valid'] = diff < (account_daily * 0.1)  # Within 10% is acceptable
        
        return validation

    def get_pricing_data(self) -> List[Dict[str, Any]]:
        """
        Get pricing data from Cloud.ru
        
        This will be implemented in Phase 3 (Step 3.3)
        
        Returns:
            List of pricing records
        """
        # TODO: Implement in Phase 3, Step 3.3
        self.logger.warning("Cloud.ru pricing data retrieval not yet implemented")
        return []

