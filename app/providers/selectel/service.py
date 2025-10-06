"""
Selectel provider service implementation
"""
from typing import Dict, List, Any, Optional
from app.providers.selectel.client import SelectelClient
from app.core.models.provider import CloudProvider
from app.core.models.resource import Resource
from app.core.models.sync import SyncSnapshot
from app.core.database import db
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SelectelService:
    """Service for managing Selectel provider operations"""
    
    def __init__(self, provider: CloudProvider):
        """
        Initialize Selectel service
        
        Args:
            provider: CloudProvider instance
        """
        self.provider = provider
        self.credentials = json.loads(provider.credentials)
        self.client = SelectelClient(provider.credentials)
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection to Selectel API
        
        Returns:
            Dict containing test results
        """
        try:
            result = self.client.test_connection()
            
            if result['success']:
                # Update provider metadata with account info
                account_info = result.get('account_info', {})
                self.provider.provider_metadata = json.dumps({
                    'account_name': account_info.get('name'),
                    'account_enabled': account_info.get('enabled'),
                    'account_locked': account_info.get('locked'),
                    'onboarding': account_info.get('onboarding'),
                    'last_test': datetime.now().isoformat()
                })
                db.session.commit()
            
            return result
            
        except Exception as e:
            logger.error(f"Selectel connection test failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Connection test failed'
            }
    
    def sync_resources(self) -> Dict[str, Any]:
        """
        Universal billing-first sync for ALL Selectel services
        
        Philosophy:
        1. Billing API is source of truth - shows everything that costs money
        2. Show all resources (active + zombie)
        3. Enrich with details when available
        4. Unified view where logical (VMs + volumes)
        5. Handles: VMs, Volumes, Kubernetes, Databases, S3, Load Balancers, etc.
        
        Returns:
            Dict containing sync results
        """
        try:
            # Create sync snapshot entry
            sync_snapshot = SyncSnapshot(
                provider_id=self.provider.id,
                sync_type='billing_first',
                sync_status='running',
                sync_started_at=datetime.now()
            )
            db.session.add(sync_snapshot)
            db.session.commit()
            
            # PHASE 1: Get all billed resources (48h window to catch deletions)
            logger.info("PHASE 1: Fetching billing data (48h window)")
            billed_resources = self.client.get_resource_costs(hours=48)
            
            if not billed_resources:
                logger.warning("No billed resources found - will fetch from OpenStack APIs")
                # Fallback to old approach if billing API fails
                return self._sync_resources_fallback(sync_snapshot)
            
            logger.info(f"Found {len(billed_resources)} billed resources")
            
            # PHASE 2: Group by service type
            logger.info("PHASE 2: Grouping resources by service type")
            resources_by_type = self._group_by_service_type(billed_resources)
            
            synced_resources = []
            orphan_volumes = []
            zombie_resources = []
            unified_vms = {}
            
            # PHASE 3: Process servers first (needed for volume unification)
            logger.info("PHASE 3: Processing servers")
            if 'server' in resources_by_type:
                for resource_id, billing_data in resources_by_type['server'].items():
                    vm = self._process_vm_resource(
                        resource_id,
                        billing_data,
                        sync_snapshot.id
                    )
                    if vm:
                        unified_vms[resource_id] = vm
                        synced_resources.append(vm)
                        if vm.status == 'DELETED_BILLED':
                            zombie_resources.append(vm)
                
                logger.info(f"Processed {len(unified_vms)} VMs ({len([v for v in unified_vms.values() if v.status == 'DELETED_BILLED'])} zombies)")
            
            # PHASE 4: Process volumes (unify with VMs where possible)
            logger.info("PHASE 4: Processing volumes")
            if 'volume' in resources_by_type:
                for resource_id, billing_data in resources_by_type['volume'].items():
                    volume_result = self._process_volume_resource(
                        resource_id,
                        billing_data,
                        unified_vms,
                        sync_snapshot.id
                    )
                    if volume_result:
                        if not volume_result.get('unified_into_vm'):
                            # Standalone or orphan volume
                            synced_resources.append(volume_result['resource'])
                            if volume_result.get('is_orphan'):
                                orphan_volumes.append(volume_result['resource'])
                        # Else: volume was merged into VM, no separate resource needed
                
                logger.info(f"Processed volumes: {len(orphan_volumes)} orphans, {len([v for v in resources_by_type['volume'].values()])} total")
            
            # PHASE 5: Process file storage
            logger.info("PHASE 5: Processing file storage")
            if 'file_storage' in resources_by_type:
                for resource_id, billing_data in resources_by_type['file_storage'].items():
                    share = self._process_file_storage_resource(
                        resource_id,
                        billing_data,
                        sync_snapshot.id
                    )
                    if share:
                        synced_resources.append(share)
                        if share.status == 'DELETED_BILLED':
                            zombie_resources.append(share)
            
            # PHASE 6: Process all other service types generically
            logger.info("PHASE 6: Processing other services (K8s, DBaaS, S3, etc.)")
            other_types = [t for t in resources_by_type.keys() 
                          if t not in ['server', 'volume', 'file_storage']]
            
            for service_type in other_types:
                for resource_id, billing_data in resources_by_type[service_type].items():
                    generic = self._process_generic_resource(
                        resource_id,
                        billing_data,
                        service_type,
                        sync_snapshot.id
                    )
                    if generic:
                        synced_resources.append(generic)
                        if generic.status == 'DELETED_BILLED':
                            zombie_resources.append(generic)
            
            # PHASE 7: Get statistics for active servers
            logger.info("PHASE 7: Fetching performance statistics")
            active_servers = [vm for vm in unified_vms.values() if vm.status != 'DELETED_BILLED']
            if active_servers:
                try:
                    server_data_list = []
                    for vm in active_servers:
                        metadata = json.loads(vm.provider_config) if vm.provider_config else {}
                        server_data_list.append({
                            'id': vm.resource_id,
                            'name': vm.resource_name,
                            'ram_mb': metadata.get('ram_mb', 1024)
                        })
                    
                    statistics = self.client.get_all_server_statistics(server_data_list)
                    if statistics:
                        self._process_server_statistics(sync_snapshot, statistics)
                        logger.info(f"Retrieved statistics for {len(statistics)} servers")
                except Exception as e:
                    logger.warning(f"Failed to get server statistics: {e}")
            
            # PHASE 8: Calculate totals and update snapshot
            logger.info("PHASE 8: Finalizing sync")
            total_cost = sum(r.daily_cost or 0 for r in synced_resources)
            zombie_cost = sum(r.daily_cost or 0 for r in zombie_resources)
            orphan_cost = sum(r.daily_cost or 0 for r in orphan_volumes)
            
            # Update sync snapshot
            sync_snapshot.sync_status = 'success'
            sync_snapshot.sync_completed_at = datetime.now()
            sync_snapshot.resources_created = len(synced_resources)
            sync_snapshot.total_resources_found = len(synced_resources)
            sync_snapshot.calculate_duration()
            
            # Store metadata about special cases
            sync_config = json.loads(sync_snapshot.sync_config) if sync_snapshot.sync_config else {}
            sync_config.update({
                'sync_method': 'billing_first',
                'orphan_volumes': len(orphan_volumes),
                'zombie_resources': len(zombie_resources),
                'unified_vms': len(unified_vms),
                'total_daily_cost': round(total_cost, 2),
                'zombie_daily_cost': round(zombie_cost, 2),
                'orphan_daily_cost': round(orphan_cost, 2),
                'service_types': list(resources_by_type.keys()),
                'billed_resource_count': len(billed_resources)
            })
            sync_snapshot.sync_config = json.dumps(sync_config)
            
            # Update provider
            self.provider.last_sync = datetime.now()
            self.provider.sync_status = 'success'
            self.provider.sync_error = None
            
            db.session.commit()
            
            logger.info(f"Sync completed: {len(synced_resources)} resources, {total_cost:.2f} ₽/day")
            logger.info(f"  - Active: {len(synced_resources) - len(zombie_resources)}")
            logger.info(f"  - Zombies: {len(zombie_resources)} ({zombie_cost:.2f} ₽/day)")
            logger.info(f"  - Orphan volumes: {len(orphan_volumes)} ({orphan_cost:.2f} ₽/day)")
            
            return {
                'success': True,
                'resources_synced': len(synced_resources),
                'orphan_volumes': len(orphan_volumes),
                'zombie_resources': len(zombie_resources),
                'total_daily_cost': round(total_cost, 2),
                'zombie_daily_cost': round(zombie_cost, 2),
                'orphan_daily_cost': round(orphan_cost, 2),
                'sync_snapshot_id': sync_snapshot.id,
                'service_types': list(resources_by_type.keys()),
                'message': f'Successfully synced {len(synced_resources)} resources ({total_cost:.2f} ₽/day)'
            }
            
        except Exception as e:
            logger.error(f"Selectel billing-first sync failed: {str(e)}", exc_info=True)
            
            # Update sync snapshot with error
            if 'sync_snapshot' in locals():
                sync_snapshot.sync_status = 'error'
                sync_snapshot.sync_completed_at = datetime.now()
                sync_snapshot.error_message = str(e)
                sync_snapshot.calculate_duration()
                
                # Update provider sync status to error
                self.provider.sync_status = 'error'
                self.provider.sync_error = str(e)
                
                db.session.commit()
            
            return {
                'success': False,
                'error': str(e),
                'message': 'Sync failed'
            }
    
    def _group_by_service_type(self, billed_resources: Dict[str, Any]) -> Dict[str, Dict]:
        """
        Group billing resources by normalized service type
        
        Maps Selectel billing types to our resource taxonomy:
        - cloud_vm -> server
        - volume_* -> volume
        - share_* -> file_storage
        - dbaas_* -> database
        - mks_* -> kubernetes
        - etc.
        """
        SERVICE_TYPE_MAPPING = {
            # Already normalized types (from billing API)
            'server': 'server',
            'volume': 'volume',
            'file_storage': 'file_storage',
            
            # Compute (raw Selectel types)
            'cloud_vm': 'server',
            'cloud_vm_gpu': 'server',
            
            # Storage (raw Selectel types)
            'volume_basic': 'volume',
            'volume_universal': 'volume', 
            'volume_fast': 'volume',
            'volume_ultra': 'volume',
            'share_basic': 'file_storage',
            'share_universal': 'file_storage',
            
            # Managed Databases
            'dbaas_postgresql': 'database',
            'dbaas_mysql': 'database',
            'dbaas_redis': 'database',
            'dbaas_kafka': 'message_queue',
            'dbaas_mongodb': 'database',
            
            # Kubernetes
            'mks_cluster': 'kubernetes_cluster',
            'mks_node_group': 'kubernetes_nodegroup',
            
            # Container Registry
            'craas_registry': 'container_registry',
            
            # Object Storage
            's3_storage': 's3_bucket',
            's3_traffic': 's3_bandwidth',
            
            # Network
            'network_floating_ip': 'floating_ip',
            'network_load_balancer': 'load_balancer',
            'network_traffic': 'network_bandwidth',
            
            # Backup
            'backup_storage': 'backup'
        }
        
        grouped = {}
        for resource_id, billing_data in billed_resources.items():
            obj_type = billing_data.get('type', 'unknown')
            normalized_type = SERVICE_TYPE_MAPPING.get(obj_type, 'other_service')
            
            if normalized_type not in grouped:
                grouped[normalized_type] = {}
            
            grouped[normalized_type][resource_id] = billing_data
        
        logger.info(f"Grouped into {len(grouped)} service types: {list(grouped.keys())}")
        return grouped
    
    def _process_vm_resource(self, resource_id: str, billing_data: Dict,
                            sync_snapshot_id: int) -> Optional[Resource]:
        """
        Process VM resource with billing data
        Try to enrich with OpenStack details, fallback to billing-only for zombies
        """
        try:
            # Try to get full details from OpenStack
            server_details = self._fetch_server_from_openstack(resource_id)
            
            if server_details:
                # Active VM - full details available
                # Extract CPU/RAM from flavor
                flavor = server_details.get('flavor', {})
                vcpus = flavor.get('vcpus')
                ram_mb = flavor.get('ram')  # OpenStack flavor uses 'ram', not 'ram_mb'
                
                # Calculate total disk from attached volumes
                attached_volumes = server_details.get('attached_volumes', [])
                total_storage_gb = sum(v.get('size_gb', 0) for v in attached_volumes)
                
                resource = self._create_resource(
                    resource_type='server',
                    resource_id=resource_id,
                    name=server_details.get('name', billing_data['name']),
                    metadata={
                        **server_details,
                        'billing': billing_data,
                        'vcpus': vcpus,
                        'ram_mb': ram_mb,
                        'total_storage_gb': total_storage_gb,
                        'ip_addresses': server_details.get('ip_addresses', []),
                        'attached_volumes': attached_volumes
                    },
                    sync_snapshot_id=sync_snapshot_id,
                    region=server_details.get('region', 'ru-3'),
                    service_name='Compute'
                )
                
                if resource:
                    # Set cost from billing
                    resource.daily_cost = billing_data['daily_cost_rubles']
                    resource.effective_cost = billing_data['daily_cost_rubles']
                    resource.original_cost = billing_data['monthly_cost_rubles']
                    resource.currency = 'RUB'
                    resource.add_tag('monthly_cost_rubles', str(billing_data['monthly_cost_rubles']))
                    resource.add_tag('cost_source', 'billing_api')
                
                return resource
            else:
                # Zombie VM - deleted but still billed
                logger.warning(f"Zombie VM: {resource_id} ({billing_data['name']}) - billed but not in OpenStack")
                
                resource = self._create_resource(
                    resource_type='server',
                    resource_id=resource_id,
                    name=billing_data['name'],
                    metadata={
                        'billing': billing_data,
                        'is_zombie': True,
                        'note': 'Deleted from OpenStack but still billed'
                    },
                    sync_snapshot_id=sync_snapshot_id,
                    region='unknown',
                    service_name='Compute'
                )
                
                if resource:
                    resource.status = 'DELETED_BILLED'
                    resource.daily_cost = billing_data['daily_cost_rubles']
                    resource.effective_cost = billing_data['daily_cost_rubles']
                    resource.original_cost = billing_data['monthly_cost_rubles']
                    resource.currency = 'RUB'
                    resource.add_tag('is_zombie', 'true')
                    resource.add_tag('recommendation', 'Contact support - billed for deleted resource')
                    resource.add_tag('cost_source', 'billing_api')
                
                return resource
                
        except Exception as e:
            logger.error(f"Error processing VM {resource_id}: {e}")
            return None
    
    def _process_volume_resource(self, resource_id: str, billing_data: Dict,
                                 unified_vms: Dict[str, Resource],
                                 sync_snapshot_id: int) -> Optional[Dict]:
        """
        Process volume - try to unify with VM or create standalone
        
        Philosophy:
        - If attached to VM: merge into VM metadata (NO separate DB resource)
        - If detached but name matches "disk-for-{VM-name}": still merge into VM
        - If standalone: create separate DB resource
        
        Returns:
            Dict with:
            - resource: Resource object (None if unified)
            - unified_into_vm: bool
            - is_orphan: bool
        """
        try:
            # Try to get volume details from OpenStack
            volume_details = self._fetch_volume_from_openstack(resource_id)
            
            if volume_details:
                # Volume exists in OpenStack
                attachments = volume_details.get('attachments', [])
                volume_name = volume_details.get('name', billing_data['name'])
                
                # Try to match by attachment
                if attachments and len(attachments) > 0:
                    server_id = attachments[0].get('server_id')
                    
                    if server_id in unified_vms:
                        # Merge volume into existing VM resource (NO separate DB resource)
                        vm_resource = unified_vms[server_id]
                        self._add_volume_to_vm(vm_resource, volume_details, billing_data)
                        
                        logger.debug(f"Volume {resource_id} unified into VM {server_id} via attachment")
                        
                        # Deactivate any existing standalone volume resource for this volume
                        from app.core.models.resource import Resource
                        existing_volume = Resource.query.filter_by(
                            provider_id=self.provider.id,
                            resource_id=resource_id,
                            resource_type='volume'
                        ).first()
                        
                        if existing_volume and existing_volume.is_active:
                            logger.info(f"Deactivating standalone volume resource {volume_name} (now unified with VM)")
                            existing_volume.is_active = False
                            db.session.add(existing_volume)
                        
                        # Return without creating a resource - volume is ONLY in VM metadata
                        return {
                            'unified_into_vm': True,
                            'vm_id': server_id,
                            'resource': None  # NO separate resource!
                        }
                
                # Try to match by naming convention: "disk-for-{VM-name}-#N"
                if volume_name.startswith('disk-for-'):
                    # Extract VM name from "disk-for-Doreen-#1" -> "Doreen"
                    try:
                        vm_name_part = volume_name.replace('disk-for-', '').split('-#')[0]
                        
                        # Find VM by name
                        for server_id, vm_resource in unified_vms.items():
                            if vm_resource.resource_name == vm_name_part:
                                # Found matching VM - unify even if detached (SHELVED case)
                                self._add_volume_to_vm(vm_resource, volume_details, billing_data)
                                
                                logger.info(f"Volume {volume_name} unified into VM {vm_name_part} via naming convention (VM status: {vm_resource.status})")
                                
                                # Deactivate any existing standalone volume resource for this volume
                                from app.core.models.resource import Resource
                                existing_volume = Resource.query.filter_by(
                                    provider_id=self.provider.id,
                                    resource_id=resource_id,
                                    resource_type='volume'
                                ).first()
                                
                                if existing_volume and existing_volume.is_active:
                                    logger.info(f"Deactivating standalone volume resource {volume_name} (now unified with VM)")
                                    existing_volume.is_active = False
                                    db.session.add(existing_volume)
                                
                                return {
                                    'unified_into_vm': True,
                                    'vm_id': server_id,
                                    'resource': None
                                }
                    except Exception as e:
                        logger.warning(f"Failed to parse volume name {volume_name}: {e}")
                
                # Standalone volume (not attached and no name match)
                is_orphan = self._is_volume_orphan(volume_details)
                
                logger.info(f"Creating standalone volume resource: {volume_details.get('name')} (orphan: {is_orphan})")
                
                resource = self._create_resource(
                    resource_type='volume',
                    resource_id=resource_id,
                    name=volume_details.get('name', billing_data['name']),
                    metadata={
                        **volume_details,
                        'billing': billing_data,
                        'size_gb': volume_details.get('size'),
                        'volume_type': volume_details.get('volume_type'),
                        'is_orphan': is_orphan
                    },
                    sync_snapshot_id=sync_snapshot_id,
                    region=volume_details.get('availability_zone', 'unknown'),
                    service_name='Block Storage'
                )
                
                if resource:
                    resource.daily_cost = billing_data['daily_cost_rubles']
                    resource.effective_cost = billing_data['daily_cost_rubles']
                    resource.original_cost = billing_data['monthly_cost_rubles']
                    resource.currency = 'RUB'
                    resource.add_tag('cost_source', 'billing_api')
                    
                    if is_orphan:
                        resource.add_tag('is_orphan', 'true')
                        resource.add_tag('recommendation', 'Unused volume - consider deletion')
                
                return {
                    'unified_into_vm': False,
                    'is_orphan': is_orphan,
                    'resource': resource
                }
            else:
                # Zombie volume - deleted but still billed
                logger.warning(f"Zombie volume: {resource_id} ({billing_data['name']})")
                
                resource = self._create_resource(
                    resource_type='volume',
                    resource_id=resource_id,
                    name=billing_data['name'],
                    metadata={
                        'billing': billing_data,
                        'is_zombie': True
                    },
                    sync_snapshot_id=sync_snapshot_id,
                    region='unknown',
                    service_name='Block Storage'
                )
                
                if resource:
                    resource.status = 'DELETED_BILLED'
                    resource.daily_cost = billing_data['daily_cost_rubles']
                    resource.effective_cost = billing_data['daily_cost_rubles']
                    resource.add_tag('is_zombie', 'true')
                    resource.add_tag('recommendation', 'Contact support - billed for deleted volume')
                
                return {
                    'unified_into_vm': False,
                    'is_orphan': False,
                    'resource': resource
                }
                
        except Exception as e:
            logger.error(f"Error processing volume {resource_id}: {e}")
            return None
    
    def _process_file_storage_resource(self, resource_id: str, billing_data: Dict,
                                       sync_snapshot_id: int) -> Optional[Resource]:
        """Process file storage (Manila shares)"""
        try:
            share_details = self._fetch_share_from_openstack(resource_id)
            
            if share_details:
                # Active file storage
                resource = self._create_resource(
                    resource_type='file_storage',
                    resource_id=resource_id,
                    name=share_details.get('name', billing_data['name']),
                    metadata={
                        **share_details,
                        'billing': billing_data,
                        'size_gb': share_details.get('size'),
                        'share_proto': share_details.get('share_proto')
                    },
                    sync_snapshot_id=sync_snapshot_id,
                    region=share_details.get('availability_zone', 'ru-3'),
                    service_name='File Storage'
                )
            else:
                # Zombie file storage
                resource = self._create_resource(
                    resource_type='file_storage',
                    resource_id=resource_id,
                    name=billing_data['name'],
                    metadata={'billing': billing_data, 'is_zombie': True},
                    sync_snapshot_id=sync_snapshot_id,
                    region='unknown',
                    service_name='File Storage'
                )
                if resource:
                    resource.status = 'DELETED_BILLED'
                    resource.add_tag('is_zombie', 'true')
            
            if resource:
                resource.daily_cost = billing_data['daily_cost_rubles']
                resource.effective_cost = billing_data['daily_cost_rubles']
                resource.add_tag('cost_source', 'billing_api')
            
            return resource
            
        except Exception as e:
            logger.error(f"Error processing file storage {resource_id}: {e}")
            return None
    
    def _process_generic_resource(self, resource_id: str, billing_data: Dict,
                                  service_type: str, sync_snapshot_id: int) -> Optional[Resource]:
        """
        Generic processor for any service type from billing
        Handles: K8s, DBaaS, S3, Load Balancers, etc.
        """
        try:
            resource = self._create_resource(
                resource_type=service_type,
                resource_id=resource_id,
                name=billing_data['name'],
                metadata={
                    'billing': billing_data,
                    'metrics': billing_data.get('metrics', {}),
                    'service_type': service_type
                },
                sync_snapshot_id=sync_snapshot_id,
                region='unknown',
                service_name=service_type.replace('_', ' ').title()
            )
            
            if resource:
                resource.daily_cost = billing_data['daily_cost_rubles']
                resource.effective_cost = billing_data['daily_cost_rubles']
                resource.original_cost = billing_data['monthly_cost_rubles']
                resource.currency = 'RUB'
                resource.add_tag('cost_source', 'billing_api')
                resource.add_tag('service_type', service_type)
                
                # Add all billing metrics as tags
                for metric_id, metric_value in billing_data.get('metrics', {}).items():
                    resource.add_tag(f'metric_{metric_id}', str(metric_value))
            
            return resource
            
        except Exception as e:
            logger.error(f"Error processing {service_type} {resource_id}: {e}")
            return None
    
    def _fetch_server_from_openstack(self, server_id: str) -> Optional[Dict]:
        """Fetch server details from OpenStack APIs across all regions"""
        try:
            # Try each region
            for region in self.client.regions.keys() if self.client.regions else ['ru-3']:
                try:
                    servers = self.client.get_openstack_servers(region=region)
                    for server in servers:
                        if server['id'] == server_id:
                            return server
                except Exception as e:
                    logger.debug(f"Server {server_id} not in region {region}")
                    continue
            return None
        except Exception as e:
            logger.error(f"Error fetching server {server_id}: {e}")
            return None
    
    def _fetch_volume_from_openstack(self, volume_id: str) -> Optional[Dict]:
        """Fetch volume details from OpenStack APIs"""
        try:
            projects = self.client.get_projects()
            project_id = projects[0]['id'] if projects else None
            
            if project_id:
                for region in self.client.regions.keys() if self.client.regions else ['ru-3']:
                    try:
                        volumes = self.client.get_openstack_volumes(project_id, region=region)
                        for volume in volumes:
                            if volume['id'] == volume_id:
                                return volume
                    except Exception:
                        continue
            return None
        except Exception as e:
            logger.error(f"Error fetching volume {volume_id}: {e}")
            return None
    
    def _fetch_share_from_openstack(self, share_id: str) -> Optional[Dict]:
        """Fetch file storage share details"""
        try:
            projects = self.client.get_projects()
            project_id = projects[0]['id'] if projects else None
            
            if project_id:
                for region in self.client.regions.keys() if self.client.regions else ['ru-3']:
                    try:
                        shares = self.client.get_openstack_shares(project_id, region=region)
                        for share in shares:
                            if share['id'] == share_id:
                                return share
                    except Exception:
                        continue
            return None
        except Exception as e:
            logger.error(f"Error fetching share {share_id}: {e}")
            return None
    
    def _add_volume_to_vm(self, vm_resource: Resource, volume_details: Dict, billing_data: Dict):
        """Add volume information to VM resource and update totals"""
        try:
            # Update VM metadata to include volume
            metadata = json.loads(vm_resource.provider_config) if vm_resource.provider_config else {}
            
            if 'attached_volumes' not in metadata:
                metadata['attached_volumes'] = []
            
            volume_info = {
                'id': volume_details['id'],
                'name': volume_details.get('name', ''),
                'size_gb': volume_details['size'],
                'type': volume_details.get('volume_type'),
                'daily_cost': billing_data['daily_cost_rubles']
            }
            
            metadata['attached_volumes'].append(volume_info)
            
            # Recalculate total storage (for UI display)
            total_storage_gb = sum(v.get('size_gb', 0) for v in metadata['attached_volumes'])
            metadata['total_storage_gb'] = total_storage_gb
            
            vm_resource.provider_config = json.dumps(metadata)
            
            # Update VM total cost
            vm_resource.daily_cost = (vm_resource.daily_cost or 0) + billing_data['daily_cost_rubles']
            vm_resource.effective_cost = vm_resource.daily_cost
            
            # Add volume cost as tag
            vm_resource.add_tag(f'volume_{volume_details["id"]}_cost', str(billing_data['daily_cost_rubles']))
            
        except Exception as e:
            logger.error(f"Error adding volume to VM: {e}")
    
    def _is_volume_orphan(self, volume_details: Dict) -> bool:
        """Check if volume is likely an orphan (old, unattached)"""
        try:
            # Volume is orphan if:
            # 1. Not attached
            # 2. Created more than 7 days ago
            
            if volume_details.get('attachments'):
                return False
            
            created_at = volume_details.get('created_at')
            if created_at:
                from dateutil import parser
                created_date = parser.parse(created_at)
                age_days = (datetime.now(created_date.tzinfo) - created_date).days
                return age_days > 7
            
            return False
        except Exception:
            return False
    
    def _sync_resources_fallback(self, sync_snapshot: SyncSnapshot) -> Dict[str, Any]:
        """
        Fallback sync method using OpenStack APIs directly
        Used when billing API is unavailable
        """
        logger.warning("Using fallback sync method (OpenStack APIs)")
        
        try:
            # This is the old method - just return basic success
            sync_snapshot.sync_status = 'success'
            sync_snapshot.sync_completed_at = datetime.now()
            sync_snapshot.error_message = 'Billing API unavailable - fallback not implemented'
            sync_snapshot.calculate_duration()
            db.session.commit()
            
            return {
                'success': False,
                'error': 'Billing API unavailable',
                'message': 'Cannot sync without billing data'
            }
        except Exception as e:
            logger.error(f"Fallback sync failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _create_resource(self, resource_type: str, resource_id: str, 
                        name: str, metadata: Dict[str, Any], 
                        sync_snapshot_id: int, region: str = None, 
                        service_name: str = None) -> Optional[Resource]:
        """
        Create or update a resource and create ResourceState entry
        
        Args:
            resource_type: Type of resource
            resource_id: Unique identifier for the resource
            name: Human-readable name
            metadata: Resource metadata
            sync_snapshot_id: ID of the sync snapshot
            region: Resource region (optional)
            service_name: Service name (optional)
            
        Returns:
            Resource instance or None if failed
        """
        from app.core.models.sync import ResourceState
        
        try:
            # Find any existing records for this provider/resource_id (regardless of type)
            existing_records = Resource.query.filter_by(
                provider_id=self.provider.id,
                resource_id=resource_id
            ).all()

            # Choose primary existing resource (prefer matching type)
            existing_resource = None
            for r in existing_records:
                if r.resource_type == resource_type:
                    existing_resource = r
                    break
            if not existing_resource and existing_records:
                existing_resource = existing_records[0]
            
            # Create unified resource data
            # Extract status from metadata (OpenStack uses ACTIVE/SHUTOFF, convert to uppercase)
            raw_status = metadata.get('status', 'active')
            # Normalize status: ACTIVE -> ACTIVE, SHUTOFF -> STOPPED, etc.
            if raw_status == 'ACTIVE':
                normalized_status = 'RUNNING'  # Match Beget convention
            elif raw_status in ['SHUTOFF', 'STOPPED']:
                normalized_status = 'STOPPED'
            elif raw_status in ['ERROR', 'FAILED']:
                normalized_status = 'ERROR'
            else:
                normalized_status = raw_status.upper() if isinstance(raw_status, str) else 'UNKNOWN'
            
            unified_resource = {
                'resource_id': resource_id,
                'resource_name': name,
                'resource_type': resource_type,
                'service_name': service_name or ('Account' if resource_type == 'account' else resource_type.title()),
                'region': region or ('global' if resource_type == 'account' else 'unknown'),
                'status': normalized_status,
                'effective_cost': 0.0,
                'provider_config': metadata
            }
            
            if existing_resource:
                # If there's a type mismatch (e.g., previously saved as 'volume' but now 'file_storage'),
                # reclassify the existing record and remove duplicates.
                if existing_resource.resource_type != resource_type:
                    existing_resource.resource_type = resource_type
                    if service_name:
                        existing_resource.service_name = service_name
                    # Remove any other duplicates with same resource_id but different id
                    for dup in existing_records:
                        if dup.id != existing_resource.id:
                            db.session.delete(dup)
                    db.session.flush()
                # Update existing resource
                previous_state = existing_resource.to_dict()
                
                # Check for changes
                has_changes = False
                changes = {}
                
                # Compare key fields
                key_fields = ['resource_name', 'status', 'effective_cost', 'region']
                for field in key_fields:
                    if getattr(existing_resource, field) != unified_resource.get(field):
                        has_changes = True
                        changes[field] = {
                            'previous': getattr(existing_resource, field),
                            'current': unified_resource.get(field)
                        }
                
                # Update resource if there are changes
                if has_changes:
                    existing_resource.resource_name = name
                    existing_resource.status = normalized_status  # Update status
                    existing_resource.provider_config = json.dumps(metadata)
                    existing_resource.last_sync = datetime.now()
                    existing_resource.is_active = True
                    if region:
                        existing_resource.region = region
                    if service_name:
                        existing_resource.service_name = service_name
                
                # Create resource state
                resource_state = ResourceState(
                    sync_snapshot_id=sync_snapshot_id,
                    resource_id=existing_resource.id,
                    provider_resource_id=resource_id,
                    resource_type=resource_type,
                    resource_name=name,
                    state_action='updated' if has_changes else 'unchanged',
                    service_name=unified_resource['service_name'],
                    region=unified_resource['region'],
                    status=unified_resource['status'],
                    effective_cost=unified_resource['effective_cost']
                )
                
                # Set previous and current states as JSON
                resource_state.set_previous_state(previous_state)
                resource_state.set_current_state(unified_resource)
                
                # Detect changes
                resource_state.detect_changes()
                
                db.session.add(resource_state)
                db.session.commit()
                return existing_resource
            else:
                # Create new resource
                new_resource = Resource(
                    provider_id=self.provider.id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    resource_name=name,
                    region=region or ('global' if resource_type == 'account' else 'unknown'),
                    service_name=service_name or ('Account' if resource_type == 'account' else resource_type.title()),
                    status=normalized_status,  # Set normalized status
                    provider_config=json.dumps(metadata),
                    last_sync=datetime.now(),
                    is_active=True
                )
                db.session.add(new_resource)
                db.session.flush()  # Get the ID
                
                # Create resource state
                resource_state = ResourceState(
                    sync_snapshot_id=sync_snapshot_id,
                    resource_id=new_resource.id,
                    provider_resource_id=resource_id,
                    resource_type=resource_type,
                    resource_name=name,
                    state_action='created',
                    service_name=unified_resource['service_name'],
                    region=unified_resource['region'],
                    status=unified_resource['status'],
                    effective_cost=unified_resource['effective_cost']
                )
                
                # Set current state as JSON
                resource_state.set_current_state(unified_resource)
                
                db.session.add(resource_state)
                db.session.commit()
                return new_resource
                
        except Exception as e:
            logger.error(f"Failed to create/update resource {resource_type}/{resource_id}: {str(e)}")
            return None
    
    def get_resource_summary(self) -> Dict[str, Any]:
        """
        Get summary of resources for this provider
        
        Returns:
            Dict containing resource summary
        """
        try:
            resources = Resource.query.filter_by(
                provider_id=self.provider.id,
                is_active=True
            ).all()
            
            summary = {
                'total_resources': len(resources),
                'by_type': {},
                'last_sync': None
            }
            
            for resource in resources:
                resource_type = resource.resource_type
                if resource_type not in summary['by_type']:
                    summary['by_type'][resource_type] = 0
                summary['by_type'][resource_type] += 1
                
                if not summary['last_sync'] or resource.last_sync > summary['last_sync']:
                    summary['last_sync'] = resource.last_sync
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get resource summary: {str(e)}")
            return {
                'total_resources': 0,
                'by_type': {},
                'last_sync': None,
                'error': str(e)
            }
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """
        Get list of projects
        
        Returns:
            List of project dictionaries
        """
        try:
            return self.client.get_projects()
        except Exception as e:
            logger.error(f"Failed to get projects: {str(e)}")
            return []
    
    def _process_server_statistics(self, sync_snapshot, statistics: Dict[str, Any]):
        """
        Process and store server statistics (similar to Beget implementation)
        
        Args:
            sync_snapshot: SyncSnapshot instance
            statistics: Dict mapping server_id to CPU/memory statistics
        """
        from app.core.models.resource import Resource
        
        for server_id, stats in statistics.items():
            try:
                # Find the server resource
                server_resource = Resource.query.filter_by(
                    provider_id=self.provider.id,
                    resource_id=server_id,
                    resource_type='server'
                ).first()
                
                if not server_resource:
                    logger.warning(f"Server resource not found for ID {server_id}")
                    continue
                
                # Add CPU statistics tags (same format as Beget)
                if stats.get('cpu_statistics'):
                    cpu_stats = stats['cpu_statistics']
                    server_resource.add_tag('cpu_avg_usage', str(cpu_stats.get('avg_cpu_usage', 0)))
                    server_resource.add_tag('cpu_max_usage', str(cpu_stats.get('max_cpu_usage', 0)))
                    server_resource.add_tag('cpu_min_usage', str(cpu_stats.get('min_cpu_usage', 0)))
                    server_resource.add_tag('cpu_trend', str(cpu_stats.get('trend', 0)))
                    server_resource.add_tag('cpu_performance_tier', cpu_stats.get('performance_tier', 'unknown'))
                    server_resource.add_tag('cpu_data_points', str(cpu_stats.get('data_points', 0)))
                    server_resource.add_tag('cpu_period', cpu_stats.get('period', 'HOUR'))
                    server_resource.add_tag('cpu_collection_timestamp', cpu_stats.get('collection_timestamp', ''))
                
                # Add memory statistics tags (same format as Beget)
                if stats.get('memory_statistics'):
                    mem_stats = stats['memory_statistics']
                    server_resource.add_tag('memory_avg_usage_mb', str(mem_stats.get('avg_memory_usage_mb', 0)))
                    server_resource.add_tag('memory_max_usage_mb', str(mem_stats.get('max_memory_usage_mb', 0)))
                    server_resource.add_tag('memory_min_usage_mb', str(mem_stats.get('min_memory_usage_mb', 0)))
                    server_resource.add_tag('memory_usage_percent', str(mem_stats.get('memory_usage_percent', 0)))
                    server_resource.add_tag('memory_trend', str(mem_stats.get('trend', 0)))
                    server_resource.add_tag('memory_tier', mem_stats.get('memory_tier', 'unknown'))
                    server_resource.add_tag('memory_data_points', str(mem_stats.get('data_points', 0)))
                    server_resource.add_tag('memory_period', mem_stats.get('period', 'HOUR'))
                    server_resource.add_tag('memory_collection_timestamp', mem_stats.get('collection_timestamp', ''))
                
                logger.debug(f"Processed statistics for server: {stats.get('server_name')}")
                
            except Exception as e:
                logger.error(f"Error processing statistics for server {server_id}: {e}")
    
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information
        
        Returns:
            Dict containing account information
        """
        try:
            return self.client.get_account_info()
        except Exception as e:
            logger.error(f"Failed to get account info: {str(e)}")
            return {}
