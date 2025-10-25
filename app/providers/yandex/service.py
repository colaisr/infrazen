"""
Yandex Cloud provider service implementation
"""
from typing import Dict, List, Any, Optional
from app.providers.yandex.client import YandexClient
from app.core.models.provider import CloudProvider
from app.core.models.resource import Resource
from app.core.models.sync import SyncSnapshot
from app.core.models.unrecognized_resource import UnrecognizedResource
from app.core.database import db
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class YandexService:
    """Service for managing Yandex Cloud provider operations"""
    
    def __init__(self, provider: CloudProvider):
        """
        Initialize Yandex Cloud service
        
        Args:
            provider: CloudProvider instance
        """
        self.provider = provider
        self.credentials = json.loads(provider.credentials)
        
        # Add cloud_id and folder_id to credentials if available
        credentials_with_ids = self.credentials.copy()
        if provider.account_id:
            # Parse account_id as cloud_id or folder_id
            if 'cloud_id' not in credentials_with_ids:
                credentials_with_ids['cloud_id'] = provider.account_id
        
        self.client = YandexClient(credentials_with_ids)
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection to Yandex Cloud API
        
        Returns:
            Dict containing test results
        """
        try:
            result = self.client.test_connection()
            
            if result['success']:
                # Update provider metadata with cloud info
                clouds = result.get('clouds', [])
                if clouds:
                    self.provider.provider_metadata = json.dumps({
                        'clouds': clouds,
                        'clouds_count': result.get('clouds_found', 0),
                        'last_test': datetime.now().isoformat()
                    })
                    db.session.commit()
            
            return result
            
        except Exception as e:
            logger.error(f"Yandex Cloud connection test failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Connection test failed'
            }
    
    def sync_resources(self) -> Dict[str, Any]:
        """
        Sync resources from Yandex Cloud
        
        This method follows a resource-discovery approach since Yandex Cloud's
        billing API requires special permissions and may not be immediately available.
        
        Process:
        1. Discover all clouds and folders
        2. List all resources in each folder
        3. Create/update resources in database
        4. Calculate estimated costs based on resource types
        
        Returns:
            Dict containing sync results
        """
        try:
            # Create sync snapshot entry
            sync_snapshot = SyncSnapshot(
                provider_id=self.provider.id,
                sync_type='resource_discovery',
                sync_status='running',
                sync_started_at=datetime.now()
            )
            db.session.add(sync_snapshot)
            db.session.commit()
            
            logger.info("PHASE 1: Discovering clouds and folders")
            
            # Get all resources across all folders
            all_resources = self.client.get_all_resources()
            
            if 'error' in all_resources:
                raise Exception(all_resources['error'])
            
            synced_resources = []
            total_instances = 0
            total_disks = 0
            total_cost = 0.0
            
            logger.info(f"PHASE 2: Processing {len(all_resources['folders'])} folders")
            
            # Process each folder's resources
            for folder_info in all_resources['folders']:
                folder = folder_info['folder']
                cloud_id = folder_info['cloud_id']
                resources = folder_info['resources']
                
                folder_id = folder['id']
                folder_name = folder.get('name', folder_id)
                
                logger.info(f"Processing folder: {folder_name} ({folder_id})")
                
                # Process instances (VMs)
                instances = resources.get('instances', [])
                disks = resources.get('disks', [])  # Get disks list for size lookup
                
                for instance in instances:
                    vm_resource = self._process_instance_resource(
                        instance,
                        folder_id,
                        folder_name,
                        cloud_id,
                        sync_snapshot.id,
                        disks  # Pass disks list for boot disk size lookup
                    )
                    if vm_resource:
                        synced_resources.append(vm_resource)
                        total_instances += 1
                        total_cost += vm_resource.daily_cost or 0.0
                
                # Process standalone disks (not attached to VMs)
                for disk in disks:
                    # Skip if disk is attached to an instance (will be unified with VM)
                    if disk.get('instanceIds'):
                        continue
                    
                    disk_resource = self._process_disk_resource(
                        disk,
                        folder_id,
                        folder_name,
                        cloud_id,
                        sync_snapshot.id
                    )
                    if disk_resource:
                        synced_resources.append(disk_resource)
                        total_disks += 1
                        total_cost += disk_resource.daily_cost or 0.0
            
            # Update sync snapshot
            sync_snapshot.sync_status = 'success'
            sync_snapshot.sync_completed_at = datetime.now()
            sync_snapshot.resources_created = len(synced_resources)
            sync_snapshot.total_resources_found = len(synced_resources)
            sync_snapshot.calculate_duration()
            
            # Store metadata
            sync_config = {
                'sync_method': 'resource_discovery',
                'clouds_discovered': len(all_resources['clouds']),
                'folders_discovered': len(all_resources['folders']),
                'total_instances': total_instances,
                'total_disks': total_disks,
                'total_estimated_daily_cost': round(total_cost, 2)
            }
            sync_snapshot.sync_config = json.dumps(sync_config)
            
            # Update provider
            self.provider.last_sync = datetime.now()
            self.provider.sync_status = 'success'
            self.provider.sync_error = None
            
            db.session.commit()
            
            logger.info(f"Sync completed: {len(synced_resources)} resources, estimated {total_cost:.2f} ₽/day")
            
            return {
                'success': True,
                'resources_synced': len(synced_resources),
                'total_instances': total_instances,
                'total_disks': total_disks,
                'estimated_daily_cost': round(total_cost, 2),
                'sync_snapshot_id': sync_snapshot.id,
                'message': f'Successfully synced {len(synced_resources)} resources (estimated cost: {total_cost:.2f} ₽/day)'
            }
            
        except Exception as e:
            logger.error(f"Yandex Cloud sync failed: {str(e)}", exc_info=True)
            
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
    
    def _process_instance_resource(self, instance: Dict, folder_id: str, 
                                    folder_name: str, cloud_id: str,
                                    sync_snapshot_id: int,
                                    all_disks: List[Dict[str, Any]] = None) -> Optional[Resource]:
        """
        Process Yandex Cloud instance (VM) resource
        
        Args:
            instance: Instance data from API
            folder_id: Folder ID
            folder_name: Folder name
            cloud_id: Cloud ID
            sync_snapshot_id: Sync snapshot ID
            all_disks: List of all disks in folder (for boot disk size lookup)
        
        Returns:
            Resource instance or None
        """
        try:
            instance_id = instance['id']
            instance_name = instance.get('name', instance_id)
            
            # Extract VM specifications
            resources_spec = instance.get('resources', {})
            vcpus = int(resources_spec.get('cores', 0))  # Convert to int
            ram_bytes = int(resources_spec.get('memory', 0))  # Convert to int first
            ram_gb = ram_bytes / (1024**3)  # Convert bytes to GB
            
            # Extract zone information
            zone_id = instance.get('zoneId', 'unknown')
            
            # Extract network interfaces and IPs
            network_interfaces = instance.get('networkInterfaces', [])
            ip_addresses = []
            external_ip = None
            
            for iface in network_interfaces:
                # Primary internal IP
                primary_v4 = iface.get('primaryV4Address', {})
                if primary_v4:
                    internal_ip = primary_v4.get('address')
                    if internal_ip:
                        ip_addresses.append(internal_ip)
                    
                    # Check for external IP (NAT)
                    one_to_one_nat = primary_v4.get('oneToOneNat', {})
                    if one_to_one_nat:
                        ext_ip = one_to_one_nat.get('address')
                        if ext_ip:
                            ip_addresses.append(ext_ip)
                            if not external_ip:
                                external_ip = ext_ip
            
            # Extract boot disk and attached disks
            boot_disk = instance.get('bootDisk', {})
            secondary_disks = instance.get('secondaryDisks', [])
            
            total_storage_gb = 0
            attached_disks = []
            
            # Create disk lookup map for size cross-reference
            disk_map = {}
            if all_disks:
                for disk in all_disks:
                    disk_map[disk['id']] = disk
            
            if boot_disk:
                boot_disk_id = boot_disk.get('diskId')
                
                # Get size from disks list (instance API doesn't include size)
                boot_disk_size = 0
                if boot_disk_id and boot_disk_id in disk_map:
                    boot_disk_size_bytes = int(disk_map[boot_disk_id].get('size', '0') or 0)
                    boot_disk_size = boot_disk_size_bytes / (1024**3)
                
                total_storage_gb += boot_disk_size
                attached_disks.append({
                    'disk_id': boot_disk_id,
                    'mode': boot_disk.get('mode', 'READ_WRITE'),
                    'size_gb': round(boot_disk_size, 2),
                    'is_boot': True
                })
            
            for disk in secondary_disks:
                disk_id = disk.get('diskId')
                
                # Get size from disks list (instance API doesn't include size)
                disk_size = 0
                if disk_id and disk_id in disk_map:
                    disk_size_bytes = int(disk_map[disk_id].get('size', '0') or 0)
                    disk_size = disk_size_bytes / (1024**3)
                
                total_storage_gb += disk_size
                attached_disks.append({
                    'disk_id': disk_id,
                    'mode': disk.get('mode', 'READ_WRITE'),
                    'size_gb': round(disk_size, 2),
                    'is_boot': False
                })
            
            # Extract status
            status_raw = instance.get('status', 'UNKNOWN')
            # Map Yandex statuses to our standard statuses
            status_map = {
                'RUNNING': 'RUNNING',
                'STOPPED': 'STOPPED',
                'STOPPING': 'STOPPING',
                'STARTING': 'STARTING',
                'RESTARTING': 'RESTARTING',
                'UPDATING': 'UPDATING',
                'ERROR': 'ERROR',
                'CRASHED': 'ERROR',
                'DELETING': 'DELETING'
            }
            status = status_map.get(status_raw, status_raw)
            
            # Estimate daily cost (rough estimation based on resources)
            # Note: Replace with actual billing API data when available
            estimated_daily_cost = self._estimate_instance_cost(vcpus, ram_gb, total_storage_gb, zone_id)
            
            # Create resource metadata
            metadata = {
                'instance': instance,
                'folder_id': folder_id,
                'folder_name': folder_name,
                'cloud_id': cloud_id,
                'zone_id': zone_id,
                'vcpus': vcpus,
                'ram_gb': ram_gb,
                'ram_mb': ram_gb * 1024,
                'total_storage_gb': total_storage_gb,
                'attached_disks': attached_disks,
                'ip_addresses': ip_addresses,
                'external_ip': external_ip,
                'network_interfaces': network_interfaces,
                'created_at': instance.get('createdAt'),
                'platform_id': instance.get('platformId'),
                'estimated_cost': True
            }
            
            resource = self._create_resource(
                resource_type='server',
                resource_id=instance_id,
                name=instance_name,
                metadata=metadata,
                sync_snapshot_id=sync_snapshot_id,
                region=zone_id,
                service_name='Compute Cloud'
            )
            
            if resource:
                resource.daily_cost = estimated_daily_cost
                resource.effective_cost = estimated_daily_cost
                resource.original_cost = estimated_daily_cost * 30  # Monthly estimate
                resource.currency = 'RUB'
                resource.external_ip = external_ip
                resource.add_tag('folder_id', folder_id)
                resource.add_tag('folder_name', folder_name)
                resource.add_tag('cloud_id', cloud_id)
                resource.add_tag('cost_source', 'estimated')
                resource.add_tag('platform_id', instance.get('platformId', 'unknown'))
            
            return resource
            
        except Exception as e:
            logger.error(f"Error processing instance {instance.get('id')}: {e}")
            return None
    
    def _process_disk_resource(self, disk: Dict, folder_id: str, 
                                folder_name: str, cloud_id: str,
                                sync_snapshot_id: int) -> Optional[Resource]:
        """
        Process standalone disk resource
        
        Args:
            disk: Disk data from API
            folder_id: Folder ID
            folder_name: Folder name
            cloud_id: Cloud ID
            sync_snapshot_id: Sync snapshot ID
        
        Returns:
            Resource instance or None
        """
        try:
            disk_id = disk['id']
            disk_name = disk.get('name', disk_id)
            
            # Extract disk specifications
            size_bytes = int(disk.get('size', 0))  # Convert to int first
            size_gb = size_bytes / (1024**3)  # Convert bytes to GB
            disk_type = disk.get('typeId', 'unknown')
            zone_id = disk.get('zoneId', 'unknown')
            status_raw = disk.get('status', 'UNKNOWN')
            
            # Map disk statuses
            status_map = {
                'READY': 'RUNNING',
                'CREATING': 'CREATING',
                'ERROR': 'ERROR',
                'DELETING': 'DELETING'
            }
            status = status_map.get(status_raw, status_raw)
            
            # Estimate daily cost
            estimated_daily_cost = self._estimate_disk_cost(size_gb, disk_type)
            
            metadata = {
                'disk': disk,
                'folder_id': folder_id,
                'folder_name': folder_name,
                'cloud_id': cloud_id,
                'zone_id': zone_id,
                'size_gb': size_gb,
                'disk_type': disk_type,
                'created_at': disk.get('createdAt'),
                'is_standalone': True,
                'estimated_cost': True
            }
            
            resource = self._create_resource(
                resource_type='volume',
                resource_id=disk_id,
                name=disk_name,
                metadata=metadata,
                sync_snapshot_id=sync_snapshot_id,
                region=zone_id,
                service_name='Block Storage'
            )
            
            if resource:
                resource.daily_cost = estimated_daily_cost
                resource.effective_cost = estimated_daily_cost
                resource.original_cost = estimated_daily_cost * 30
                resource.currency = 'RUB'
                resource.status = status
                resource.add_tag('folder_id', folder_id)
                resource.add_tag('folder_name', folder_name)
                resource.add_tag('cloud_id', cloud_id)
                resource.add_tag('cost_source', 'estimated')
                resource.add_tag('disk_type', disk_type)
                resource.add_tag('is_orphan', 'true')  # Standalone disk
            
            return resource
            
        except Exception as e:
            logger.error(f"Error processing disk {disk.get('id')}: {e}")
            return None
    
    def _estimate_instance_cost(self, vcpus: int, ram_gb: float, 
                                 storage_gb: float, zone_id: str) -> float:
        """
        Estimate daily cost for an instance
        
        This is a rough estimation. Replace with actual billing API data.
        
        Pricing (approximate as of 2024):
        - vCPU: ~1.50 ₽/hour (Intel) or ~1.20 ₽/hour (AMD)
        - RAM: ~0.40 ₽/GB/hour
        - Storage (HDD): ~0.0015 ₽/GB/hour
        - Storage (SSD): ~0.0050 ₽/GB/hour
        """
        # Base pricing (conservative estimates)
        cpu_cost_per_hour = 1.50  # ₽ per vCPU per hour
        ram_cost_per_gb_per_hour = 0.40  # ₽ per GB per hour
        storage_cost_per_gb_per_hour = 0.0025  # ₽ per GB per hour (avg between HDD and SSD)
        
        hourly_cost = (
            vcpus * cpu_cost_per_hour +
            ram_gb * ram_cost_per_gb_per_hour +
            storage_gb * storage_cost_per_gb_per_hour
        )
        
        daily_cost = hourly_cost * 24
        
        return round(daily_cost, 2)
    
    def _estimate_disk_cost(self, size_gb: float, disk_type: str) -> float:
        """
        Estimate daily cost for a standalone disk
        
        Pricing (approximate):
        - HDD: ~0.0015 ₽/GB/hour
        - SSD: ~0.0050 ₽/GB/hour
        - NVMe: ~0.0070 ₽/GB/hour
        """
        # Determine storage cost based on type
        if 'network-ssd' in disk_type or 'ssd' in disk_type.lower():
            cost_per_gb_per_hour = 0.0050
        elif 'network-nvme' in disk_type or 'nvme' in disk_type.lower():
            cost_per_gb_per_hour = 0.0070
        else:  # HDD or unknown
            cost_per_gb_per_hour = 0.0015
        
        daily_cost = size_gb * cost_per_gb_per_hour * 24
        
        return round(daily_cost, 2)
    
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
            # Find existing resource
            existing_resource = Resource.query.filter_by(
                provider_id=self.provider.id,
                resource_id=resource_id,
                resource_type=resource_type
            ).first()
            
            # Extract status from metadata
            raw_status = metadata.get('instance', {}).get('status') or metadata.get('disk', {}).get('status', 'ACTIVE')
            status = raw_status.upper() if isinstance(raw_status, str) else 'UNKNOWN'
            
            # Normalize status
            if status == 'READY':
                status = 'RUNNING'
            elif status in ['STOPPED', 'STOPPING']:
                status = 'STOPPED'
            
            # Extract external IP
            external_ip = metadata.get('external_ip')
            
            unified_resource = {
                'resource_id': resource_id,
                'resource_name': name,
                'resource_type': resource_type,
                'service_name': service_name or resource_type.title(),
                'region': region or 'unknown',
                'status': status,
                'effective_cost': 0.0,
                'provider_config': metadata,
                'external_ip': external_ip
            }
            
            if existing_resource:
                # Update existing resource
                previous_state = existing_resource.to_dict()
                
                # Check for changes
                has_changes = False
                changes = {}
                
                key_fields = ['resource_name', 'status', 'effective_cost', 'region']
                for field in key_fields:
                    if getattr(existing_resource, field) != unified_resource.get(field):
                        has_changes = True
                        changes[field] = {
                            'previous': getattr(existing_resource, field),
                            'current': unified_resource.get(field)
                        }
                
                if has_changes:
                    existing_resource.resource_name = name
                    existing_resource.status = status
                    existing_resource.provider_config = json.dumps(metadata)
                    existing_resource.last_sync = datetime.now()
                    existing_resource.is_active = True
                    if region:
                        existing_resource.region = region
                    if service_name:
                        existing_resource.service_name = service_name
                    if external_ip:
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
                
                resource_state.set_previous_state(previous_state)
                resource_state.set_current_state(unified_resource)
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
                    region=region or 'unknown',
                    service_name=service_name or resource_type.title(),
                    status=status,
                    provider_config=json.dumps(metadata),
                    external_ip=external_ip,
                    last_sync=datetime.now(),
                    is_active=True
                )
                db.session.add(new_resource)
                db.session.flush()
                
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

