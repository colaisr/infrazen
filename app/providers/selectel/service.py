"""
Selectel provider service implementation
"""
from typing import Dict, List, Any, Optional
from app.providers.selectel.client import SelectelClient
from app.core.models.provider import CloudProvider
from app.core.models.resource import Resource
from app.core.models.sync import SyncSnapshot
from app.core.models.unrecognized_resource import UnrecognizedResource
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
        
        # Add account_id to credentials for OpenStack authentication
        credentials_with_account = self.credentials.copy()
        credentials_with_account['account_id'] = provider.account_id
        
        self.client = SelectelClient(credentials_with_account)
    
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
            
            # PHASE 0: Validate OpenStack authentication (critical for VM/volume details)
            logger.info("PHASE 0: Validating OpenStack authentication")
            openstack_auth_ok = False
            try:
                iam_token = self.client._get_iam_token()
                if iam_token:
                    openstack_auth_ok = True
                    logger.info("✅ OpenStack authentication successful")
            except Exception as auth_error:
                logger.error(f"❌ OpenStack authentication FAILED: {auth_error}")
                logger.warning("⚠️  Sync will continue with billing data only - VMs will lack CPU/RAM/IP details")
                logger.warning("⚠️  Fix: Check service user credentials and permissions in Selectel admin panel")
            
            # PHASE 1: Get all billed resources (2h window for current active resources only)
            logger.info("PHASE 1: Fetching billing data (2h window - current active resources only)")
            billed_resources = self.client.get_resource_costs(hours=2)
            
            # Cache provision dates for all resources (single API call)
            logger.info("Caching provision dates for all resources")
            self._provision_dates_cache = self._fetch_all_provision_dates()
            
            if not billed_resources:
                logger.warning("No billed resources found - deactivating all existing resources")
                # Deactivate all existing resources since nothing is currently consuming
                from app.core.models.resource import Resource
                existing_resources = Resource.query.filter_by(
                    provider_id=self.provider.id,
                    is_active=True
                ).all()
                
                deactivated_count = 0
                for resource in existing_resources:
                    resource.is_active = False
                    resource.add_tag('deactivation_reason', 'no_current_billing')
                    resource.add_tag('deactivated_at', datetime.now().isoformat())
                    db.session.add(resource)
                    deactivated_count += 1
                
                db.session.commit()
                
                # Update sync snapshot
                sync_snapshot.sync_status = 'success'
                sync_snapshot.sync_completed_at = datetime.now()
                sync_snapshot.sync_duration_seconds = int((sync_snapshot.sync_completed_at - sync_snapshot.sync_started_at).total_seconds())
                sync_snapshot.total_resources_found = 0
                sync_snapshot.resources_deleted = deactivated_count
                sync_snapshot.total_monthly_cost = 0.0
                
                sync_config = {
                    'sync_method': 'billing_first',
                    'cost_calculation': 'latest_hour_selectel_ui_match',
                    'deactivation_reason': 'no_current_billing',
                    'deactivated_resources': deactivated_count,
                    'billing_window_hours': 24
                }
                sync_snapshot.sync_config = json.dumps(sync_config)
                
                db.session.add(sync_snapshot)
                db.session.commit()
                
                logger.info(f"Deactivated {deactivated_count} resources - no current billing")
                
                return {
                    'success': True,
                    'resources_synced': 0,
                    'resources_deactivated': deactivated_count,
                    'total_daily_cost': 0.0,
                    'message': f'No current resources consuming - deactivated {deactivated_count} existing resources'
                }
            
            logger.info(f"Found {len(billed_resources)} billed resources")
            
            # PHASE 2: Group by service type
            logger.info("PHASE 2: Grouping resources by service type")
            resources_by_type = self._group_by_service_type(billed_resources, sync_snapshot.id)
            
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
            
            # PHASE 3.5: Extract orphaned volumes from deleted VMs (volumes with no parent VM in OpenStack)
            logger.info("PHASE 3.5: Extracting orphaned volumes from deleted VMs")
            orphaned_volumes_from_deleted_vms = {}
            
            if 'server' in resources_by_type:
                for resource_id, billing_data in resources_by_type['server'].items():
                    # Check if this VM exists in unified_vms (was found in OpenStack)
                    if resource_id not in unified_vms:
                        # VM not in OpenStack - check for attached volumes
                        attached_volumes = billing_data.get('attached_volumes', [])
                        if attached_volumes:
                            logger.info(f"Found {len(attached_volumes)} orphaned volumes from deleted VM {billing_data['name']}")
                            for vol_info in attached_volumes:
                                vol_id = vol_info.get('id')
                                # Create a billing data entry for this volume
                                orphaned_volumes_from_deleted_vms[vol_id] = {
                                    'name': vol_info.get('name', f'Volume {vol_id[:20]}...'),
                                    'type': 'volume',
                                    'service_type': 'volume',
                                    'region': billing_data.get('region', 'unknown'),
                                    'project_id': billing_data.get('project_id'),
                                    'project_name': billing_data.get('project_name'),
                                    'size_gb': vol_info.get('size_gb', 0),
                                    # Pro-rate the cost based on volume size contribution
                                    # For now, assign the full deleted VM cost to the volumes
                                    'daily_cost_rubles': billing_data['daily_cost_rubles'] / len(attached_volumes) if len(attached_volumes) > 0 else 0,
                                    'monthly_cost_rubles': billing_data['monthly_cost_rubles'] / len(attached_volumes) if len(attached_volumes) > 0 else 0,
                                    'hourly_cost_rubles': billing_data.get('hourly_cost_rubles', 0) / len(attached_volumes) if len(attached_volumes) > 0 else 0,
                                    'hourly_cost_kopecks': billing_data.get('hourly_cost_kopecks', 0) / len(attached_volumes) if len(attached_volumes) > 0 else 0,
                                    'is_orphan': True,
                                    'parent_vm_name': billing_data['name'],
                                    'parent_vm_id': resource_id
                                }
            
            logger.info(f"Extracted {len(orphaned_volumes_from_deleted_vms)} orphaned volumes from deleted VMs")
            
            # Add orphaned volumes to the volume list for processing
            if 'volume' not in resources_by_type:
                resources_by_type['volume'] = {}
            resources_by_type['volume'].update(orphaned_volumes_from_deleted_vms)
            
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
            
            # PHASE 7: Get statistics for active servers (OPTIONAL - controlled by provider settings)
            # Performance stats collection makes 2 API calls per server (CPU + Memory)
            # Can be enabled via provider_metadata['collect_performance_stats'] = True
            provider_metadata = json.loads(self.provider.provider_metadata) if self.provider.provider_metadata else {}
            collect_stats = provider_metadata.get('collect_performance_stats', False)
            
            logger.info(f"PHASE 7: Performance statistics {'ENABLED' if collect_stats else 'DISABLED (set in provider settings)'}")
            active_servers = [vm for vm in unified_vms.values() if vm.status != 'DELETED_BILLED']
            if active_servers and collect_stats:
                try:
                    server_data_list = []
                    for vm in active_servers:
                        metadata = json.loads(vm.provider_config) if vm.provider_config else {}
                        billing_data = metadata.get('billing', {})
                        
                        server_data_list.append({
                            'id': vm.resource_id,
                            'name': vm.resource_name,
                            'ram_mb': metadata.get('ram_mb', 1024),
                            'region': vm.region,  # Pass VM's actual region for stats API
                            'project_id': billing_data.get('project_id')  # CRITICAL: Pass project ID for token scoping
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
                'openstack_auth_ok': openstack_auth_ok,
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
            
            # Update provider - set status based on OpenStack auth
            self.provider.last_sync = datetime.now()
            
            if not openstack_auth_ok:
                # OpenStack auth failed - sync succeeded but with degraded data
                self.provider.sync_status = 'success'  # Still success (billing worked)
                self.provider.sync_error = 'OpenStack authentication failed - VMs have limited details. Check service user credentials.'
                logger.warning("⚠️  Sync completed with WARNINGS - OpenStack enrichment unavailable")
            else:
                # Full success
                self.provider.sync_status = 'success'
                self.provider.sync_error = None
            
            db.session.commit()
            
            logger.info(f"Sync completed: {len(synced_resources)} resources, {total_cost:.2f} ₽/day")
            logger.info(f"  - Active: {len(synced_resources) - len(zombie_resources)}")
            logger.info(f"  - Zombies: {len(zombie_resources)} ({zombie_cost:.2f} ₽/day)")
            logger.info(f"  - Orphan volumes: {len(orphan_volumes)} ({orphan_cost:.2f} ₽/day)")
            
            if not openstack_auth_ok:
                logger.error("❌ CRITICAL: OpenStack authentication failed - VMs are missing CPU/RAM/IP details")
                logger.error("❌ ACTION REQUIRED: Update service user credentials in connection settings")
            
            # Build success message with prominent warning if OpenStack auth failed
            base_message = f'Successfully synced {len(synced_resources)} resources ({total_cost:.2f} ₽/day)'
            if not openstack_auth_ok:
                base_message = f'⚠️ PARTIAL SYNC: {len(synced_resources)} resources found but OpenStack auth FAILED - VMs lack CPU/RAM/IP details. Update service user credentials!'
            
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
                'openstack_auth_ok': openstack_auth_ok,
                'message': base_message
            }
            
        except Exception as e:
            logger.error(f"Selectel billing-first sync failed: {str(e)}", exc_info=True)
            
            # Update sync snapshot with error
            snapshot_id = None
            if 'sync_snapshot' in locals():
                sync_snapshot.sync_status = 'error'
                sync_snapshot.sync_completed_at = datetime.now()
                sync_snapshot.error_message = str(e)
                sync_snapshot.calculate_duration()
                snapshot_id = sync_snapshot.id
                
                # Update provider sync status to error
                self.provider.sync_status = 'error'
                self.provider.sync_error = str(e)
                
                db.session.commit()
            
            return {
                'success': False,
                'error': str(e),
                'message': 'Sync failed',
                'sync_snapshot_id': snapshot_id  # Include snapshot ID even on error
            }
    
    def _group_by_service_type(self, billed_resources: Dict[str, Any], sync_snapshot_id: int = None) -> Dict[str, Dict]:
        """
        Group billing resources by normalized service type
        
        Maps Selectel billing types to our resource taxonomy:
        - cloud_vm -> server
        - volume_* -> volume
        - share_* -> file_storage
        - dbaas_* -> database
        - mks_* -> kubernetes
        - etc.
        
        Also tracks unrecognized resource types for platform improvement.
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
        unrecognized_count = 0
        
        for resource_id, billing_data in billed_resources.items():
            obj_type = billing_data.get('type', 'unknown')
            
            # If type is unknown, try to infer from metrics
            if obj_type == 'unknown':
                inferred_type = self._infer_resource_type_from_metrics(billing_data)
                if inferred_type:
                    obj_type = inferred_type
                    # Update the billing data with inferred type
                    billing_data['type'] = obj_type
            
            normalized_type = SERVICE_TYPE_MAPPING.get(obj_type, 'other_service')
            
            # Track unrecognized resource types for platform improvement
            # Track ALL resources that fall into 'other_service' category (not in our mapping)
            # This helps identify gaps in provider coverage for future development
            if normalized_type == 'other_service':
                self._track_unrecognized_resource(
                    resource_id=resource_id,
                    billing_data=billing_data,
                    sync_snapshot_id=sync_snapshot_id
                )
                unrecognized_count += 1
            
            if normalized_type not in grouped:
                grouped[normalized_type] = {}
            
            grouped[normalized_type][resource_id] = billing_data
        
        if unrecognized_count > 0:
            logger.info(f"Found {unrecognized_count} unrecognized resource types - tracked for platform improvement")
        
        logger.info(f"Grouped into {len(grouped)} service types: {list(grouped.keys())}")
        return grouped
    
    def _infer_resource_type_from_metrics(self, billing_data: Dict) -> Optional[str]:
        """
        Infer resource type from billing metrics when type is unknown.
        This helps identify resource types that Selectel billing API doesn't properly categorize.
        """
        metrics = billing_data.get('metrics', {})
        
        # Load Balancer detection
        if any(key.startswith('load_balancers_') for key in metrics.keys()):
            return 'network_load_balancer'
        
        # Volume detection  
        if any(key.startswith('volume_') for key in metrics.keys()):
            return 'volume_universal'  # Default to universal volume
        
        # File Storage detection
        if any(key.startswith('share_') for key in metrics.keys()):
            return 'share_basic'  # Default to basic share
        
        # Database detection
        if any(key.startswith('dbaas_') for key in metrics.keys()):
            return 'dbaas_postgresql'  # Default to PostgreSQL
        
        # Kubernetes detection
        if any(key.startswith('mks_') for key in metrics.keys()):
            return 'mks_cluster'
        
        # Container Registry detection
        if any(key.startswith('craas_') for key in metrics.keys()):
            return 'craas_registry'
        
        # S3 detection
        if any(key.startswith('s3_') for key in metrics.keys()):
            return 's3_storage'
        
        # Network detection
        if any(key.startswith('network_') for key in metrics.keys()):
            return 'network_floating_ip'  # Default to floating IP
        
        # Backup detection
        if any(key.startswith('backup_') for key in metrics.keys()):
            return 'backup_storage'
        
        # If no metrics match, return None (will stay as other_service)
        return None
    
    def _track_unrecognized_resource(self, resource_id: str, billing_data: Dict, sync_snapshot_id: int = None):
        """
        Track unrecognized resource types for platform improvement
        
        Args:
            resource_id: Resource ID from billing data
            billing_data: Raw billing data for the resource
            sync_snapshot_id: ID of the current sync snapshot
        """
        try:
            # Create new unrecognized resource record for every occurrence
            # This allows tracking the full history across multiple syncs
            unrecognized = UnrecognizedResource(
                provider_id=self.provider.id,
                resource_id=resource_id,
                resource_name=billing_data.get('name', 'Unknown'),
                resource_type=billing_data.get('type', 'unknown'),
                service_type=billing_data.get('service_type', 'unknown'),
                billing_data=json.dumps(billing_data, ensure_ascii=False),
                user_id=self.provider.user_id,
                sync_snapshot_id=sync_snapshot_id,
                discovered_at=datetime.utcnow()
            )
            
            db.session.add(unrecognized)
            db.session.commit()
            
            logger.info(f"Tracked unrecognized resource: {resource_id} ({billing_data.get('type', 'unknown')})")
            
        except Exception as e:
            logger.error(f"Failed to track unrecognized resource {resource_id}: {e}")
            db.session.rollback()
    
    def _process_vm_resource(self, resource_id: str, billing_data: Dict,
                            sync_snapshot_id: int) -> Optional[Resource]:
        """
        Process VM resource with billing data
        Try to enrich with OpenStack details, fallback to billing-only for zombies
        """
        try:
            # Extract project and region from billing data to avoid brute-force search
            billing_project_id = billing_data.get('project_id')
            billing_region_raw = billing_data.get('region')
            
            # Convert billing availability zone (ru-7b) to OpenStack region (ru-7)
            # Billing uses zones like "ru-7b", "ru-8a", OpenStack uses "ru-7", "ru-8"
            # Pattern: ru-{number}{letter} -> ru-{number}
            # Only remove last char if it's a letter AND preceded by a digit
            billing_region = billing_region_raw
            if billing_region_raw and len(billing_region_raw) > 2:
                if billing_region_raw[-1].isalpha() and billing_region_raw[-2].isdigit():
                    billing_region = billing_region_raw[:-1]
            
            # Try to get full details from OpenStack (using billing location hint)
            server_details = self._fetch_server_from_openstack(
                resource_id, 
                billing_project_id=billing_project_id,
                billing_region=billing_region
            )
            
            if server_details:
                # Active VM - full details available
                # Extract CPU/RAM from flavor
                flavor = server_details.get('flavor', {})
                vcpus = flavor.get('vcpus')
                ram_mb = flavor.get('ram')  # OpenStack flavor uses 'ram', not 'ram_mb'
                
                # Calculate total disk from attached volumes
                attached_volumes = server_details.get('attached_volumes', [])
                total_storage_gb = sum(v.get('size_gb', 0) for v in attached_volumes)
                
                # Extract provision date from billing data
                created_at = self._extract_provision_date_from_billing(resource_id)
                
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
                        'attached_volumes': attached_volumes,
                        'created_at': created_at
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
                # VM not found in OpenStack - BILLING-FIRST: Create resource from billing data
                # This could mean:
                # 1. OpenStack authentication/permissions issue (our bug, not user's)
                # 2. VM is truly deleted but still being billed (user's issue)
                # 
                # We MUST create the resource either way (billing = source of truth)
                logger.warning(f"VM {resource_id} ({billing_data['name']}) found in billing but not in OpenStack - creating with limited info")
                
                # Extract provision date from billing data
                created_at = self._extract_provision_date_from_billing(resource_id)
                
                # Use billing region if available
                region = billing_data.get('region', 'unknown')
                
                resource = self._create_resource(
                    resource_type='server',
                    resource_id=resource_id,
                    name=billing_data['name'],
                    metadata={
                        'billing': billing_data,
                        'openstack_enrichment_failed': True,
                        'note': 'Created from billing data only - OpenStack details unavailable',
                        'created_at': created_at,
                        # Try to extract any available info from billing metrics
                        'metrics': billing_data.get('metrics', {})
                    },
                    sync_snapshot_id=sync_snapshot_id,
                    region=region,
                    service_name='Compute'
                )
                
                if resource:
                    # Resource is RUNNING (has costs in billing) but missing details
                    resource.status = 'RUNNING'  # Active if being billed
                    resource.daily_cost = billing_data['daily_cost_rubles']
                    resource.effective_cost = billing_data['daily_cost_rubles']
                    resource.original_cost = billing_data['monthly_cost_rubles']
                    resource.currency = 'RUB'
                    resource.add_tag('openstack_enrichment_failed', 'true')
                    resource.add_tag('cost_source', 'billing_api')
                    resource.add_tag('warning', 'Missing CPU/RAM/IP details - check service user permissions')
                
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
            # Extract project and region from billing data to optimize OpenStack search
            billing_project_id = billing_data.get('project_id')
            billing_region_raw = billing_data.get('region')
            
            # Convert billing availability zone (ru-7b) to OpenStack region (ru-7)
            billing_region = billing_region_raw
            if billing_region_raw and len(billing_region_raw) > 2:
                if billing_region_raw[-1].isalpha() and billing_region_raw[-2].isdigit():
                    billing_region = billing_region_raw[:-1]
            
            # Try to get volume details from OpenStack (using billing location hint)
            volume_details = self._fetch_volume_from_openstack(
                resource_id,
                billing_project_id=billing_project_id,
                billing_region=billing_region
            )
            
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
                
                # Extract provision date from billing data
                created_at = self._extract_provision_date_from_billing(resource_id)
                
                resource = self._create_resource(
                    resource_type='volume',
                    resource_id=resource_id,
                    name=volume_details.get('name', billing_data['name']),
                    metadata={
                        **volume_details,
                        'billing': billing_data,
                        'size_gb': volume_details.get('size'),
                        'volume_type': volume_details.get('volume_type'),
                        'is_orphan': is_orphan,
                        'created_at': created_at
                    },
                    sync_snapshot_id=sync_snapshot_id,
                    region=volume_details.get('region', volume_details.get('availability_zone', 'unknown')),
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
                # Volume not found in OpenStack (could be deleted or OpenStack API issue)
                # Mark as STOPPED instead of DELETED_BILLED since we can't definitively say it's deleted
                logger.warning(f"Volume not enriched from OpenStack: {resource_id} ({billing_data['name']})")
                
                # Extract volume size and creation timestamp from billing data if available
                # For volumes, the size is typically in the metrics under volume_gigabytes_universal
                volume_size_gb = None
                created_at = None
                if 'metrics' in billing_data:
                    # Look for volume size in metrics
                    for metric_id, metric_value in billing_data['metrics'].items():
                        if 'volume_gigabytes' in metric_id:
                            # For zombie volumes, we need to make a direct billing API call to get the size
                            # since the processed billing data doesn't include the raw metric.quantity
                            size_and_timestamp = self._get_volume_details_from_billing_api(resource_id)
                            if size_and_timestamp:
                                volume_size_gb = size_and_timestamp.get('size_gb')
                                created_at = size_and_timestamp.get('created_at')
                            else:
                                # Fallback to just getting the provision date
                                created_at = self._extract_provision_date_from_billing(resource_id)
                            break
                
                # Extract region from billing data
                volume_region = billing_data.get('region', 'unknown')
                # Convert billing zone to region (ru-3b -> ru-3)
                if volume_region and len(volume_region) > 2:
                    if volume_region[-1].isalpha() and volume_region[-2].isdigit():
                        volume_region = volume_region[:-1]
                
                resource = self._create_resource(
                    resource_type='volume',
                    resource_id=resource_id,
                    name=billing_data['name'],
                    metadata={
                        'billing': billing_data,
                        'size_gb': volume_size_gb,
                        'created_at': created_at,
                        'project_id': billing_data.get('project_id'),
                        'project_name': billing_data.get('project_name')
                    },
                    sync_snapshot_id=sync_snapshot_id,
                    region=volume_region,
                    service_name='Block Storage'
                )
                
                if resource:
                    # Volume is being billed, so it's active (just detached from any VM)
                    resource.status = 'RUNNING'  # Active detached volume
                    resource.daily_cost = billing_data['daily_cost_rubles']
                    resource.effective_cost = billing_data['daily_cost_rubles']
                    resource.original_cost = billing_data['monthly_cost_rubles']
                    resource.currency = 'RUB'
                    resource.add_tag('cost_source', 'billing_api')
                    resource.add_tag('note', 'Detached volume (not attached to any VM)')
                
                return {
                    'unified_into_vm': False,
                    'is_orphan': False,
                    'resource': resource
                }
                
        except Exception as e:
            logger.error(f"Error processing volume {resource_id}: {e}")
            return None
    
    def _get_volume_details_from_billing_api(self, volume_id: str) -> Optional[Dict[str, Any]]:
        """
        Get volume size and creation timestamp from billing API by making a direct call
        
        Args:
            volume_id: Volume ID to get details for
            
        Returns:
            Dict with 'size_gb' and 'created_at' or None if not found
        """
        try:
            from datetime import datetime, timedelta
            import requests
            
            # Get recent billing data
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            start_str = start_time.strftime('%Y-%m-%dT%H:00:00')
            end_str = end_time.strftime('%Y-%m-%dT%H:59:59')
            
            billing_url = 'https://api.selectel.ru/v1/cloud_billing/statistic/consumption'
            params = {
                'provider_keys': ['vpc', 'mks', 'dbaas', 'craas'],
                'start': start_str,
                'end': end_str,
                'locale': 'ru',
                'group_type': 'project_object_region_metric',
                'period_group_type': 'hour'
            }
            
            headers = {
                'X-Token': self.client.api_key,
                'Accept': 'application/json'
            }
            
            # Increase timeout to tolerate slower billing API in production
            response = requests.get(billing_url, params=params, headers=headers, timeout=90)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    # Look for the volume in billing data
                    for item in data.get('data', []):
                        if item.get('object', {}).get('id') == volume_id:
                            # Check if this is a volume metric
                            metric = item.get('metric', {})
                            if 'quantity' in metric and 'volume_gigabytes' in metric.get('id', ''):
                                size_gb = metric.get('quantity', 0)
                                created_at = item.get('provision_start')
                                
                                logger.info(f"Found volume details for {volume_id}: {size_gb} GB, created: {created_at}")
                                
                                return {
                                    'size_gb': size_gb,
                                    'created_at': created_at
                                }
            
            logger.warning(f"Could not find volume details for {volume_id} in billing API")
            return None
            
        except Exception as e:
            logger.error(f"Error getting volume details for {volume_id}: {e}")
            return None
    
    def _fetch_all_provision_dates(self) -> Dict[str, str]:
        """
        Fetch provision dates for all resources in a single API call
        
        Returns:
            Dict mapping resource_id to provision_start date
        """
        try:
            from datetime import datetime, timedelta
            import requests
            
            # Get recent billing data
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            start_str = start_time.strftime('%Y-%m-%dT%H:00:00')
            end_str = end_time.strftime('%Y-%m-%dT%H:59:59')
            
            billing_url = 'https://api.selectel.ru/v1/cloud_billing/statistic/consumption'
            params = {
                'provider_keys': ['vpc', 'mks', 'dbaas', 'craas'],
                'start': start_str,
                'end': end_str,
                'locale': 'ru',
                'group_type': 'project_object_region_metric',
                'period_group_type': 'hour'
            }
            
            headers = {
                'X-Token': self.client.api_key,
                'Accept': 'application/json'
            }
            
            # Increase timeout to tolerate slower billing API in production
            response = requests.get(billing_url, params=params, headers=headers, timeout=90)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    # Build cache of provision dates
                    provision_dates = {}
                    for item in data.get('data', []):
                        obj_id = item.get('object', {}).get('id')
                        provision_start = item.get('provision_start')
                        if obj_id and provision_start and obj_id not in provision_dates:
                            provision_dates[obj_id] = provision_start
                    
                    logger.info(f"Cached provision dates for {len(provision_dates)} resources")
                    return provision_dates
            
            logger.warning("Could not fetch provision dates from billing API")
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching provision dates: {e}")
            return {}
    
    def _extract_provision_date_from_billing(self, resource_id: str) -> Optional[str]:
        """
        Extract provision_start date from cached billing data
        
        Args:
            resource_id: Resource ID to get provision date for
            
        Returns:
            Provision start date string or None if not found
        """
        try:
            # Use cached provision dates if available
            if hasattr(self, '_provision_dates_cache') and self._provision_dates_cache:
                provision_date = self._provision_dates_cache.get(resource_id)
                if provision_date:
                    logger.debug(f"Found cached provision date for {resource_id}: {provision_date}")
                    return provision_date
                else:
                    logger.debug(f"No provision date found in cache for {resource_id}")
                    return None
            else:
                logger.warning(f"Provision dates cache not available, skipping for {resource_id}")
                return None
            
        except Exception as e:
            logger.error(f"Error getting provision date for {resource_id}: {e}")
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
    
    def _fetch_server_from_openstack(self, server_id: str, billing_project_id: str = None, billing_region: str = None) -> Optional[Dict]:
        """
        Fetch server details from OpenStack APIs
        
        Uses project_id and region from billing API if available to avoid brute-force search
        Falls back to multi-project/region search if billing info not provided
        """
        try:
            # OPTIMIZATION: If we have project/region from billing, try that first
            if billing_project_id and billing_region:
                logger.debug(f"Trying server {server_id} in billing-provided project {billing_project_id} region {billing_region}")
                try:
                    servers = self.client.get_openstack_servers(region=billing_region, project_id=billing_project_id)
                    for server in servers:
                        if server['id'] == server_id:
                            logger.info(f"✅ Found server {server_id} using billing-provided location")
                            server['project_id'] = billing_project_id
                            # Get project name from billing
                            projects = self.client.get_all_projects_from_billing()
                            for p in projects:
                                if p.get('id') == billing_project_id:
                                    server['project_name'] = p.get('name')
                                    break
                            return server
                except Exception as e:
                    logger.warning(f"Server {server_id} not found at billing location: {e}")
            
            # FALLBACK: Brute-force search across all projects/regions
            logger.debug(f"Falling back to brute-force search for server {server_id}")
            
            # Discover all projects from billing
            projects = self.client.get_all_projects_from_billing()
            if not projects:
                logger.warning("No projects discovered from billing, using default")
                projects = [{'id': None, 'name': 'default'}]
            
            # Get available regions
            regions = self.client.get_available_regions()
            logger.debug(f"Searching across {len(projects)} projects and {len(regions)} regions")
            
            # Try each project/region combination
            for project in projects:
                project_id = project.get('id')
                project_name = project.get('name', 'Unknown')
                
                for region in regions:
                    try:
                        servers = self.client.get_openstack_servers(region=region, project_id=project_id)
                        for server in servers:
                            if server['id'] == server_id:
                                logger.info(f"Found server {server_id} in project '{project_name}' region {region}")
                                server['project_id'] = project_id
                                server['project_name'] = project_name
                                return server
                    except Exception as e:
                        logger.debug(f"Server {server_id} not in project '{project_name}' region {region}: {e}")
                        continue
            
            logger.warning(f"Server {server_id} not found in any project/region combination")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching server {server_id}: {e}")
            return None
    
    def _fetch_volume_from_openstack(self, volume_id: str, billing_project_id: str = None, billing_region: str = None) -> Optional[Dict]:
        """
        Fetch volume details from OpenStack APIs
        
        Uses project_id and region from billing API if available to avoid brute-force search
        Falls back to multi-project/region search if billing info not provided
        """
        try:
            # OPTIMIZATION: If we have project/region from billing, try that first
            if billing_project_id and billing_region:
                logger.debug(f"Trying volume {volume_id} in billing-provided project {billing_project_id} region {billing_region}")
                try:
                    volumes = self.client.get_openstack_volumes(billing_project_id, region=billing_region)
                    for volume in volumes:
                        if volume['id'] == volume_id:
                            logger.info(f"✅ Found volume {volume_id} using billing-provided location")
                            return volume
                except Exception as e:
                    logger.warning(f"Volume {volume_id} not found at billing location: {e}")
            
            # FALLBACK: Brute-force search across all projects/regions
            logger.debug(f"Falling back to brute-force search for volume {volume_id}")
            
            # Ensure regions are discovered
            if not self.client.regions:
                try:
                    self.client.get_available_regions()
                except Exception as e:
                    logger.warning(f"Failed to discover regions: {e}")
            
            # Get all projects from billing
            projects = self.client.get_all_projects_from_billing()
            if not projects:
                logger.warning("No projects discovered from billing")
                return None
            
            # Use discovered regions, fallback to known regions
            regions_to_try = list(self.client.regions.keys()) if self.client.regions else ['ru-3', 'ru-7', 'ru-8']
            
            for project in projects:
                project_id = project.get('id')
                project_name = project.get('name', 'Unknown')
                
                for region in regions_to_try:
                    try:
                        volumes = self.client.get_openstack_volumes(project_id, region=region)
                        for volume in volumes:
                            if volume['id'] == volume_id:
                                logger.info(f"Found volume {volume_id} in project '{project_name}' region {region}")
                                return volume
                    except Exception as e:
                        logger.debug(f"Volume {volume_id} not in project '{project_name}' region {region}: {e}")
                        continue
            
            logger.warning(f"Volume {volume_id} not found in any project/region combination")
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
            # Convert to uppercase first to handle case variations
            raw_status_upper = raw_status.upper() if isinstance(raw_status, str) else 'UNKNOWN'
            
            if raw_status_upper == 'ACTIVE':
                normalized_status = 'RUNNING'  # Match Beget convention
            elif raw_status_upper in ['SHUTOFF', 'STOPPED']:
                normalized_status = 'STOPPED'
            elif raw_status_upper == 'RESERVED':  # OpenStack volume status for detached volumes
                normalized_status = 'STOPPED'  # Detached volumes are stopped
            elif raw_status_upper in ['ERROR', 'FAILED']:
                normalized_status = 'ERROR'
            else:
                normalized_status = raw_status_upper
            
            # Extract external IP from ip_addresses (prefer public/floating IPs over private)
            external_ip = None
            if 'ip_addresses' in metadata and metadata['ip_addresses']:
                # Try to find a public IP (typically starts with something other than 10., 172.16-31., 192.168.)
                for ip in metadata['ip_addresses']:
                    if ip and not ip.startswith(('10.', '172.16.', '172.17.', '172.18.', '172.19.', 
                                                  '172.20.', '172.21.', '172.22.', '172.23.', '172.24.', 
                                                  '172.25.', '172.26.', '172.27.', '172.28.', '172.29.', 
                                                  '172.30.', '172.31.', '192.168.')):
                        external_ip = ip
                        break
                # If no public IP found, use the first one
                if not external_ip and metadata['ip_addresses']:
                    external_ip = metadata['ip_addresses'][0]
            
            unified_resource = {
                'resource_id': resource_id,
                'resource_name': name,
                'resource_type': resource_type,
                'service_name': service_name or ('Account' if resource_type == 'account' else resource_type.title()),
                'region': region or ('global' if resource_type == 'account' else 'unknown'),
                'status': normalized_status,
                'effective_cost': 0.0,
                'provider_config': metadata,
                'external_ip': external_ip
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
                    # Update external IP
                    existing_resource.external_ip = external_ip
                
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
                    external_ip=external_ip,  # Set external IP
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
        import json
        
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
                    
                    # Add daily aggregated data for UI charts
                    if cpu_stats.get('daily_aggregated'):
                        daily_data = cpu_stats['daily_aggregated']
                        raw_data = {
                            'dates': [d['date'] for d in daily_data],
                            'values': [d['value'] for d in daily_data]
                        }
                        server_resource.add_tag('cpu_raw_data', json.dumps(raw_data))
                
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
                    
                    # Add daily aggregated data for UI charts
                    if mem_stats.get('daily_aggregated'):
                        daily_data = mem_stats['daily_aggregated']
                        raw_data = {
                            'dates': [d['date'] for d in daily_data],
                            'values': [d['value'] for d in daily_data]
                        }
                        server_resource.add_tag('memory_raw_data', json.dumps(raw_data))
                
                # Also add usage statistics to provider_config for UI display
                if server_resource.provider_config:
                    import json
                    config = json.loads(server_resource.provider_config)
                    
                    # Add usage statistics to metadata
                    usage_stats = {}
                    if stats.get('cpu_statistics'):
                        cpu_stats = stats['cpu_statistics']
                        usage_stats['cpu'] = {
                            'avg_usage': cpu_stats.get('avg_cpu_usage', 0),
                            'max_usage': cpu_stats.get('max_cpu_usage', 0),
                            'min_usage': cpu_stats.get('min_cpu_usage', 0),
                            'trend': cpu_stats.get('trend', 0),
                            'performance_tier': cpu_stats.get('performance_tier', 'unknown')
                        }
                    
                    if stats.get('memory_statistics'):
                        mem_stats = stats['memory_statistics']
                        usage_stats['memory'] = {
                            'avg_usage_mb': mem_stats.get('avg_memory_usage_mb', 0),
                            'max_usage_mb': mem_stats.get('max_memory_usage_mb', 0),
                            'min_usage_mb': mem_stats.get('min_memory_usage_mb', 0),
                            'usage_percent': mem_stats.get('memory_usage_percent', 0),
                            'trend': mem_stats.get('trend', 0)
                        }
                    
                    if usage_stats:
                        config['usage_statistics'] = usage_stats
                        server_resource.provider_config = json.dumps(config)
                        server_resource.last_sync = datetime.now()
                        db.session.add(server_resource)
                
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
