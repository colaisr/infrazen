"""
Cloud.ru provider plugin
Implements Cloud.ru provider integration using the plugin architecture
"""
import hashlib
import logging
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from ..plugin_system import ProviderPlugin, SyncResult
from ..cloud_ru.client import CloudRuClient, CloudRuAdvancedClient

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
            
            # Persist auto-discovered agreement_id to provider credentials (no manual input needed)
            if self.client.agreement_id and not provider.get_credentials().get('agreement_id'):
                try:
                    from app.core.models import db
                    creds = provider.get_credentials()
                    creds['agreement_id'] = self.client.agreement_id
                    provider.set_credentials(creds)
                    db.session.add(provider)
                    db.session.commit()
                    self.logger.info(f"Saved auto-discovered agreement_id to provider credentials")
                except Exception as e:
                    self.logger.warning(f"Could not persist agreement_id: {e}")
            
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
        Uses servname (service name), sku/sku_name to determine resource type
        """
        servname = consumption.get('servname', '').lower()
        sku = (consumption.get('sku') or consumption.get('sku_name') or '').lower()
        resource_name = consumption.get('resource_name', '').lower()
        
        # Check SKU first (more reliable)
        # SKU patterns: PS-COREFT10N24000F-HD1MS0 (VM), PS-COREFT10NSSDFTF-HD1MS0 (Disk), PS-GTW0PRVTNNNNNNN-HD1MS0 (IP)
        # BFF format: HA-ECS0CH0LS02X206-HX2MS0 (VM), HA-ECS0CH0LS0L2006-HX2MS0 (VM)
        if 'coreft' in sku and 'ssd' in sku:
            return 'volume'  # Disk/Volume
        elif 'coreft' in sku:
            return 'server'  # VM
        elif 'ecs' in sku and 'ha-' in sku:
            return 'server'  # BFF ECS VM (HA-ECS...)
        elif 'ecs' in sku:
            return 'server'  # ECS compute
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
        # File Storage / NFS (SFS Turbo) - treat as storage (volume bucket)
        if any(x in servname for x in ['nfs', 'sfs', 'файлов', 'file system', 'file storage']):
            return 'volume'
        
        # Backup / snapshots (CBR)
        if any(x in servname for x in ['резервное копирование', 'backup', 'cbr', 'vault.backup']):
            return 'backup'

        # KMS (Key Management Service)
        if any(x in servname for x in ['kms', 'управления ключами', 'key management', 'cmk']):
            return 'kms'

        # Logging / LTS (often appears as AOM LTS services)
        if any(x in servname for x in ['lts', 'логов', 'logging']) and 'aom' in servname:
            return 'logging'

        # Networks/IPs
        if any(x in servname for x in ['direct ip', 'floating ip', 'ip адрес', 'ip address']):
            return 'network'
        if 'ip' in servname and 'direct' in servname:
            return 'network'
        # Evolution EIP / Internet access / bandwidth (рус/eng)
        if any(x in servname for x in ['eip', 'доступ в интернет', 'полоса пропускания', 'bandwidth', 'bgp']):
            return 'network'
        
        # Check resource_name for patterns
        if 'disk' in resource_name or 'volume' in resource_name:
            return 'volume'
        if 'ip' in resource_name or 'network' in resource_name:
            return 'network'
        
        # Databases
        if any(x in servname for x in ['postgresql', 'postgres', 'mysql', 'redis', 'mongodb', 'kafka']):
            return 'database'
        if any(x in servname for x in ['субд', 'база данных', 'кластер баз', 'managed database']):
            return 'database'
        
        # Kubernetes
        if any(x in servname for x in ['kubernetes', 'k8s', 'managed kubernetes']):
            return 'kubernetes'
        if any(x in servname for x in ['кубер', 'kuber']):
            return 'kubernetes'
        # Cloud.ru Managed Kubernetes is billed as "Контейнеры (CCE)"
        if 'cce' in servname or 'контейнеры' in servname:
            return 'kubernetes'
        
        # Load Balancer
        if any(x in servname for x in ['load balancer', 'balancer', 'lb']):
            return 'load_balancer'
        
        # Object Storage
        if any(x in servname for x in ['object storage', 's3']):
            return 's3'
        
        # Event/audit logging, recording services (often S3/object-storage related)
        if any(x in servname for x in ['запис', 'событ', 'действ', 'event', 'audit', 'логирован']):
            return 's3'
        
        # Check resource_name for volume/disk patterns (ext4, data- prefix, empty)
        if any(x in resource_name for x in ['ext4', 'ext3', 'xfs', '-empty-', 'data-']):
            return 'volume'
        if 'disk' in resource_name or 'volume' in resource_name:
            return 'volume'
        
        # S3 / object storage API operations and related (reduce 'unknown' in components)
        if any(x in servname for x in ['object storage', 's3', 's3e', 'obs']):
            return 's3'
        if any(x in resource_name for x in ['operation', 'request', 'bucket', 'listall', 'getobject', 'putobject']):
            return 's3'
        if resource_name.endswith(('operation', 'request')) and 'storage' in servname:
            return 's3'
        
        # Default to unknown - will be handled as generic resource
        return 'unknown'
    
    def _parse_sku_specs(self, sku_name: str) -> Dict[str, Any]:
        """
        Parse Cloud.ru SKU name to extract VM specs (vCPU, RAM) for tile display.
        BFF format: HA-ECS0CH0LS02X206-HX2MS0 (2 vCPU, 6 GB), HA-ECS0CH0LS0L2006 (2 vCPU, 6 GB).
        Returns dict with vcpus, ram_mb, cpu_cores if parseable; empty dict otherwise.
        """
        if not sku_name or not isinstance(sku_name, str):
            return {}
        sku = sku_name.upper()
        result = {}
        # Extract digit sequences (e.g. 02, 206, 2006)
        numbers = re.findall(r'\d+', sku)
        if not numbers:
            return {}
        # Filter out leading zeros: 02 -> 2, 06 -> 6
        nums = [int(n) for n in numbers if int(n) > 0]
        if not nums:
            return {}
        # First try: find 3-digit number encoding vCPU*100+RAM (206=2vCPU 6GB, 408=4vCPU 8GB)
        for n in nums:
            if 100 <= n <= 999:
                vcpu = n // 100
                ram = n % 100
                if 1 <= vcpu <= 32 and 1 <= ram <= 128:
                    result['vcpus'] = vcpu
                    result['cpu_cores'] = vcpu
                    result['ram_mb'] = ram * 1024
                    result['memory_mb'] = ram * 1024
                    return result
        # Second try: 4-digit like 2006 -> 2 vCPU, 6 GB
        for n in nums:
            if 1000 <= n <= 9999:
                vcpu = n // 1000
                ram = n % 1000
                if ram >= 100:
                    ram = ram // 10  # 006 -> 6
                if 1 <= vcpu <= 32 and 1 <= ram <= 128:
                    result['vcpus'] = vcpu
                    result['cpu_cores'] = vcpu
                    result['ram_mb'] = ram * 1024
                    result['memory_mb'] = ram * 1024
                    return result
        # Third: pair of small numbers (e.g. 2, 8)
        if len(nums) >= 2:
            last = nums[-1]
            prev = nums[-2]
            if last <= 32 and prev <= 32:
                result['vcpus'] = prev
                result['cpu_cores'] = prev
                result['ram_mb'] = last * 1024
                result['memory_mb'] = last * 1024
            elif last <= 128 and prev <= 64:
                result['vcpus'] = min(prev, last)
                result['cpu_cores'] = min(prev, last)
                result['ram_mb'] = max(prev, last) * 1024
                result['memory_mb'] = max(prev, last) * 1024
        elif len(nums) == 1:
            n = nums[0]
            if 2 <= n <= 32:
                # Single number - could be vCPU or RAM; assume vCPU if small
                result['vcpus'] = n
                result['cpu_cores'] = n
            elif 100 <= n <= 999:
                # e.g. 206 -> 2 vCPU, 6 GB
                vcpu = n // 100
                ram = n % 100
                if 1 <= vcpu <= 32 and 1 <= ram <= 128:
                    result['vcpus'] = vcpu
                    result['cpu_cores'] = vcpu
                    result['ram_mb'] = ram * 1024
                    result['memory_mb'] = ram * 1024
            elif 1000 <= n <= 9999:
                # e.g. 2006 -> 2 vCPU, 6 GB
                vcpu = n // 1000
                ram = n % 1000
                if ram >= 100:
                    ram = ram // 10  # 006 -> 6
                if 1 <= vcpu <= 32 and 1 <= ram <= 128:
                    result['vcpus'] = vcpu
                    result['cpu_cores'] = vcpu
                    result['ram_mb'] = ram * 1024
                    result['memory_mb'] = ram * 1024
        return result

    def _parse_volume_size_from_consumption(self, billing_info: Dict[str, Any]) -> Optional[float]:
        """
        Extract volume size (GB) from billing/consumption data for tile display.
        Checks: consumptions[].quantity, consumptions[].consumption_amount, sku patterns.
        """
        consumptions = billing_info.get('consumptions', [])
        for c in consumptions:
            qty = c.get('quantity') or c.get('consumption_amount') or c.get('amount')
            if qty is not None:
                try:
                    v = float(qty)
                    if 1 <= v <= 100000:  # Reasonable GB range
                        return round(v, 1)
                except (TypeError, ValueError):
                    pass
        sku = (billing_info.get('sku') or billing_info.get('sku_name') or '').upper()
        if sku:
            # Try patterns like "20GB", "HD1MS0" (1 = 1GB?), numbers in sku
            m = re.search(r'(\d+)\s*GB', sku, re.I)
            if m:
                return float(m.group(1))
            nums = re.findall(r'\d+', sku)
            for n in nums:
                v = int(n)
                if 1 <= v <= 10000:
                    return float(v)
        return None

    def _is_s3_api_operation(self, resource_id: str, consumption: Dict[str, Any]) -> bool:
        """Check if consumption record is an S3 API operation (not a real resource)."""
        rid = str(resource_id).lower()
        rname = str(consumption.get('resource_name', '')).lower()
        servname = str(consumption.get('servname', '')).lower()
        # Must be object storage / S3 related
        if not any(x in servname for x in ['object storage', 's3', 's3e']):
            return False
        # API operation patterns (List*, Get*, Put*, Delete*, Head*, etc.)
        op_suffixes = ('operation', 'request', 'list', 'get', 'put', 'delete', 'head', 'copy', 'post')
        return rid.endswith(op_suffixes) or any(rid.startswith(p) for p in ('list', 'get', 'put', 'delete', 'head'))
    
    def _process_resources(self, resources: Dict[str, List[Dict[str, Any]]], 
                          account_billing: Dict[str, Any]) -> List:
        """Phase 3: Process resources into unified format - BILLING-FIRST approach"""
        from app.providers.resource_registry import ProviderResource
        
        # BILLING-FIRST: Get all consumption records and create resources from them
        billing_data = {}
        billing_resources_by_type = {}  # Group by resource type for processing
        try:
            # Use 1 calendar day (yesterday) for daily cost - matches console totals
            billing_response = self.client.get_billing_data(days=1)
            if billing_response and isinstance(billing_response, dict):
                # Cloud.ru API returns: { "consumptions": [...] }
                consumptions = billing_response.get('consumptions', [])
                self.logger.info(f"Processing {len(consumptions)} consumption records from billing API")
                
                # Group consumption by resource_id and calculate daily costs
                s3_aggregate_cost = 0.0  # Aggregate S3 API operations into one resource
                s3_consumptions = []
                # Aggregate AOM/LTS log indexing+storage (not a deployable resource; reduce noise)
                lts_aggregates: Dict[str, Dict[str, Any]] = {}
                for consumption in consumptions:
                    # Extract resource identifier (support both organization API and BFF formats)
                    # BFF/console: instance_id for VMs, organization API: resource_id
                    resource_id = (consumption.get('resource_id') or consumption.get('instance_id') or
                                  consumption.get('id') or consumption.get('resource_name'))
                    if not resource_id:
                        continue
                    resource_id = str(resource_id)

                    # LTS/AOM logs: resource_id like "<prefix>.lts.*", usually no resource_name
                    rid_lower = resource_id.lower()
                    servname_lower = str(consumption.get('servname', '')).lower()
                    resource_name_raw = consumption.get('resource_name')
                    if ('.lts.' in rid_lower and (not resource_name_raw) and ('lts' in servname_lower)):
                        prefix = resource_id.split('.lts.')[0]
                        agg_id = f"lts:{prefix}"
                        cost = consumption.get('amount_nds') or consumption.get('amount') or consumption.get('cost') or consumption.get('price', 0)
                        daily_cost = float(cost) if cost else 0.0
                        if agg_id not in lts_aggregates:
                            lts_aggregates[agg_id] = {
                                'daily_cost': 0.0,
                                'currency': consumption.get('currency', 'RUB'),
                                'consumptions': [],
                                'platform': consumption.get('platform', ''),
                            }
                        lts_aggregates[agg_id]['daily_cost'] += daily_cost
                        lts_aggregates[agg_id]['consumptions'].append(consumption)
                        continue

                    # S3/object storage API operations (ListAllMyBucketsOperation, GetObject, etc.)
                    # - aggregate into one "Object Storage" resource instead of one per operation
                    if self._is_s3_api_operation(resource_id, consumption):
                        cost = consumption.get('amount_nds') or consumption.get('amount') or consumption.get('cost') or consumption.get('price', 0)
                        s3_aggregate_cost += float(cost) if cost else 0.0
                        s3_consumptions.append(consumption)
                        continue
                    
                    # Map to resource type based on service name/SKU
                    resource_type = self._map_consumption_to_resource_type(consumption)

                    meta = consumption.get('meta') if isinstance(consumption.get('meta'), dict) else {}
                    iam_project_name = (
                        meta.get('iam_project_name') or meta.get('iamProjectName') or meta.get('iam_project') or ''
                    )
                    tenant_name = meta.get('tenant_name') or meta.get('tenantName') or meta.get('tenant') or ''
                    
                    # Extract cost: amount_nds = with VAT (НДС, matches console "включая НДС")
                    cost = consumption.get('amount_nds') or consumption.get('amount') or consumption.get('cost') or consumption.get('price', 0)
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
                            'sku': consumption.get('sku') or consumption.get('sku_name', ''),
                            'sku_name': consumption.get('sku_name', ''),
                            'resource_name': consumption.get('resource_name', ''),
                            'platform': consumption.get('platform', ''),
                            # Billing metadata used for UI grouping/filtering
                            'iam_project_name': iam_project_name,
                            'tenant_name': tenant_name,
                        }
                    
                    billing_data[resource_id]['daily_cost'] += daily_cost
                    billing_data[resource_id]['consumptions'].append(consumption)
                    # Keep first non-empty metadata (should be stable per resource)
                    if iam_project_name and not billing_data[resource_id].get('iam_project_name'):
                        billing_data[resource_id]['iam_project_name'] = iam_project_name
                    if tenant_name and not billing_data[resource_id].get('tenant_name'):
                        billing_data[resource_id]['tenant_name'] = tenant_name
                    # Prefer resource_name from consumption when we have it (org API provides it)
                    if consumption.get('resource_name') and not billing_data[resource_id].get('resource_name'):
                        billing_data[resource_id]['resource_name'] = consumption.get('resource_name', '')
                    
                    # Group by resource type for processing
                    if resource_type not in billing_resources_by_type:
                        billing_resources_by_type[resource_type] = {}
                    billing_resources_by_type[resource_type][resource_id] = billing_data[resource_id]
                
                # Add aggregated S3/object storage as single resource (if any)
                if s3_aggregate_cost > 0:
                    s3_resource_id = 'object-storage-aggregate'
                    s3_meta = s3_consumptions[0].get('meta') if (s3_consumptions and isinstance(s3_consumptions[0].get('meta'), dict)) else {}
                    billing_data[s3_resource_id] = {
                        'daily_cost': s3_aggregate_cost,
                        'monthly_cost': s3_aggregate_cost * 30.0,
                        'currency': 'RUB',
                        'consumptions': s3_consumptions,
                        'resource_type': 's3',
                        'servname': 'Object Storage',
                        'sku': '',
                        'resource_name': 'Object Storage',
                        'platform': s3_consumptions[0].get('platform', '') if s3_consumptions else '',
                        'iam_project_name': s3_meta.get('iam_project_name') or '',
                        'tenant_name': s3_meta.get('tenant_name') or '',
                    }
                    if 's3' not in billing_resources_by_type:
                        billing_resources_by_type['s3'] = {}
                    billing_resources_by_type['s3'][s3_resource_id] = billing_data[s3_resource_id]

                # Add aggregated LTS logs as one resource per prefix
                if lts_aggregates:
                    if 'logging' not in billing_resources_by_type:
                        billing_resources_by_type['logging'] = {}
                    for agg_id, agg in lts_aggregates.items():
                        prefix = agg_id.split(':', 1)[-1]
                        short = prefix[:8]
                        first_meta = None
                        try:
                            first = (agg.get('consumptions') or [None])[0]
                            if isinstance(first, dict) and isinstance(first.get('meta'), dict):
                                first_meta = first.get('meta')
                        except Exception:
                            first_meta = None
                        billing_data[agg_id] = {
                            'daily_cost': agg.get('daily_cost', 0.0),
                            'monthly_cost': (agg.get('daily_cost', 0.0) * 30.0),
                            'currency': agg.get('currency', 'RUB'),
                            'consumptions': agg.get('consumptions', []),
                            'resource_type': 'logging',
                            'servname': 'Logging (LTS)',
                            'sku': '',
                            'resource_name': f'logging-lts-{short}',
                            'platform': agg.get('platform', ''),
                            'iam_project_name': (first_meta or {}).get('iam_project_name') or '',
                            'tenant_name': (first_meta or {}).get('tenant_name') or '',
                        }
                        billing_resources_by_type['logging'][agg_id] = billing_data[agg_id]
                
                # Calculate monthly costs (daily * 30)
                for resource_id, cost_data in billing_data.items():
                    cost_data['monthly_cost'] = cost_data['daily_cost'] * 30.0
                
                self.logger.info(f"Mapped billing costs for {len(billing_data)} resources")
                self.logger.info(f"Resources by type: {[(k, len(v)) for k, v in billing_resources_by_type.items()]}")
        except Exception as e:
            self.logger.warning(f"Failed to get per-resource billing data: {e}", exc_info=True)
        
        # GROUP BY resource_name: use Advanced API ID map (disk→vm, vm→cluster) when tenants
        # are configured; fall back to name heuristics for Evolution-only accounts.
        advanced_id_map: Dict[str, Any] = {}
        if not os.environ.get('CLOUD_RU_SKIP_DISK_MAPPING'):
            try:
                advanced_id_map = self._build_advanced_id_map()
            except Exception as e:
                self.logger.warning(f"Advanced API ID map failed, using name heuristics: {e}")
        unified_resources = self._create_unified_resources_by_name(
            billing_data, billing_resources_by_type, resources, account_billing,
            advanced_id_map.get('disk_to_vm', {}),
            advanced_id_map,
        )
        return unified_resources

    def _build_advanced_id_map(self) -> Dict[str, Any]:
        """
        Build a unified ID-relationship map across all configured Advanced tenants.

        Returns the merged result of ``CloudRuAdvancedClient.build_id_map()`` for
        every tenant in ``credentials['advanced_tenants']``.  If no tenants are
        configured (Evolution-only account), returns an empty dict so the caller
        falls back gracefully to name heuristics.

        Also fetches SFS Turbo share details and CES utilization metrics.
        """
        tenants = self.credentials.get('advanced_tenants') or []
        if not tenants:
            self.logger.info("No advanced_tenants configured – skipping Advanced ID map")
            return {}

        merged: Dict[str, Any] = {
            'disk_to_vm': {},
            'vm_to_cluster': {},
            'vm_details': {},
            'cluster_details': {},
            'vm_name_to_id': {},
            'db_name_to_id': {},
            'sfs_shares': {},
            'ces_utilization': {},
        }

        for tenant in tenants:
            ak = tenant.get('ak', '').strip()
            sk = tenant.get('sk', '').strip()
            project_id = tenant.get('project_id', '').strip()
            name = tenant.get('name', project_id)
            if not (ak and sk and project_id):
                self.logger.warning(f"Advanced tenant '{name}' missing ak/sk/project_id – skipping")
                continue
            try:
                adv_client = CloudRuAdvancedClient(ak, sk)
                tenant_map = adv_client.build_id_map(project_id)
                for key in ('disk_to_vm', 'vm_to_cluster', 'vm_details',
                            'cluster_details', 'vm_name_to_id'):
                    merged[key].update(tenant_map.get(key, {}))
                self.logger.info(
                    f"Advanced ID map for tenant '{name}': "
                    f"{len(tenant_map.get('disk_to_vm', {}))} disk→vm, "
                    f"{len(tenant_map.get('vm_to_cluster', {}))} vm→cluster"
                )

                # SFS Turbo shares (for capacity/utilization enrichment)
                try:
                    shares = adv_client.get_sfs_turbo_shares(project_id)
                    for s in shares:
                        sid = s.get('id')
                        if sid:
                            merged['sfs_shares'][sid] = s
                    self.logger.info(f"SFS Turbo for tenant '{name}': {len(shares)} shares")
                except Exception as e:
                    self.logger.warning(f"SFS Turbo fetch failed for tenant '{name}': {e}")

                # CES utilization metrics
                try:
                    vm_ids = list(tenant_map.get('vm_details', {}).keys())
                    sfs_ids = [s.get('id') for s in shares if s.get('id')] if shares else []
                    rds_ids = []
                    try:
                        dbs = adv_client.get_databases(project_id)
                        for d in dbs:
                            rid = d.get('id')
                            if rid:
                                rds_ids.append(rid)
                            rname = (d.get('name') or '').strip().lower()
                            if rname:
                                merged['db_name_to_id'][rname] = rid or ''
                        if rds_ids:
                            self.logger.info(f"RDS instances for CES: {len(rds_ids)}")
                    except Exception as e:
                        self.logger.warning(f"RDS fetch for CES failed: {e}")
                    utilization = adv_client.build_ces_utilization_map(
                        project_id,
                        vm_ids=vm_ids,
                        sfs_share_ids=sfs_ids,
                        rds_ids=rds_ids,
                        hours=24,
                    )
                    merged['ces_utilization'].update(utilization)
                    self.logger.info(
                        f"CES metrics for tenant '{name}': "
                        f"{len(utilization)} resources with utilization data"
                    )
                except Exception as e:
                    self.logger.warning(f"CES metrics failed for tenant '{name}': {e}")

            except Exception as e:
                self.logger.warning(f"Advanced ID map failed for tenant '{name}': {e}")

        self.logger.info(
            f"Advanced ID map total: {len(merged['disk_to_vm'])} disk→vm, "
            f"{len(merged['vm_to_cluster'])} vm→cluster, "
            f"{len(merged['vm_details'])} vm_details, "
            f"{len(merged['sfs_shares'])} sfs_shares, "
            f"{len(merged['ces_utilization'])} ces_utilization"
        )
        return merged

    def _extract_base_name_for_grouping(self, name: str, resource_type: str) -> str:
        """
        Extract base name for heuristic VM+disk grouping when names differ.
        e.g. prod01-nodepool-dmz2-az2-8ywxb-volume-0000 -> prod01-nodepool-dmz2-az2-8ywxb
        """
        if not name or resource_type not in ('server', 'volume'):
            return name or ''
        name_lower = name.lower()
        # Strip volume/disk suffixes for volumes to match VM base name
        if resource_type == 'volume':
            base = name
            # Common pattern: VM boot/data disks named "<vm-name>-volume..." should attach to VM "<vm-name>"
            # Examples:
            # - vm-foo-bar-volume
            # - vm-foo-bar-volume-data-opensearch
            # - vm-21sch-hq-gitlab-01-infra-infra-volume-data-0001 -> vm-21sch-hq-gitlab-01-infra
            if name_lower.startswith('vm-') and '-volume' in name_lower:
                idx = name_lower.index('-volume')
                if idx > 0:
                    base = name[:idx].rstrip('-')
            elif name_lower.endswith('-infra-infra'):
                base = name[:-6].rstrip('-')
            else:
                for pattern in [
                    r'-volume$', r'-volume-\d+$', r'-volume-\w+$', r'-volume_\w+$',
                    r'-volume-data-cache-\d+$', r'-volume-data-\d+$',
                    r'-disk-\d+$', r'-disk-\w+$', r'-disk_[a-f0-9-]+$',
                    r'-data\d+$', r'-data-\d+$',
                    r'-ext4-empty$', r'-ext4-empty-\d+$',
                ]:
                    m = re.search(pattern, name_lower)
                    if m:
                        base = name[:m.start()].rstrip('-')
                        break
            if base.lower().endswith('-infra-infra'):
                base = base[:-6].rstrip('-')
            return base
        return name

    def _create_unified_resources_by_name(self, billing_data: Dict, billing_resources_by_type: Dict,
                                          resources: Dict, account_billing: Dict,
                                          disk_to_vm: Optional[Dict[str, Dict[str, str]]] = None,
                                          advanced_id_map: Optional[Dict[str, Any]] = None) -> List:
        """
        Group resources by resource_name. Uses disk-to-VM / vm-to-cluster maps from Advanced API
        when available; falls back to heuristic base-name matching for Evolution-only accounts.
        """
        disk_to_vm = disk_to_vm or {}
        advanced_id_map = advanced_id_map or {}
        vm_details: Dict[str, Dict] = advanced_id_map.get('vm_details', {})
        vm_to_cluster: Dict[str, Dict] = advanced_id_map.get('vm_to_cluster', {})
        cluster_details: Dict[str, Dict] = advanced_id_map.get('cluster_details', {})
        vm_name_to_id: Dict[str, str] = advanced_id_map.get('vm_name_to_id', {})
        db_name_to_id: Dict[str, str] = advanced_id_map.get('db_name_to_id', {})
        sfs_shares: Dict[str, Dict] = advanced_id_map.get('sfs_shares', {})
        ces_utilization: Dict[str, Dict] = advanced_id_map.get('ces_utilization', {})
        from app.providers.resource_registry import ProviderResource

        # Infer Kubernetes clusters from VM naming ("<cluster>-nodepool-...").
        # Cloud.ru often bills MK8S only as ECS nodes; no explicit "Kubernetes" servname appears.
        nodepool_clusters: List[str] = []
        # CCE cluster names from explicit CCE control-plane billing lines (Контейнеры CCE).
        # These are used to group CCE worker VMs whose names embed the cluster name.
        cce_clusters: List[str] = []
        server_names_lower: set = set()
        server_name_lookup: Dict[str, str] = {}
        server_norm_map: Dict[Tuple[str, ...], List[str]] = {}
        try:
            clusters_set = set()
            for _t, items in (billing_resources_by_type or {}).items():
                for _rid, info in (items or {}).items():
                    nm = str((info or {}).get('resource_name') or '').strip()
                    low = nm.lower()
                    if nm and '-nodepool-' in low:
                        clusters_set.add(nm[:low.index('-nodepool-')])
            nodepool_clusters = sorted(clusters_set, key=lambda s: (-len(s), s.lower()))
        except Exception:
            nodepool_clusters = []
        try:
            # CCE cluster names come from billing lines with servname containing 'cce' or 'контейнеры'
            # (resource_type='kubernetes' after _map_consumption_to_resource_type).
            k8s_items = billing_resources_by_type.get('kubernetes') or {}
            cce_set = set()
            for _rid, info in k8s_items.items():
                nm = str((info or {}).get('resource_name') or '').strip()
                if nm:
                    cce_set.add(nm.lower())
            # Sort longest first so more-specific names match before shorter ones
            cce_clusters = sorted(cce_set, key=lambda s: (-len(s), s))
        except Exception:
            cce_clusters = []
        try:
            for _rid, info in (billing_resources_by_type.get('server') or {}).items():
                nm = str((info or {}).get('resource_name') or '').strip()
                if nm:
                    server_names_lower.add(nm.lower())
                    server_name_lookup[nm.lower()] = nm
            # Normalized token index for fuzzy matching (ignore 'vm' token and numeric tokens like '01')
            def _norm_tokens(s: str) -> Tuple[str, ...]:
                toks = [t for t in str(s).lower().split('-') if t]
                toks = [t for t in toks if not re.fullmatch(r'\\d+', t)]
                if toks and toks[0] == 'vm':
                    toks = toks[1:]
                return tuple(toks)
            for low, orig in server_name_lookup.items():
                key = _norm_tokens(orig)
                if key:
                    server_norm_map.setdefault(key, []).append(orig)
        except Exception:
            server_names_lower = set()
            server_name_lookup = {}
            server_norm_map = {}

        # Group by grouping_key: use base name for server+volume to merge vm+disk with different names
        # plus stronger heuristics for DB volumes and EIP bandwidth add-ons.
        groups: Dict[str, List[Tuple[str, Dict, str]]] = {}
        for resource_type, items in billing_resources_by_type.items():
            for resource_id, billing_info in items.items():
                name = billing_info.get('resource_name') or resource_id
                grouping_key = None

                # 0) Managed Kubernetes (CCE) control-plane charge is a deployable cluster line.
                # Map it into the same cluster key so cluster cards include masters/control-plane cost.
                serv_l = str((billing_info or {}).get('servname', '')).lower()
                if (not grouping_key) and (resource_type == 'kubernetes' or 'контейнеры' in serv_l or 'cce' in serv_l):
                    nm = str(name).strip()
                    if nm:
                        grouping_key = f'k8s:{nm.lower()}'

                # 0b) Backup (CBR) is attached to a VM: merge `vault-*` lines into the owning VM when possible.
                # Examples:
                # - vault-vm-21sch-hq-1c-01-infra -> vm-21sch-hq-1c-01-infra
                # - vault-21sch-hq-atlassian-01-infra -> vm-21sch-hq-atlassian-01-infra (if exists)
                if not grouping_key:
                    sku_l = str((billing_info or {}).get('sku', '')).lower()
                    nm = str(name).strip()
                    nm_l = nm.lower()
                    if nm_l.startswith('vault-') and (('резерв' in serv_l) or ('cbr' in serv_l) or ('vault.backup' in sku_l)):
                        base = nm[6:]
                        base_l = base.lower()
                        if base_l in server_names_lower:
                            grouping_key = server_name_lookup.get(base_l, base)
                        elif f"vm-{base_l}" in server_names_lower:
                            grouping_key = server_name_lookup.get(f"vm-{base_l}", f"vm-{base}")
                        else:
                            # Fuzzy match: normalize tokens and require a single exact normalized match.
                            base_key = tuple([t for t in base_l.split('-') if t and not re.fullmatch(r'\\d+', t)])
                            vm_base_key = tuple(['vm'] + list(base_key))
                            candidates = server_norm_map.get(base_key, []) or server_norm_map.get(vm_base_key, [])
                            if len(candidates) == 1:
                                grouping_key = candidates[0]
                            else:
                                grouping_key = base

                # 0) Kubernetes Persistent Volumes (PVC): these are deploy-time k8s artifacts, not standalone infra.
                # Billing uses opaque names like "pvc-<uuid>" → group into one "Kubernetes Persistent Volumes" card.
                if resource_type == 'volume':
                    nm0 = str(name).strip().lower()
                    if nm0.startswith('pvc-'):
                        grouping_key = 'k8s-persistent-volumes'

                # 1) DB instance sub-resources often have resource_id like "<db_uuid>in03.volume"
                # or "<db_uuid>in03.vm".  Cloud.ru RDS uses dashless 32-hex-char UUIDs
                # (e.g. 09277e44…in03.volume) while the regex must also accept the
                # standard 36-char dashed form.  Match .vm too so that when only
                # one billing line survives (e.g. shutdown DB still bills storage),
                # the resource still groups under its DB key.
                rid = str(resource_id)
                m = re.match(r'^([0-9a-fA-F-]{32,36}).*\.(volume|disk|storage|vm)$', rid)
                if m:
                    grouping_key = f"db:{m.group(1).lower()}"

                # 2) EIP bandwidth add-on lines often have resource_name prefixed with "bw-"
                if not grouping_key and resource_type == 'network':
                    nm = str(name).strip()
                    if nm.lower().startswith('bw-') and len(nm) > 3:
                        grouping_key = nm[3:]  # pair with the base resource name

                # 3) Kubernetes clusters: group all nodepool nodes (and their volumes) under cluster key
                nm_l = str(name).lower()
                if not grouping_key and '-nodepool-' in nm_l:
                    grouping_key = f"k8s:{str(name)[:nm_l.index('-nodepool-')].lower()}"
                # 3b) Also attach obvious cluster-related network add-ons to the cluster (LB/EIP)
                if (not grouping_key and resource_type == 'network' and nodepool_clusters
                        and isinstance(name, str) and name):
                    low = nm_l
                    # Only if name looks like cluster-scoped networking
                    if any(tok in low for tok in ('eip', 'bandwidth', 'lb', 'nlb')):
                        for cluster in nodepool_clusters:
                            cl = cluster.lower()
                            if low.startswith(cl + '-'):
                                grouping_key = f'k8s:{cl}'
                                break

                # 3c) K8s node volumes: disk billed as "vm-{cluster}-{suffix}" (no -nodepool- in name)
                if (not grouping_key and resource_type == 'volume' and nodepool_clusters
                        and isinstance(name, str) and name):
                    for cluster in nodepool_clusters:
                        cl = cluster.lower()
                        if nm_l.startswith(f'vm-{cl}-') or nm_l == f'vm-{cl}':
                            grouping_key = f'k8s:{cl}'
                            break
                        if nm_l.startswith(cl + '-') or nm_l == cl:
                            grouping_key = f'k8s:{cl}'
                            break

                # 3d) Volume→VM via Advanced API EVS attachments (most reliable).
                # Match billing resource_id to EVS volume UUID; no name fallback
                # needed for volumes since EVS UUIDs match billing directly.
                if not grouping_key and resource_type == 'volume' and disk_to_vm:
                    vm_info = disk_to_vm.get(rid) or disk_to_vm.get(rid.lower())
                    if vm_info:
                        vm_name = (vm_info.get('vm_name') or '').strip()
                        if vm_name:
                            grouping_key = vm_name
                            self.logger.debug(f"Volume {rid[:8]}... grouped with VM {vm_name} (Advanced EVS)")

                # 3e) VM→Cluster via Advanced API node naming (when vm resource_id is a UUID)
                if not grouping_key and resource_type == 'server' and vm_to_cluster:
                    cluster_info = vm_to_cluster.get(rid) or vm_to_cluster.get(rid.lower())
                    if not cluster_info and vm_name_to_id:
                        name_l = str(name).strip().lower()
                        vm_uuid = vm_name_to_id.get(name_l)
                        if vm_uuid:
                            cluster_info = vm_to_cluster.get(vm_uuid)
                    if cluster_info:
                        cluster_name = (cluster_info.get('cluster_name') or '').strip()
                        if cluster_name:
                            grouping_key = f'k8s:{cluster_name.lower()}'
                            self.logger.debug(f"VM {rid[:8]}... grouped with cluster {cluster_name} (Advanced CCE)")

                # 3f) CCE worker VMs and their volumes: Cloud.ru CCE worker node names embed
                # the CCE cluster name literally.
                # Pattern A: vm-{nodepool}-{cce-cluster-name}-{az}-{random5}
                # Example: vm-sdp-workers1-cce-mgmt-shared-shared-u92rt → cluster cce-mgmt-shared
                # We match by checking if "-{cluster-name}-" appears as a substring of the VM name.
                # NOTE: For volumes, step 3d may have already set grouping_key to the VM name (e.g.
                # "vm-sdp-workers1-cce-mgmt-shared-shared-u92rt"). We deliberately override that key
                # so the volumes end up inside the CCE cluster group rather than floating standalone.
                #
                # Pattern B: node(-pool)?-{base}-k8s-cce-{az}-{pool}-{env}[-suffix]
                # Example: node-21sch-hq-k8s-cce-az2-applicant-02-prod → cluster cce-21sch-hq-k8s-prod
                # Here the cluster name is NOT embedded literally; instead the cluster's base and
                # environment appear at different positions in the node name.
                if resource_type in ('server', 'volume') and cce_clusters:
                    # Determine which name to test: prefer the current grouping_key (VM name from step 3d)
                    # so that volumes grouped to a CCE worker VM are promoted to the cluster.
                    check_name = (grouping_key or nm_l).lower()
                    matched_cce = False
                    for cname in cce_clusters:
                        # Pattern A: cluster name appears as literal substring
                        if f'-{cname}-' in check_name or check_name.startswith(f'{cname}-') or check_name == cname:
                            new_key = f'k8s:{cname}'
                            if grouping_key != new_key:
                                self.logger.debug(
                                    f"{resource_type} '{name[:40]}' grouped into CCE cluster '{cname}' (name embedding)"
                                )
                                grouping_key = new_key
                            matched_cce = True
                            break
                    if not matched_cce and ('k8s' in check_name and 'cce' in check_name):
                        # Pattern B: node-{base}-k8s-cce-{az}-...-{env} style names.
                        # Try each cluster whose name is "cce-{base}-{env}": check if {base} is in
                        # the node name AND the {env} suffix also appears in the node name.
                        _ENV_KEYWORDS = ('prod', 'stage', 'infra', 'test', 'dev', 'rocketchat')
                        for cname in cce_clusters:
                            for env_word in _ENV_KEYWORDS:
                                if not cname.endswith(f'-{env_word}'):
                                    continue
                                # Strip env suffix and optional 'cce-' prefix to get the base
                                cluster_base = cname[:-len(env_word) - 1]  # e.g. "cce-21sch-hq-k8s"
                                if cluster_base.startswith('cce-'):
                                    cluster_base = cluster_base[4:]       # e.g. "21sch-hq-k8s"
                                if not cluster_base or len(cluster_base) < 5:
                                    continue
                                # Match: base appears in node name AND env suffix also present
                                if (cluster_base in check_name and
                                        (check_name.endswith(f'-{env_word}') or
                                         f'-{env_word}-' in check_name)):
                                    new_key = f'k8s:{cname}'
                                    if grouping_key != new_key:
                                        self.logger.debug(
                                            f"{resource_type} '{name[:40]}' grouped into CCE cluster "
                                            f"'{cname}' (base+env pattern)"
                                        )
                                        grouping_key = new_key
                                    matched_cce = True
                                    break
                            if matched_cce:
                                break

                # 4) Default heuristic: for server/volume, use base name so vm-x and vm-x-volume-0000 group
                if not grouping_key:
                    grouping_key = self._extract_base_name_for_grouping(name, resource_type)
                    # For volumes: if base doesn't match a server but "vm-{base}" does, use that server
                    if resource_type == 'volume' and grouping_key:
                        base_l = grouping_key.lower()
                        if base_l in server_names_lower:
                            grouping_key = server_name_lookup.get(base_l, grouping_key)
                        elif f"vm-{base_l}" in server_names_lower:
                            grouping_key = server_name_lookup.get(f"vm-{base_l}", f"vm-{grouping_key}")
                        else:
                            base_key = tuple([t for t in base_l.split('-') if t and not re.fullmatch(r'\d+', t)])
                            vm_base_key = tuple(['vm'] + list(base_key))
                            candidates = server_norm_map.get(base_key, []) or server_norm_map.get(vm_base_key, [])
                            if len(candidates) == 1:
                                grouping_key = candidates[0]
                            else:
                                prefix_match = [s for s in server_names_lower if s.startswith(f'vm-{base_l}-') or s.startswith(f'{base_l}-')]
                                if len(prefix_match) == 1:
                                    grouping_key = server_name_lookup.get(prefix_match[0], grouping_key)

                if grouping_key not in groups:
                    groups[grouping_key] = []
                groups[grouping_key].append((resource_id, billing_info, resource_type))

        unified_resources = []
        for grouping_key, components in groups.items():
            try:
                # Display name: prefer primary component name (db/k8s/server), else grouping_key
                resource_name = str(grouping_key)
                preferred_types = ('kubernetes', 'database', 'server')
                for rid, info, t in components:
                    if t in preferred_types and (info.get('resource_name') or '').strip():
                        resource_name = info.get('resource_name').strip()
                        break
                # Strip internal prefixes from display
                if resource_name.startswith('db:'):
                    resource_name = resource_name[3:]
                if resource_name.startswith('k8s:'):
                    resource_name = resource_name[4:]
                # For inferred k8s groups, force cluster name (not a node name)
                if isinstance(grouping_key, str) and grouping_key.startswith('k8s:'):
                    resource_name = grouping_key[4:]

                # Sum cost across all components
                total_daily_cost = sum(b[1].get('daily_cost', 0) for b in components)
                # Infer unified resource type from components
                component_types = [c[2] for c in components]
                unified_type = self._infer_unified_type(component_types, components)
                # Semantic type for card display (vm, k8s, db, etc.) - stored in provider_config
                display_type = self._infer_display_type(component_types, components)
                if isinstance(grouping_key, str) and grouping_key.startswith('k8s:'):
                    unified_type = 'kubernetes-cluster'
                    display_type = 'kubernetes-cluster'
                # File storage / NFS: separate type for pricing comparison
                servnames_lower = [str((info or {}).get('servname', '')).lower() for _, info, _ in components]
                if unified_type == 'volume' and any(('nfs' in s) or ('sfs' in s) or ('файлов' in s) for s in servnames_lower):
                    unified_type = 'file_storage'
                    display_type = 'file_storage'
                # Image template / IMS
                if unified_type == 'volume' and any(('управления образами' in s) or ('ims' in s) or ('образ' in s) for s in servnames_lower):
                    display_type = 'image-template'
                # Backup-only groups
                if unified_type == 'other' and ('backup' in set(component_types)) and ('server' not in set(component_types)):
                    unified_type = 'backup'
                    display_type = 'backup'
                # KMS-only groups
                if unified_type == 'other' and ('kms' in set(component_types)) and len(set(component_types)) == 1:
                    display_type = 'kms'
                # Build provider_config with component breakdown
                component_count = len(components)
                # Avoid huge provider_config payloads for very large groups (e.g., hundreds of PVC volumes)
                # MySQL TEXT can overflow; keep a compact summary and a small sample.
                max_components_in_config = 200
                if component_count > max_components_in_config:
                    by_type = {}
                    for rid, info, t in components:
                        if t not in by_type:
                            by_type[t] = {'type': t, 'count': 0, 'daily_cost': 0.0}
                        by_type[t]['count'] += 1
                        by_type[t]['daily_cost'] += float(info.get('daily_cost', 0) or 0.0)
                    component_list = list(by_type.values())
                    component_sample = [
                        {
                            'resource_id': rid,
                            'resource_name': (info.get('resource_name') or rid)[:80],
                            'type': t,
                            'servname': info.get('servname', '')[:60],
                            'daily_cost': info.get('daily_cost', 0),
                        }
                        for rid, info, t in components[:20]
                    ]
                else:
                    component_list = [
                        {
                            'resource_id': rid,
                            'resource_name': (info.get('resource_name') or rid)[:80],
                            'type': t,
                            'servname': info.get('servname', '')[:60],
                            'daily_cost': info.get('daily_cost', 0),
                        }
                        for rid, info, t in components
                    ]
                    component_sample = None
                # Stable resource_id for DB (unique per provider)
                unified_resource_id = f"unified-{hashlib.md5(grouping_key.encode()).hexdigest()[:24]}"
                # Region + tenant from first component (Cloud.ru billing meta)
                region = (
                    components[0][1].get('iam_project_name') or components[0][1].get('platform') or 'Cloud.ru'
                ) if components else 'Cloud.ru'
                tenant = (
                    components[0][1].get('tenant_name') or None
                ) if components else None
                # Service name from unified type
                service_map = {
                    'server': 'Compute',
                    'kubernetes-cluster': 'Kubernetes',
                    'load_balancer': 'Load Balancer',
                    'database': 'Database',
                    'volume': 'Block Storage',
                    'file_storage': 'File Storage',
                    'network': 'Network',
                    's3': 'Object Storage',
                    'backup': 'Backup',
                }
                service_name = service_map.get(unified_type, unified_type.replace('-', ' ').replace('_', ' ').title())
                if grouping_key == 'k8s-persistent-volumes':
                    service_name = 'Kubernetes'
                if display_type == 'image-template':
                    service_name = 'Image Template'
                if display_type == 'kms':
                    service_name = 'KMS'
                if display_type == 'logging':
                    service_name = 'Logging'

                provider_config = {
                    'unified': True,
                    'unified_display_type': display_type,  # vm, kubernetes-cluster, postgresql-cluster, etc.
                    'grouping_key': grouping_key,
                    'components': component_list,
                    'component_count': component_count,
                    'billing_source': 'consumption_api',
                }
                if component_sample is not None:
                    provider_config['components_truncated'] = True
                    provider_config['components_sample'] = component_sample
                # Add first component's details for card display
                first_info = components[0][1]
                provider_config.update({
                    'servname': first_info.get('servname', ''),
                    'sku': first_info.get('sku', ''),
                    'platform': first_info.get('platform', 'Cloud.ru'),
                    'iam_project_name': first_info.get('iam_project_name', ''),
                    'tenant_name': first_info.get('tenant_name', ''),
                })

                # --- Advanced API enrichment ---
                # For VM groups: overlay real CPU/RAM/disk/IP from vm_details.
                # Match by billing resource_id → Advanced server UUID; fall back
                # to billing resource_name → Advanced VM name when UUID differs.
                if display_type == 'server' and vm_details:
                    for comp_rid, comp_info, comp_t in components:
                        if comp_t == 'server':
                            vd = vm_details.get(comp_rid) or vm_details.get(comp_rid.lower())
                            if not vd and vm_name_to_id:
                                comp_name = (comp_info.get('resource_name') or '').strip().lower()
                                vm_uuid = vm_name_to_id.get(comp_name)
                                if vm_uuid:
                                    vd = vm_details.get(vm_uuid)
                            if vd:
                                if vd.get('cpu_cores'):
                                    provider_config['cpu_cores'] = vd['cpu_cores']
                                    provider_config['vcpus'] = vd['cpu_cores']
                                if vd.get('ram_mb'):
                                    provider_config['ram_mb'] = vd['ram_mb']
                                    provider_config['memory_mb'] = vd['ram_mb']
                                if vd.get('disk_gb'):
                                    provider_config['disk_gb'] = vd['disk_gb']
                                    provider_config['total_storage_gb'] = vd['disk_gb']
                                if vd.get('external_ip'):
                                    provider_config['external_ip'] = vd['external_ip']
                                if vd.get('status'):
                                    provider_config['status'] = vd['status']
                                if vd.get('flavor_name'):
                                    provider_config['flavor_name'] = vd['flavor_name']
                                if vd.get('availability_zone'):
                                    provider_config['availability_zone'] = vd['availability_zone']
                                if vd.get('attached_volume_ids'):
                                    provider_config['attached_volume_ids'] = vd['attached_volume_ids']
                                break  # Use first matched VM

                # For k8s cluster groups: aggregate node specs from vm_details
                if display_type == 'kubernetes-cluster' and vm_details and vm_to_cluster:
                    cluster_name_key = grouping_key[4:] if isinstance(grouping_key, str) and grouping_key.startswith('k8s:') else ''
                    node_vcpus = 0
                    node_ram_mb = 0
                    node_count = 0
                    for vm_id, cluster_info in vm_to_cluster.items():
                        if (cluster_info.get('cluster_name') or '').lower() == cluster_name_key:
                            vd = vm_details.get(vm_id, {})
                            node_vcpus += vd.get('cpu_cores', 0)
                            node_ram_mb += vd.get('ram_mb', 0)
                            node_count += 1
                    if node_count:
                        provider_config['total_nodes'] = node_count
                        provider_config['total_vcpus'] = node_vcpus
                        provider_config['total_ram_gb'] = round(node_ram_mb / 1024, 1)
                        provider_config['cpu_cores'] = node_vcpus
                        provider_config['ram_mb'] = node_ram_mb

                # --- SFS Turbo enrichment ---
                if display_type == 'file_storage' and sfs_shares:
                    for comp_rid, comp_info, comp_t in components:
                        share = sfs_shares.get(comp_rid)
                        if share:
                            try:
                                total_gb = float(share.get('size', 0))
                                avail_gb = float(share.get('avail_capacity', 0))
                                used_gb = total_gb - avail_gb
                                provider_config['total_storage_gb'] = total_gb
                                provider_config['used_storage_gb'] = round(used_gb, 1)
                                provider_config['avail_storage_gb'] = round(avail_gb, 1)
                                if total_gb > 0:
                                    provider_config['storage_used_pct'] = round(used_gb / total_gb * 100, 1)
                                provider_config['share_type'] = share.get('share_type', '')
                                provider_config['share_proto'] = share.get('share_proto', '')
                                provider_config['export_location'] = share.get('export_location', '')
                                provider_config['availability_zone'] = share.get('az_name', '')
                            except (ValueError, TypeError):
                                pass
                            break

                # --- CES utilization enrichment ---
                ces_tags: Dict[str, str] = {}
                if ces_utilization:
                    matched_ces: Optional[Dict] = None
                    matched_ces_id = ''
                    for comp_rid, comp_info, comp_t in components:
                        if comp_rid in ces_utilization:
                            matched_ces = ces_utilization[comp_rid]
                            matched_ces_id = comp_rid
                            break
                        rid_lower = comp_rid.lower()
                        if rid_lower in ces_utilization:
                            matched_ces = ces_utilization[rid_lower]
                            matched_ces_id = rid_lower
                            break
                    # For VMs: also try name-based CES lookup
                    if not matched_ces and display_type == 'server' and vm_name_to_id:
                        for comp_rid, comp_info, comp_t in components:
                            if comp_t == 'server':
                                cname = (comp_info.get('resource_name') or '').strip().lower()
                                vm_uuid = vm_name_to_id.get(cname)
                                if vm_uuid and vm_uuid in ces_utilization:
                                    matched_ces = ces_utilization[vm_uuid]
                                    matched_ces_id = vm_uuid
                                    break
                    # For databases: try name-based CES lookup (billing resource_id may differ from RDS instance id)
                    if not matched_ces and display_type == 'database' and db_name_to_id:
                        for comp_rid, comp_info, comp_t in components:
                            cname = (comp_info.get('resource_name') or '').strip().lower()
                            rds_id = db_name_to_id.get(cname)
                            if rds_id and rds_id in ces_utilization:
                                matched_ces = ces_utilization[rds_id]
                                matched_ces_id = rds_id
                                break
                    # For k8s: aggregate node metrics
                    if not matched_ces and display_type == 'kubernetes-cluster' and vm_to_cluster:
                        cluster_key = grouping_key[4:] if isinstance(grouping_key, str) and grouping_key.startswith('k8s:') else ''
                        node_metrics: List[Dict] = []
                        for vm_id, ci in vm_to_cluster.items():
                            if (ci.get('cluster_name') or '').lower() == cluster_key and vm_id in ces_utilization:
                                node_metrics.append(ces_utilization[vm_id])
                        if node_metrics:
                            agg: Dict[str, Dict[str, float]] = {}
                            for nm in node_metrics:
                                for metric, vals in nm.items():
                                    if metric not in agg:
                                        agg[metric] = {'avg': 0, 'max': 0, 'count': 0}
                                    agg[metric]['avg'] += vals.get('avg', 0)
                                    agg[metric]['max'] = max(agg[metric]['max'], vals.get('max', 0))
                                    agg[metric]['count'] += 1
                            matched_ces = {}
                            for metric, a in agg.items():
                                cnt = a['count'] or 1
                                matched_ces[metric] = {
                                    'avg': round(a['avg'] / cnt, 2),
                                    'max': round(a['max'], 2),
                                    'nodes': cnt,
                                }

                    if matched_ces:
                        provider_config['ces_metrics'] = matched_ces
                        # Map to template-compatible tags
                        cpu = matched_ces.get('cpu_util') or matched_ces.get('rds001_cpu_util')
                        if cpu:
                            ces_tags['cpu_avg_usage'] = str(cpu.get('avg', 0))
                            ces_tags['cpu_max_usage'] = str(cpu.get('max', 0))
                        mem = matched_ces.get('rds002_mem_util')
                        if mem:
                            ces_tags['memory_usage_percent'] = str(mem.get('avg', 0))
                        # Disk utilization (RDS)
                        disk_util = matched_ces.get('rds039_disk_util')
                        if disk_util:
                            ces_tags['disk_util_percent'] = str(disk_util.get('avg', 0))
                        # SFS used capacity percent
                        sfs_pct = matched_ces.get('used_capacity_percent')
                        if sfs_pct:
                            ces_tags['storage_used_percent'] = str(sfs_pct.get('avg', 0))
                        # Network (ECS)
                        net_in = matched_ces.get('network_incoming_bytes_aggregate_rate')
                        net_out = matched_ces.get('network_outgoing_bytes_aggregate_rate')
                        if net_in:
                            ces_tags['net_in_avg_bps'] = str(net_in.get('avg', 0))
                        if net_out:
                            ces_tags['net_out_avg_bps'] = str(net_out.get('avg', 0))
                        # ELB active connections
                        elb_conn = matched_ces.get('m2_act_conn')
                        if elb_conn:
                            ces_tags['elb_active_conn_avg'] = str(elb_conn.get('avg', 0))

                resource_tags = {'cloud_ru_unified': 'true'}
                resource_tags.update(ces_tags)

                unified_resources.append(ProviderResource(
                    resource_id=unified_resource_id,
                    resource_name=resource_name,
                    resource_type=unified_type,
                    service_name=service_name,
                    region=region,
                    tenant=tenant,
                    status='RUNNING',
                    effective_cost=total_daily_cost,
                    currency=account_billing.get('currency', 'RUB'),
                    billing_period='daily',
                    provider_config=provider_config,
                    provider_type='cloud-ru',
                    tags=resource_tags,
                ))
            except Exception as e:
                self.logger.warning(f"Failed to create unified resource for {resource_name}: {e}")

        self.logger.info(f"Created {len(unified_resources)} unified resources (grouped by name)")
        return unified_resources

    def _infer_unified_type(self, component_types: List[str], components: List[Tuple]) -> str:
        """Infer unified resource type from component types.

        Types must match the cross-provider taxonomy used by Beget, Selectel,
        and Yandex so pricing comparison works correctly.
        """
        types_set = set(component_types)
        if 'database' in types_set:
            return 'database'
        for t in ['postgresql-cluster', 'mysql-cluster', 'kafka-cluster', 'redis-cluster']:
            if t in types_set:
                return 'database'
        if 'kubernetes' in types_set:
            return 'kubernetes-cluster'
        if 'load_balancer' in types_set:
            return 'load_balancer'
        if 'server' in types_set:
            return 'server'
        if 'backup' in types_set and 'server' not in types_set:
            return 'backup'
        if 'volume' in types_set and 'network' not in types_set:
            return 'volume'
        if 'network' in types_set and 'volume' not in types_set:
            return 'network'
        if 'volume' in types_set:
            return 'volume'
        if 's3' in types_set:
            return 's3'
        if 'logging' in types_set:
            return 'other'
        if 'kms' in types_set:
            return 'other'
        return 'other'

    def _infer_display_type(self, component_types: List[str], components: List[Tuple]) -> str:
        """Semantic type for card display (vm, kubernetes-cluster, etc.)."""
        types_set = set(component_types)
        if 'database' in types_set:
            return 'database'
        for t in ['postgresql-cluster', 'mysql-cluster', 'kafka-cluster', 'redis-cluster']:
            if t in types_set:
                return t
        if 'kubernetes' in types_set:
            return 'kubernetes-cluster'
        if 'backup' in types_set and 'server' not in types_set:
            return 'backup'
        if 'kms' in types_set and len(types_set) == 1:
            return 'kms'
        if 'logging' in types_set and len(types_set) == 1:
            return 'logging'
        if 'load_balancer' in types_set:
            return 'load_balancer'
        if 'server' in types_set:
            return 'server'  # VM
        if 'volume' in types_set:
            return 'volume'
        if 'network' in types_set:
            return 'network'
        if 's3' in types_set:
            return 's3'
        return 'other'

    def _create_unified_vm(self, vm_data: Dict[str, Any], account_billing: Dict[str, Any]) -> Optional:
        """Create unified VM resource from Cloud.ru VM data"""
        from app.providers.resource_registry import ProviderResource
        
        resource_id = vm_data.get('id')
        if not resource_id:
            return None
        
        resource_name = vm_data.get('name') or f"VM-{resource_id[:8]}"
        
        # Map Cloud.ru state to unified status (RUNNING/STOPPED for template display)
        cloud_ru_state = vm_data.get('state', '').lower()
        status_mapping = {
            'active': 'RUNNING',
            'running': 'RUNNING',
            'stopped': 'STOPPED',
            'paused': 'STOPPED',
            'suspended': 'STOPPED',
            'error': 'STOPPED',
            'deleted': 'STOPPED'
        }
        status = status_mapping.get(cloud_ru_state, cloud_ru_state.upper() if cloud_ru_state else 'RUNNING')
        
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
        raw_status = (volume_data.get('status') or 'unknown').lower()
        status_map = {'in-use': 'RUNNING', 'in_use': 'RUNNING', 'available': 'RUNNING', 'attached': 'RUNNING'}
        status = status_map.get(raw_status, raw_status.upper() if raw_status else 'RUNNING')
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
        
        resource_name = (billing_info.get('resource_name') or billing_info.get('servname', '') or
                        f"{resource_type.title()}-{resource_id[:8]}")
        daily_cost = billing_info.get('daily_cost', 0.0)
        monthly_cost = billing_info.get('monthly_cost', daily_cost * 30.0)
        
        # Region (Cloud.ru: use billing meta.iam_project_name) + tenant (meta.tenant_name)
        region = billing_info.get('iam_project_name') or 'unknown'
        if region == 'unknown' and billing_info.get('consumptions'):
            first_consumption = billing_info['consumptions'][0]
            meta = first_consumption.get('meta') if isinstance(first_consumption.get('meta'), dict) else {}
            region = (meta.get('iam_project_name') or first_consumption.get('region') or
                      first_consumption.get('availability_zone') or first_consumption.get('zone') or
                      first_consumption.get('platform') or 'unknown')
        if region == 'unknown' and billing_info.get('platform'):
            region = billing_info['platform']
        tenant = billing_info.get('tenant_name') or None
        if not tenant and billing_info.get('consumptions'):
            first_consumption = billing_info['consumptions'][0]
            meta = first_consumption.get('meta') if isinstance(first_consumption.get('meta'), dict) else {}
            tenant = meta.get('tenant_name') or meta.get('tenantName') or None
        
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
        sku = billing_info.get('sku', '')
        provider_config = {
            'resource_id': resource_id,
            'resource_name': resource_name,
            'servname': billing_info.get('servname', ''),
            'sku': sku,
            'sku_name': billing_info.get('sku_name', ''),
            'platform': billing_info.get('platform', ''),
            'iam_project_name': billing_info.get('iam_project_name', ''),
            'tenant_name': billing_info.get('tenant_name', ''),
            'billing_source': 'consumption_api',
            'consumptions': billing_info.get('consumptions', [])
        }
        # Parse SKU for VM/volume specs (vCPU, RAM, disk) for tile display
        sku_for_parse = sku or billing_info.get('sku_name', '')
        if sku_for_parse and resource_type == 'server':
            parsed = self._parse_sku_specs(sku_for_parse)
            if parsed:
                provider_config.update(parsed)
        elif sku_for_parse and resource_type == 'volume':
            # Extract volume size from SKU (e.g. "20GB", "100" in sku name)
            size_gb = self._parse_volume_size_from_consumption(billing_info)
            if size_gb:
                provider_config['size_gb'] = size_gb
                provider_config['storage_gb'] = size_gb
        
        return ProviderResource(
            resource_id=resource_id,
            resource_name=resource_name,
            resource_type=resource_type if resource_type != 'unknown' else 'other',
            service_name=service_name,
            region=region,
            tenant=tenant,
            status='RUNNING',  # Assume running if being billed (for template display)
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
        
        Returns standardized pricing data for cross-provider comparison
        """
        try:
            self.logger.info("Starting Cloud.ru pricing data collection")
            
            # Get access token and project_id from client
            if not self.client.api_key or not self.client.api_secret:
                self.logger.warning("No credentials provided for Cloud.ru pricing fetch")
                return []
            
            # Authenticate to get access token
            access_token = self.client._get_access_token()
            if not access_token:
                self.logger.warning("Failed to authenticate for Cloud.ru pricing fetch")
                return []
            
            # Get project_id (should be set during authentication)
            project_id = self.client.project_id
            if not project_id:
                self.logger.warning("No project_id available for Cloud.ru pricing fetch")
                return []
            
            # Initialize pricing client
            from ..cloud_ru.pricing_client import CloudRuPricingClient
            pricing_client = CloudRuPricingClient(access_token, project_id)
            
            # Collect all pricing data
            pricing_data = pricing_client.get_all_prices()
            
            if pricing_data:
                self.logger.info(
                    "Collected %d Cloud.ru pricing records",
                    len(pricing_data)
                )
            else:
                self.logger.warning("No Cloud.ru pricing data collected")
            
            return pricing_data
            
        except Exception as exc:
            self.logger.error("Failed to collect Cloud.ru pricing: %s", exc, exc_info=True)
            return []

