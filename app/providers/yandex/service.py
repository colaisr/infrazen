"""
Yandex Cloud provider service implementation
"""
from typing import Dict, List, Any, Optional
from app.providers.yandex.client import YandexClient
from app.providers.yandex.pricing import YandexPricing
from app.providers.yandex.sku_pricing import YandexSKUPricing
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
        Sync resources from Yandex Cloud with proper managed services support
        
        This method now properly identifies and groups managed services:
        1. Discover all clouds and folders
        2. Query managed services (Kubernetes, PostgreSQL, etc.)
        3. Query compute resources and filter out managed service nodes
        4. Create/update resources in database with proper grouping
        5. Calculate estimated costs based on resource types
        
        Returns:
            Dict containing sync results
        """
        try:
            # Create sync snapshot entry
            sync_snapshot = SyncSnapshot(
                provider_id=self.provider.id,
                sync_type='managed_services',
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
            total_snapshots = 0
            total_images = 0
            total_reserved_ips = 0
            total_load_balancers = 0
            total_registries = 0
            total_dns_zones = 0
            total_managed_clusters = 0
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
                
                # PHASE 2A: Query managed services first
                logger.info(f"  Querying managed services...")
                managed_services = self.client.get_all_managed_services(folder_id)
                
                # Get compute resources early (needed for K8s CSI volume and worker VM detection)
                folder_disks = self.client.list_disks(folder_id)
                folder_instances = self.client.list_instances(folder_id)
                logger.info(f"  Found {len(folder_disks)} disks and {len(folder_instances)} instances in folder")
                
                # Process Kubernetes clusters (pass disks for CSI volume aggregation and instances for worker VM aggregation)
                k8s_clusters = managed_services.get('kubernetes_clusters', [])
                for cluster in k8s_clusters:
                    cluster_resource = self._process_kubernetes_cluster(
                        cluster, folder_id, folder_name, cloud_id, sync_snapshot.id, folder_disks, folder_instances
                    )
                    if cluster_resource:
                        synced_resources.append(cluster_resource)
                        total_managed_clusters += 1
                        total_cost += cluster_resource.daily_cost or 0.0
                
                # Process PostgreSQL clusters
                postgres_clusters = managed_services.get('postgresql_clusters', [])
                for cluster in postgres_clusters:
                    cluster_resource = self._process_postgresql_cluster(
                        cluster, folder_id, folder_name, cloud_id, sync_snapshot.id
                    )
                    if cluster_resource:
                        synced_resources.append(cluster_resource)
                        total_managed_clusters += 1
                        total_cost += cluster_resource.daily_cost or 0.0
                
                # Process MySQL clusters
                mysql_clusters = managed_services.get('mysql_clusters', [])
                for cluster in mysql_clusters:
                    cluster_resource = self._process_mysql_cluster(
                        cluster, folder_id, folder_name, cloud_id, sync_snapshot.id
                    )
                    if cluster_resource:
                        synced_resources.append(cluster_resource)
                        total_managed_clusters += 1
                        total_cost += cluster_resource.daily_cost or 0.0
                
                # Process Kafka clusters
                kafka_clusters = managed_services.get('kafka_clusters', [])
                for cluster in kafka_clusters:
                    cluster_resource = self._process_kafka_cluster(
                        cluster, folder_id, folder_name, cloud_id, sync_snapshot.id
                    )
                    if cluster_resource:
                        synced_resources.append(cluster_resource)
                        total_managed_clusters += 1
                        total_cost += cluster_resource.daily_cost or 0.0
                
                # Process other managed services
                for service_type in ['mongodb_clusters', 'clickhouse_clusters', 'redis_clusters']:
                    clusters = managed_services.get(service_type, [])
                    for cluster in clusters:
                        cluster_resource = self._process_managed_cluster(
                            cluster, service_type.replace('_clusters', ''), 
                            folder_id, folder_name, cloud_id, sync_snapshot.id
                        )
                        if cluster_resource:
                            synced_resources.append(cluster_resource)
                            total_managed_clusters += 1
                            total_cost += cluster_resource.daily_cost or 0.0
                
                # PHASE 2B: Process compute resources, filtering out managed service nodes
                logger.info(f"  Processing compute resources (filtering managed service nodes)...")
                instances = folder_instances  # Use instances fetched earlier
                disks = folder_disks  # Use disks fetched earlier for K8s CSI volume detection
                
                # Get cluster IDs for tagging (but DON'T filter out K8s worker VMs!)
                # According to Yandex billing:
                # - "Managed Service for Kubernetes" = Master node cost only
                # - "Compute Cloud" = ALL VMs including K8s worker nodes
                k8s_cluster_ids = {cluster['id'] for cluster in k8s_clusters}
                
                # Process standalone VMs (skip K8s worker nodes - they're aggregated into cluster)
                for instance in instances:
                    # Check if this is a K8s worker node (already aggregated into cluster)
                    labels = instance.get('labels', {})
                    cluster_id = labels.get('managed-kubernetes-cluster-id')
                    
                    if cluster_id:
                        # Skip K8s worker nodes - they're aggregated into the cluster resource
                        logger.debug(f"Skipping K8s worker node {instance.get('name', instance.get('id'))} (part of cluster {cluster_id})")
                        continue
                    
                    # Process standalone VM (not part of K8s cluster)
                    vm_resource = self._process_instance_resource(
                        instance,
                        folder_id,
                        folder_name,
                        cloud_id,
                        sync_snapshot.id,
                        disks
                    )
                    if vm_resource:
                        synced_resources.append(vm_resource)
                        total_instances += 1
                        total_cost += vm_resource.daily_cost or 0.0
                
                # Process standalone disks (not attached to VMs)
                # Note: Skip K8s CSI volumes (already aggregated into cluster cost)
                # Also skip database service disks (postgres, mysql, etc.) as they're in cluster costs
                for disk in disks:
                    # Skip if disk is attached to an instance
                    if disk.get('instanceIds'):
                        continue
                    
                    disk_name = disk.get('name', '')
                    labels = disk.get('labels', {})
                    
                    # Skip K8s CSI volumes (already counted in cluster cost)
                    if labels.get('cluster-name') or disk_name.startswith('k8s-csi-'):
                        logger.debug(f"    Skipping K8s CSI volume: {disk_name} (included in cluster cost)")
                        continue
                    
                    # Skip database service disks
                    if any(pattern in disk_name.lower() for pattern in ['postgres', 'mysql', 'mongodb', 'clickhouse', 'redis']):
                        logger.debug(f"    Skipping database service disk: {disk_name}")
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
                
                # PHASE 2C: Process snapshots
                logger.info(f"  Processing snapshots...")
                snapshots = self.client.list_snapshots(folder_id)
                total_snapshots = 0
                for snapshot in snapshots:
                    snapshot_resource = self._process_snapshot_resource(
                        snapshot,
                        folder_id,
                        folder_name,
                        cloud_id,
                        sync_snapshot.id
                    )
                    if snapshot_resource:
                        synced_resources.append(snapshot_resource)
                        total_snapshots += 1
                        total_cost += snapshot_resource.daily_cost or 0.0
                
                # PHASE 2D: Process custom images
                logger.info(f"  Processing custom images...")
                images = self.client.list_images(folder_id)
                total_images = 0
                for image in images:
                    image_resource = self._process_image_resource(
                        image,
                        folder_id,
                        folder_name,
                        cloud_id,
                        sync_snapshot.id
                    )
                    if image_resource:
                        synced_resources.append(image_resource)
                        total_images += 1
                        total_cost += image_resource.daily_cost or 0.0
                
                # PHASE 2E: Process reserved (unused) public IPs
                logger.info(f"  Processing reserved IPs...")
                addresses = self.client.list_addresses(folder_id)
                total_reserved_ips = 0
                for address in addresses:
                    reserved_ip_resource = self._process_reserved_ip_resource(
                        address,
                        folder_id,
                        folder_name,
                        cloud_id,
                        sync_snapshot.id
                    )
                    if reserved_ip_resource:
                        synced_resources.append(reserved_ip_resource)
                        total_reserved_ips += 1
                        total_cost += reserved_ip_resource.daily_cost or 0.0
                
                # PHASE 2F: Process network load balancers
                logger.info(f"  Processing load balancers...")
                load_balancers = self.client.list_network_load_balancers(folder_id)
                total_load_balancers = 0
                for lb in load_balancers:
                    lb_resource = self._process_load_balancer_resource(
                        lb,
                        folder_id,
                        folder_name,
                        cloud_id,
                        sync_snapshot.id
                    )
                    if lb_resource:
                        synced_resources.append(lb_resource)
                        total_load_balancers += 1
                        total_cost += lb_resource.daily_cost or 0.0
                
                # PHASE 2G: Process container registries
                logger.info(f"  Processing container registries...")
                registries = self.client.list_container_registries(folder_id)
                total_registries = 0
                for registry in registries:
                    registry_resource = self._process_container_registry_resource(
                        registry,
                        folder_id,
                        folder_name,
                        cloud_id,
                        sync_snapshot.id
                    )
                    if registry_resource:
                        synced_resources.append(registry_resource)
                        total_registries += 1
                        total_cost += registry_resource.daily_cost or 0.0
                
                # PHASE 2H: Process DNS zones
                logger.info(f"  Processing DNS zones...")
                dns_zones = self.client.list_dns_zones(folder_id)
                total_dns_zones = 0
                for zone in dns_zones:
                    dns_resource = self._process_dns_zone_resource(
                        zone,
                        folder_id,
                        folder_name,
                        cloud_id,
                        sync_snapshot.id
                    )
                    if dns_resource:
                        synced_resources.append(dns_resource)
                        total_dns_zones += 1
                        total_cost += dns_resource.daily_cost or 0.0
            
            # Update sync snapshot
            sync_snapshot.sync_status = 'success'
            sync_snapshot.sync_completed_at = datetime.now()
            sync_snapshot.resources_created = len(synced_resources)
            sync_snapshot.total_resources_found = len(synced_resources)
            sync_snapshot.calculate_duration()
            
            # Store metadata
            sync_config = {
                'sync_method': 'managed_services',
                'clouds_discovered': len(all_resources['clouds']),
                'folders_discovered': len(all_resources['folders']),
                'total_instances': total_instances,
                'total_disks': total_disks,
                'total_snapshots': total_snapshots,
                'total_images': total_images,
                'total_reserved_ips': total_reserved_ips,
                'total_load_balancers': total_load_balancers,
                'total_registries': total_registries,
                'total_dns_zones': total_dns_zones,
                'total_managed_clusters': total_managed_clusters,
                'total_estimated_daily_cost': round(total_cost, 2)
            }
            sync_snapshot.sync_config = json.dumps(sync_config)
            
            # PHASE 3: Collect performance statistics (CPU usage) - OPTIONAL
            provider_metadata = json.loads(self.provider.provider_metadata) if self.provider.provider_metadata else {}
            collect_stats = provider_metadata.get('collect_performance_stats', True)
            
            logger.info(f"PHASE 3: Performance statistics {'ENABLED' if collect_stats else 'DISABLED'}")
            
            vm_resources = [r for r in synced_resources if r.resource_type == 'server']
            
            if vm_resources and collect_stats:
                logger.info(f"Collecting CPU statistics for {len(vm_resources)} standalone VMs...")
                
                for vm_resource in vm_resources:
                    try:
                        cpu_stats = self.client.get_instance_cpu_statistics(
                            instance_id=vm_resource.resource_id,
                            folder_id=folder_id,
                            days=30
                        )
                        
                        if cpu_stats and not cpu_stats.get('no_data'):
                            vm_resource.add_tag('cpu_avg_usage', str(cpu_stats.get('avg_cpu_usage', 0)))
                            vm_resource.add_tag('cpu_max_usage', str(cpu_stats.get('max_cpu_usage', 0)))
                            vm_resource.add_tag('cpu_min_usage', str(cpu_stats.get('min_cpu_usage', 0)))
                            vm_resource.add_tag('cpu_performance_tier', cpu_stats.get('performance_tier', 'unknown'))
                            
                            if cpu_stats.get('daily_aggregated'):
                                daily_data = cpu_stats['daily_aggregated']
                                raw_data = {
                                    'dates': [d['date'] for d in daily_data],
                                    'values': [d['value'] for d in daily_data]
                                }
                                vm_resource.add_tag('cpu_raw_data', json.dumps(raw_data))
                            
                            logger.info(f"   ✅ {vm_resource.resource_name}: CPU avg={cpu_stats.get('avg_cpu_usage')}%")
                        else:
                            logger.warning(f"   ⚠️  {vm_resource.resource_name}: No CPU data available")
                    
                    except Exception as stats_error:
                        logger.error(f"   ❌ Error getting CPU stats for {vm_resource.resource_name}: {stats_error}")
                
                db.session.commit()
                logger.info(f"Performance statistics collection completed")
            
            # Update provider metadata with organization and folder info
            try:
                existing_metadata = json.loads(self.provider.provider_metadata) if self.provider.provider_metadata else {}
                
                # Get organization info
                import requests
                iam_token = self.client._get_iam_token()
                headers = {'Authorization': f'Bearer {iam_token}'}
                
                org_url = 'https://organization-manager.api.cloud.yandex.net/organization-manager/v1/organizations'
                org_response = requests.get(org_url, headers=headers, timeout=10)
                organizations = org_response.json().get('organizations', []) if org_response.status_code == 200 else []
                
                # Get folder info (use folder_id from first resource)
                folder_info = {}
                if synced_resources:
                    first_resource_config = synced_resources[0].get_provider_config()
                    folder_id = first_resource_config.get('folder_id')
                    
                    if folder_id:
                        folder_url = f'https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders/{folder_id}'
                        folder_response = requests.get(folder_url, headers=headers, timeout=10)
                        if folder_response.status_code == 200:
                            folder_info = folder_response.json()
                
                # Get current service account info
                sa_info = self.credentials.get('service_account_key', {})
                
                # Build account info
                enhanced_account_info = {
                    'organization': {
                        'name': organizations[0].get('title') if organizations else 'N/A',
                        'legal_name': organizations[0].get('description') if organizations else 'N/A',
                        'id': organizations[0].get('id') if organizations else 'N/A'
                    } if organizations else {},
                    'folder': {
                        'name': folder_info.get('name', 'N/A'),
                        'cloud_id': folder_info.get('cloudId', 'N/A'),
                        'status': folder_info.get('status', 'N/A')
                    } if folder_info else {},
                    'service_account': {
                        'name': 'infrazen',  # Can extract from SA key if needed
                        'id': sa_info.get('service_account_id', 'N/A')
                    }
                }
                
                # Merge with existing metadata
                existing_metadata['account_info'] = enhanced_account_info
                existing_metadata['last_account_update'] = datetime.now().isoformat()
                
                self.provider.provider_metadata = json.dumps(existing_metadata)
            except Exception as meta_error:
                logger.warning(f"Failed to update Yandex account metadata: {meta_error}")
            
            # Update provider
            self.provider.last_sync = datetime.now()
            self.provider.sync_status = 'success'
            self.provider.sync_error = None
            
            db.session.commit()
            
            logger.info(f"Sync completed: {len(synced_resources)} resources ({total_managed_clusters} clusters, {total_instances} VMs, {total_disks} disks, {total_snapshots} snapshots, {total_images} images, {total_reserved_ips} reserved IPs, {total_load_balancers} load balancers, {total_registries} registries, {total_dns_zones} DNS zones), estimated {total_cost:.2f} ₽/day")
            
            return {
                'success': True,
                'resources_synced': len(synced_resources),
                'total_managed_clusters': total_managed_clusters,
                'total_instances': total_instances,
                'total_disks': total_disks,
                'total_snapshots': total_snapshots,
                'total_images': total_images,
                'total_reserved_ips': total_reserved_ips,
                'total_load_balancers': total_load_balancers,
                'total_registries': total_registries,
                'total_dns_zones': total_dns_zones,
                'estimated_daily_cost': round(total_cost, 2),
                'sync_snapshot_id': sync_snapshot.id,
                'cpu_stats_collected': collect_stats and len(vm_resources) > 0,
                'message': f'Successfully synced {len(synced_resources)} resources ({total_managed_clusters} clusters, {total_instances} VMs, {total_disks} disks, {total_snapshots} snapshots, {total_images} images, {total_reserved_ips} reserved IPs, {total_load_balancers} load balancers, {total_registries} registries, {total_dns_zones} DNS zones) - estimated cost: {total_cost:.2f} ₽/day'
            }
            
        except Exception as e:
            logger.error(f"Yandex Cloud sync failed: {str(e)}", exc_info=True)
            
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
                'sync_snapshot_id': snapshot_id
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
                
                # Get size and type from disks list (instance API doesn't include these)
                boot_disk_size = 0
                boot_disk_type = 'network-ssd'  # Default
                if boot_disk_id and boot_disk_id in disk_map:
                    boot_disk_size_bytes = int(disk_map[boot_disk_id].get('size', '0') or 0)
                    boot_disk_size = boot_disk_size_bytes / (1024**3)
                    boot_disk_type = disk_map[boot_disk_id].get('typeId', 'network-ssd')
                
                total_storage_gb += boot_disk_size
                attached_disks.append({
                    'disk_id': boot_disk_id,
                    'mode': boot_disk.get('mode', 'READ_WRITE'),
                    'size_gb': round(boot_disk_size, 2),
                    'type': boot_disk_type,
                    'device_name': boot_disk.get('deviceName', 'boot'),
                    'is_boot': True
                })
            
            for disk in secondary_disks:
                disk_id = disk.get('diskId')
                
                # Get size and type from disks list (instance API doesn't include these)
                disk_size = 0
                disk_type = 'network-ssd'  # Default
                if disk_id and disk_id in disk_map:
                    disk_size_bytes = int(disk_map[disk_id].get('size', '0') or 0)
                    disk_size = disk_size_bytes / (1024**3)
                    disk_type = disk_map[disk_id].get('typeId', 'network-ssd')
                
                total_storage_gb += disk_size
                attached_disks.append({
                    'disk_id': disk_id,
                    'mode': disk.get('mode', 'READ_WRITE'),
                    'size_gb': round(disk_size, 2),
                    'type': disk_type,
                    'device_name': disk.get('deviceName', f'disk-{disk_id[:8]}'),
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
            
            # Extract pricing parameters
            platform_id = instance.get('platformId', 'standard-v3')
            core_fraction = int(resources_spec.get('coreFraction', 100))
            
            # Check for public IP
            has_public_ip = bool(external_ip)
            
            # Calculate CPU + RAM cost first (without storage)
            base_cost = self._estimate_instance_cost(
                vcpus, ram_gb, 0,  # Pass 0 for storage - we'll calculate disks separately
                zone_id,
                platform_id=platform_id,
                core_fraction=core_fraction,
                disk_type='network-ssd',  # Not used when storage_gb=0
                has_public_ip=has_public_ip,
                status=status
            )
            
            # Calculate storage cost for each disk separately (with their individual types)
            total_disk_cost = 0
            for disk_info in attached_disks:
                disk_size = disk_info.get('size_gb', 0)
                disk_type = disk_info.get('type', 'network-ssd')
                
                # For stopped VMs, only charge for disks
                if status in ['STOPPED', 'STOPPING']:
                    disk_cost = self._estimate_disk_cost(disk_size, disk_type)
                    total_disk_cost += disk_cost
                else:
                    # For running VMs, charge for disks normally
                    disk_cost = self._estimate_disk_cost(disk_size, disk_type)
                    total_disk_cost += disk_cost
            
            # Total VM cost = base (CPU+RAM+IP) + all disks
            estimated_daily_cost = base_cost + total_disk_cost
            
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
                                 storage_gb: float, zone_id: str, 
                                 platform_id: str = 'standard-v3',
                                 core_fraction: int = 100,
                                 disk_type: str = 'network-ssd',
                                 has_public_ip: bool = False,
                                 status: str = 'RUNNING') -> float:
        """
        Calculate instance cost using SKU-based pricing (99.97% accuracy!)
        
        Uses actual SKU prices from Yandex Billing API, synced to our database.
        Falls back to documented pricing if SKUs not available.
        
        IMPORTANT: Yandex Cloud billing rules for STOPPED VMs:
        - STOPPED VMs only pay for disk storage (no CPU/RAM charges)
        - RUNNING VMs pay full cost (CPU + RAM + disk + optional public IP)
        
        Args:
            status: VM status ('RUNNING', 'STOPPED', etc.)
        """
        # STOPPED VMs only pay for disk storage
        if status in ['STOPPED', 'STOPPING']:
            logger.debug(f"VM is {status} - calculating disk-only cost")
            disk_only_cost = self._estimate_disk_cost(storage_gb, disk_type)
            logger.info(f"  STOPPED VM: disk only = {disk_only_cost:.2f} ₽/day (storage: {storage_gb} GB)")
            return disk_only_cost
        
        # RUNNING VMs: full cost calculation
        # Try SKU-based pricing first (99.97% accurate)
        sku_cost = YandexSKUPricing.calculate_vm_cost(
            vcpus=vcpus,
            ram_gb=ram_gb,
            storage_gb=storage_gb,
            platform_id=platform_id,
            core_fraction=core_fraction,
            disk_type=disk_type,
            has_public_ip=has_public_ip
        )
        
        if sku_cost and sku_cost.get('accuracy') == 'sku_based':
            logger.debug(f"Using SKU-based pricing: {sku_cost['daily_cost']} ₽/day")
            return sku_cost['daily_cost']
        
        # Fallback to documented pricing
        logger.warning("SKU prices not available, falling back to documented pricing")
        cost_data = YandexPricing.calculate_vm_cost(
            vcpus=vcpus,
            ram_gb=ram_gb,
            storage_gb=storage_gb,
            platform_id=platform_id,
            core_fraction=core_fraction,
            disk_type=disk_type,
            has_public_ip=has_public_ip
        )
        
        return cost_data['daily_cost']
    
    def _estimate_disk_cost(self, size_gb: float, disk_type: str) -> float:
        """
        Calculate standalone disk cost using SKU-based pricing
        
        Uses actual SKU prices for maximum accuracy
        """
        # Try SKU-based pricing first
        sku_cost = YandexSKUPricing.calculate_disk_cost(
            size_gb=size_gb,
            disk_type=disk_type
        )
        
        if sku_cost and sku_cost.get('accuracy') == 'sku_based':
            return sku_cost['daily_cost']
        
        # Fallback to documented pricing
        cost_data = YandexPricing.calculate_disk_cost(
            size_gb=size_gb,
            disk_type=disk_type
        )
        
        return cost_data['daily_cost']
    
    def _process_snapshot_resource(self, snapshot: Dict, folder_id: str, 
                                   folder_name: str, cloud_id: str,
                                   sync_snapshot_id: int) -> Optional[Resource]:
        """
        Process snapshot resource
        
        Snapshots are storage-based resources charged per GB per day.
        From HAR analysis: 0.1123₽/GB/day (478.98₽ for 4,264 GB)
        
        Args:
            snapshot: Snapshot data from API
            folder_id: Folder ID
            folder_name: Folder name
            cloud_id: Cloud ID
            sync_snapshot_id: Sync snapshot ID
        
        Returns:
            Resource instance or None
        """
        try:
            snapshot_id = snapshot['id']
            snapshot_name = snapshot.get('name', snapshot_id)
            
            # Extract snapshot specifications
            size_bytes = int(snapshot.get('storageSize', 0))
            size_gb = size_bytes / (1024**3)
            status_raw = snapshot.get('status', 'UNKNOWN')
            source_disk_id = snapshot.get('sourceDiskId', '')
            
            # Map snapshot statuses
            status_map = {
                'READY': 'RUNNING',
                'CREATING': 'CREATING',
                'ERROR': 'ERROR',
                'DELETING': 'DELETING'
            }
            status = status_map.get(status_raw, status_raw)
            
            # Snapshot pricing: 0.1123₽/GB/day (from HAR analysis)
            # This matches documented pricing of ~0.0047₽/GB/hour
            daily_cost = size_gb * 0.1123
            
            metadata = {
                'snapshot': snapshot,
                'folder_id': folder_id,
                'folder_name': folder_name,
                'cloud_id': cloud_id,
                'size_gb': round(size_gb, 2),
                'source_disk_id': source_disk_id,
                'created_at': snapshot.get('createdAt'),
                'cost_source': 'har_analysis'
            }
            
            resource = self._create_resource(
                resource_type='snapshot',
                resource_id=snapshot_id,
                name=snapshot_name,
                metadata=metadata,
                sync_snapshot_id=sync_snapshot_id,
                region=folder_id,
                service_name='Compute Cloud'
            )
            
            if resource:
                resource.daily_cost = round(daily_cost, 2)
                resource.effective_cost = round(daily_cost, 2)
                resource.original_cost = round(daily_cost * 30, 2)
                resource.currency = 'RUB'
                resource.status = status
                resource.add_tag('source_disk_id', source_disk_id)
                resource.add_tag('cost_source', 'har_analysis')
                resource.add_tag('pricing_per_gb_day', '0.1123')
                
                logger.debug(f"    Snapshot: {snapshot_name} ({size_gb:.1f} GB) = {daily_cost:.2f} ₽/day")
            
            return resource
            
        except Exception as e:
            logger.error(f"Error processing snapshot {snapshot.get('id', 'unknown')}: {str(e)}")
            return None
    
    def _process_image_resource(self, image: Dict, folder_id: str, 
                                folder_name: str, cloud_id: str,
                                sync_snapshot_id: int) -> Optional[Resource]:
        """
        Process custom image resource
        
        Custom images are storage-based resources charged per GB per day.
        From HAR analysis: 0.1382₽/GB/day (126.02₽ for 912 GB)
        
        Args:
            image: Image data from API
            folder_id: Folder ID
            folder_name: Folder name
            cloud_id: Cloud ID
            sync_snapshot_id: Sync snapshot ID
        
        Returns:
            Resource instance or None
        """
        try:
            image_id = image['id']
            image_name = image.get('name', image_id)
            
            # Extract image specifications
            size_bytes = int(image.get('storageSize', 0))
            size_gb = size_bytes / (1024**3)
            status_raw = image.get('status', 'UNKNOWN')
            
            # Map image statuses
            status_map = {
                'READY': 'RUNNING',
                'CREATING': 'CREATING',
                'ERROR': 'ERROR',
                'DELETING': 'DELETING'
            }
            status = status_map.get(status_raw, status_raw)
            
            # Image pricing: 0.1382₽/GB/day (from HAR analysis)
            # This matches documented pricing of ~0.0058₽/GB/hour
            daily_cost = size_gb * 0.1382
            
            metadata = {
                'image': image,
                'folder_id': folder_id,
                'folder_name': folder_name,
                'cloud_id': cloud_id,
                'size_gb': round(size_gb, 2),
                'created_at': image.get('createdAt'),
                'cost_source': 'har_analysis'
            }
            
            resource = self._create_resource(
                resource_type='image',
                resource_id=image_id,
                name=image_name,
                metadata=metadata,
                sync_snapshot_id=sync_snapshot_id,
                region=folder_id,
                service_name='Compute Cloud'
            )
            
            if resource:
                resource.daily_cost = round(daily_cost, 2)
                resource.effective_cost = round(daily_cost, 2)
                resource.original_cost = round(daily_cost * 30, 2)
                resource.currency = 'RUB'
                resource.status = status
                resource.add_tag('cost_source', 'har_analysis')
                resource.add_tag('pricing_per_gb_day', '0.1382')
                
                logger.debug(f"    Image: {image_name} ({size_gb:.1f} GB) = {daily_cost:.2f} ₽/day")
            
            return resource
            
        except Exception as e:
            logger.error(f"Error processing image {image.get('id', 'unknown')}: {str(e)}")
            return None
    
    def _process_reserved_ip_resource(self, address: Dict, folder_id: str, 
                                     folder_name: str, cloud_id: str,
                                     sync_snapshot_id: int) -> Optional[Resource]:
        """
        Process reserved but unused public IP address
        
        Reserved IPs that are not attached to any resource still cost money.
        SKU: network.public_fips.deallocated
        Pricing: 8.04₽/day per unused IP (0.335₽/hour)
        Source: Yandex billing data (Oct 31: 120 fip*hour = 40.18₽ for 5 IPs)
        
        Args:
            address: Address data from API
            folder_id: Folder ID
            folder_name: Folder name
            cloud_id: Cloud ID
            sync_snapshot_id: Sync snapshot ID
        
        Returns:
            Resource instance or None
        """
        try:
            address_id = address['id']
            address_value = address.get('address', address_id)
            
            # Only process unused (reserved) addresses
            is_used = address.get('used', True)
            if is_used:
                return None  # Skip active IPs (they're counted in VM costs)
            
            # Reserved IP pricing (deallocated/inactive public static IP)
            # SKU: network.public_fips.deallocated (dn2nqa0nqffbhihsq2n5)
            # Source: Yandex billing data (Oct 31: 120 fip*hour = 40.18₽)
            # Calculation: 40.18₽ / 120 fip*hour = 0.3348₽/hour = 8.04₽/day
            daily_cost = 8.04
            
            metadata = {
                'address': address,
                'folder_id': folder_id,
                'folder_name': folder_name,
                'cloud_id': cloud_id,
                'ip_address': address_value,
                'is_used': is_used,
                'reserved': address.get('reserved', False),
                'created_at': address.get('createdAt'),
                'cost_source': 'billing_data',
                'sku': 'network.public_fips.deallocated',
                'sku_id': 'dn2nqa0nqffbhihsq2n5'
            }
            
            resource = self._create_resource(
                resource_type='reserved_ip',
                resource_id=address_id,
                name=f"Reserved IP: {address_value}",
                metadata=metadata,
                sync_snapshot_id=sync_snapshot_id,
                region=folder_id,
                service_name='Virtual Private Cloud'
            )
            
            if resource:
                resource.daily_cost = round(daily_cost, 2)
                resource.effective_cost = round(daily_cost, 2)
                resource.original_cost = round(daily_cost * 30, 2)
                resource.currency = 'RUB'
                resource.status = 'RUNNING'
                resource.add_tag('ip_address', address_value)
                resource.add_tag('is_reserved', 'true')
                resource.add_tag('cost_source', 'documented')
                resource.add_tag('pricing_per_day', '4.608')
                
                logger.debug(f"    Reserved IP: {address_value} = {daily_cost:.2f} ₽/day")
            
            return resource
            
        except Exception as e:
            logger.error(f"Error processing reserved IP {address.get('id', 'unknown')}: {str(e)}")
            return None
    
    def _process_load_balancer_resource(self, load_balancer: Dict, folder_id: str, 
                                       folder_name: str, cloud_id: str,
                                       sync_snapshot_id: int) -> Optional[Resource]:
        """
        Process network load balancer resource
        
        Load balancers are charged per active balancer per hour.
        From HAR analysis: 40.44₽/day per balancer (includes 1.685₽/hour base + IPs)
        
        Args:
            load_balancer: Load balancer data from API
            folder_id: Folder ID
            folder_name: Folder name
            cloud_id: Cloud ID
            sync_snapshot_id: Sync snapshot ID
        
        Returns:
            Resource instance or None
        """
        try:
            lb_id = load_balancer['id']
            lb_name = load_balancer.get('name', lb_id)
            
            # Get load balancer details
            lb_type = load_balancer.get('type', 'EXTERNAL')
            status_raw = load_balancer.get('status', 'UNKNOWN')
            
            # Map LB statuses
            status_map = {
                'ACTIVE': 'RUNNING',
                'CREATING': 'CREATING',
                'STARTING': 'STARTING',
                'STOPPING': 'STOPPING',
                'INACTIVE': 'STOPPED',
                'DELETING': 'DELETING'
            }
            status = status_map.get(status_raw, status_raw)
            
            # Count attached public IPs
            listeners = load_balancer.get('listeners', [])
            public_ip_count = 0
            public_ips = []
            
            for listener in listeners:
                address = listener.get('address')
                if address:
                    public_ips.append(address)
                    public_ip_count += 1
            
            # Load balancer pricing from HAR analysis:
            # Base balancer: 1.685₽/hour = 40.44₽/day (includes all costs)
            # This already includes the public IPs, so we use it as-is
            daily_cost = 40.44
            
            metadata = {
                'load_balancer': load_balancer,
                'folder_id': folder_id,
                'folder_name': folder_name,
                'cloud_id': cloud_id,
                'lb_type': lb_type,
                'listeners': len(listeners),
                'public_ips': public_ips,
                'public_ip_count': public_ip_count,
                'created_at': load_balancer.get('createdAt'),
                'cost_source': 'har_analysis'
            }
            
            resource = self._create_resource(
                resource_type='load_balancer',
                resource_id=lb_id,
                name=lb_name,
                metadata=metadata,
                sync_snapshot_id=sync_snapshot_id,
                region=folder_id,
                service_name='Network Load Balancer'
            )
            
            if resource:
                resource.daily_cost = round(daily_cost, 2)
                resource.effective_cost = round(daily_cost, 2)
                resource.original_cost = round(daily_cost * 30, 2)
                resource.currency = 'RUB'
                resource.status = status
                resource.add_tag('lb_type', lb_type)
                resource.add_tag('listeners', str(len(listeners)))
                resource.add_tag('public_ip_count', str(public_ip_count))
                resource.add_tag('cost_source', 'har_analysis')
                resource.add_tag('pricing_per_day', '40.44')
                
                logger.debug(f"    Load Balancer: {lb_name} ({len(listeners)} listeners) = {daily_cost:.2f} ₽/day")
            
            return resource
            
        except Exception as e:
            logger.error(f"Error processing load balancer {load_balancer.get('id', 'unknown')}: {str(e)}")
            return None
    
    def _process_container_registry_resource(self, registry: Dict, folder_id: str, 
                                            folder_name: str, cloud_id: str,
                                            sync_snapshot_id: int) -> Optional[Resource]:
        """
        Process container registry resource
        
        Registries are charged based on storage used.
        From HAR analysis: 75.94₽/day for yc-it registry
        Storage pricing: ~0.1080₽/GB/day (estimated from total cost)
        
        Args:
            registry: Registry data from API
            folder_id: Folder ID
            folder_name: Folder name
            cloud_id: Cloud ID
            sync_snapshot_id: Sync snapshot ID
        
        Returns:
            Resource instance or None
        """
        try:
            registry_id = registry['id']
            registry_name = registry.get('name', registry_id)
            
            status_raw = registry.get('status', 'UNKNOWN')
            
            # Map registry statuses
            status_map = {
                'ACTIVE': 'RUNNING',
                'CREATING': 'CREATING',
                'DELETING': 'DELETING'
            }
            status = status_map.get(status_raw, status_raw)
            
            # Container registry pricing:
            # From HAR: 75.94₽/day total
            # Assuming ~700GB storage: 75.94 ÷ 700 = 0.1085₽/GB/day
            # Since we can't get storage from API, we'll use the total from HAR
            # and divide by number of registries if we find multiple
            
            # For now, use the HAR total as a flat fee per registry
            # This will be accurate if there's only 1 registry in the account
            daily_cost = 75.94
            
            metadata = {
                'registry': registry,
                'folder_id': folder_id,
                'folder_name': folder_name,
                'cloud_id': cloud_id,
                'created_at': registry.get('createdAt'),
                'cost_source': 'har_total',
                'note': 'Storage-based pricing - total from HAR analysis'
            }
            
            resource = self._create_resource(
                resource_type='container_registry',
                resource_id=registry_id,
                name=registry_name,
                metadata=metadata,
                sync_snapshot_id=sync_snapshot_id,
                region=folder_id,
                service_name='Container Registry'
            )
            
            if resource:
                resource.daily_cost = round(daily_cost, 2)
                resource.effective_cost = round(daily_cost, 2)
                resource.original_cost = round(daily_cost * 30, 2)
                resource.currency = 'RUB'
                resource.status = status
                resource.add_tag('cost_source', 'har_total')
                resource.add_tag('pricing_model', 'storage_based')
                
                logger.debug(f"    Container Registry: {registry_name} = {daily_cost:.2f} ₽/day")
            
            return resource
            
        except Exception as e:
            logger.error(f"Error processing container registry {registry.get('id', 'unknown')}: {str(e)}")
            return None
    
    def _process_dns_zone_resource(self, zone: Dict, folder_id: str, 
                                   folder_name: str, cloud_id: str,
                                   sync_snapshot_id: int) -> Optional[Resource]:
        """
        Process DNS zone resource
        
        DNS zones are charged per zone + per query.
        From HAR analysis: 13.47₽/day total (mostly zone hosting)
        
        Args:
            zone: DNS zone data from API
            folder_id: Folder ID
            folder_name: Folder name
            cloud_id: Cloud ID
            sync_snapshot_id: Sync snapshot ID
        
        Returns:
            Resource instance or None
        """
        try:
            zone_id = zone['id']
            zone_name = zone.get('zone', zone.get('name', zone_id))
            api_name = zone.get('name', '')
            
            # DNS zone status
            # DNS zones don't have explicit status in API response
            status = 'RUNNING'
            
            # Check if this is a private DNS zone (FREE)
            # Yandex Cloud billing: Private DNS zones are FREE
            # This includes:
            # 1. Auto-created service zones (internal., 10.in-addr.arpa., .)
            #    - One set per VPC network
            #    - API name starts with "auto-"
            # 2. Manual private zones (created by user with privateVisibility)
            # Only public zones or zones with no visibility are charged
            has_private_visibility = bool(zone.get('privateVisibility'))
            has_public_visibility = bool(zone.get('publicVisibility'))
            is_auto_created = api_name.startswith('auto-')
            
            # All private zones are FREE (both auto-created and manual)
            # Only public zones (or zones with no visibility flags) are charged
            is_service_zone = has_private_visibility and not has_public_visibility
            
            # Initialize sku_cost
            sku_cost = None
            
            if is_service_zone:
                # Private zones are free - don't charge
                daily_cost = 0.0
                zone_type = 'auto-created' if is_auto_created else 'manual'
                logger.debug(f"Skipping free private DNS zone ({zone_type}): {zone_name} = FREE (FinOps: zero-cost resources not tracked)")
                # FinOps Best Practice: Do not store resources with zero cost
                return None
            else:
                # Regular DNS zones (public or manually created private)
                # Try to get DNS zone pricing from SKU database
                sku_cost = YandexSKUPricing.calculate_dns_zone_cost()
                
                if sku_cost and sku_cost.get('accuracy') == 'sku_based':
                    # Use SKU-based pricing (most accurate)
                    daily_cost = sku_cost['daily_cost']
                    logger.debug(f"Using SKU-based DNS zone pricing: {daily_cost:.2f} ₽/day")
                else:
                    # Fallback to HAR-derived pricing if SKU not available
                    # DNS pricing from HAR analysis: 1.30₽/day per zone (dns.zones.v1)
                    # Query costs are variable and small (~0.10₽/day)
                    daily_cost = 1.30
                    logger.warning(f"DNS SKU not found, using HAR-based pricing: {daily_cost:.2f} ₽/day")
            
            # Only paid zones reach here (free zones return None above)
            metadata = {
                'dns_zone': zone,
                'folder_id': folder_id,
                'folder_name': folder_name,
                'cloud_id': cloud_id,
                'zone_name': zone_name,
                'api_name': api_name,
                'created_at': zone.get('createdAt'),
                'has_private_visibility': has_private_visibility,
                'has_public_visibility': has_public_visibility,
                'cost_source': 'sku_based' if sku_cost else 'har_analysis',
                'note': 'Zone hosting cost only (queries are variable)',
                'pricing_sku': 'dns.zones.v1'
            }
            
            resource = self._create_resource(
                resource_type='dns_zone',
                resource_id=zone_id,
                name=f"DNS: {zone_name}",
                metadata=metadata,
                sync_snapshot_id=sync_snapshot_id,
                region=folder_id,
                service_name='Cloud DNS'
            )
            
            if resource:
                resource.daily_cost = round(daily_cost, 2)
                resource.effective_cost = round(daily_cost, 2)
                resource.original_cost = round(daily_cost * 30, 2)
                resource.currency = 'RUB'
                resource.status = status
                resource.add_tag('zone_name', zone_name)
                resource.add_tag('visibility_type', 'public' if has_public_visibility else 'none')
                resource.add_tag('cost_source', 'sku_based' if sku_cost else 'har_analysis')
                resource.add_tag('pricing_per_day', str(round(daily_cost, 2)))
                resource.add_tag('pricing_sku', 'dns.zones.v1')
                resource.add_tag('note', 'Query costs not included (variable)')
                
                logger.debug(f"    DNS Zone (PAID): {zone_name} = {daily_cost:.2f} ₽/day")
            
            return resource
            
        except Exception as e:
            logger.error(f"Error processing DNS zone {zone.get('id', 'unknown')}: {str(e)}")
            return None
    
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
    
    # ============================================================================
    # MANAGED SERVICES PROCESSING METHODS
    # ============================================================================
    
    def _process_kubernetes_cluster(self, cluster: Dict, folder_id: str, 
                                  folder_name: str, cloud_id: str,
                                  sync_snapshot_id: int, disks: List[Dict] = None,
                                  instances: List[Dict] = None) -> Optional[Resource]:
        """
        Process Kubernetes cluster resource
        
        Args:
            cluster: Cluster data from API
            folder_id: Folder ID
            folder_name: Folder name
            cloud_id: Cloud ID
            sync_snapshot_id: Sync snapshot ID
            disks: List of disks for CSI volume aggregation
            instances: List of VMs for worker node aggregation
        
        Returns:
            Resource instance or None
        """
        try:
            cluster_id = cluster['id']
            cluster_name = cluster.get('name', cluster_id)
            
            # Extract cluster specifications
            master = cluster.get('master', {})
            master_version = master.get('version', 'unknown')
            master_zone = master.get('zonalMaster', {}).get('zoneId', 'unknown')
            
            # Get node groups to calculate total resources
            node_groups = self.client.list_kubernetes_node_groups(cluster_id)
            
            total_nodes = 0
            total_vcpus = 0
            total_ram_gb = 0
            total_storage_gb = 0
            
            for node_group in node_groups:
                scale_policy = node_group.get('scalePolicy', {})
                fixed_scale = scale_policy.get('fixedScale', {})
                auto_scale = scale_policy.get('autoScale', {})
                
                # Get node count (API returns strings, convert to int)
                if fixed_scale:
                    node_count = int(fixed_scale.get('size', 0))
                elif auto_scale:
                    node_count = int(auto_scale.get('maxSize', 0))
                else:
                    node_count = 0
                
                total_nodes += node_count
                
                # Get node specifications
                node_template = node_group.get('nodeTemplate', {})
                resources_spec = node_template.get('resourcesSpec', {})  # Fixed: resourcesSpec not resources
                vcpus = int(resources_spec.get('cores', 0))
                ram_bytes = int(resources_spec.get('memory', 0))
                ram_gb = ram_bytes / (1024**3)
                
                total_vcpus += vcpus * node_count
                total_ram_gb += ram_gb * node_count
                
                # Get actual boot disk size from node template
                boot_disk_spec = node_template.get('bootDiskSpec', {})
                disk_size_bytes = int(boot_disk_spec.get('diskSize', 107374182400))  # Default 100GB in bytes
                disk_size_gb = disk_size_bytes / (1024**3)
                
                total_storage_gb += disk_size_gb * node_count
            
            # Estimate master cost (master node only, workers are billed as VMs)
            master_daily_cost = self._estimate_kubernetes_cluster_cost(
                total_vcpus, total_ram_gb, total_storage_gb, master_zone
            )
            
            # Find and sum CSI volumes for this cluster
            csi_volumes_cost = 0.0
            csi_volumes_count = 0
            csi_volumes_list = []
            
            if disks:
                for disk in disks:
                    labels = disk.get('labels', {})
                    disk_name = disk.get('name', '')
                    disk_cluster_id = labels.get('cluster-name')
                    
                    # Check if this disk belongs to this K8s cluster
                    if disk_cluster_id == cluster_id:
                        # Calculate disk cost
                        size_bytes = int(disk.get('size', 0))
                        size_gb = size_bytes / (1024**3)
                        disk_type = disk.get('typeId', 'network-hdd')
                        volume_cost = self._estimate_disk_cost(size_gb, disk_type)
                        
                        csi_volumes_cost += volume_cost
                        csi_volumes_count += 1
                        csi_volumes_list.append({
                            'name': disk_name,
                            'size_gb': round(size_gb, 2),
                            'type': disk_type,
                            'cost': round(volume_cost, 2)
                        })
                        
                        logger.info(f"  Found CSI volume '{disk_name}' for cluster '{cluster_name}': {volume_cost:.2f}₽/day")
            
            # Find and sum worker node VMs for this cluster
            worker_vms_cost = 0.0
            worker_vms_count = 0
            worker_vms_list = []
            
            if instances:
                for instance in instances:
                    labels = instance.get('labels', {})
                    instance_cluster_id = labels.get('managed-kubernetes-cluster-id')
                    
                    # Check if this VM is a worker node for this K8s cluster
                    if instance_cluster_id == cluster_id:
                        instance_name = instance.get('name', instance.get('id', 'unknown'))
                        
                        # Calculate VM cost (estimate from resources)
                        resources = instance.get('resources', {})
                        cores = int(resources.get('cores', 0))
                        memory_bytes = int(resources.get('memory', 0))
                        memory_gb = memory_bytes / (1024**3)
                        
                        # Get boot disk info
                        boot_disk = instance.get('bootDisk', {})
                        disk_id = boot_disk.get('diskId')
                        boot_disk_size_gb = 0
                        boot_disk_type = 'network-hdd'
                        
                        # Find boot disk in disks list
                        if disk_id and disks:
                            for disk in disks:
                                if disk.get('id') == disk_id:
                                    boot_disk_size_gb = int(disk.get('size', 0)) / (1024**3)
                                    boot_disk_type = disk.get('typeId', 'network-hdd')
                                    break
                        
                        # Get VM status for correct cost calculation (STOPPED VMs only pay for disk)
                        status_raw = instance.get('status', 'RUNNING')
                        status_map = {
                            'RUNNING': 'RUNNING', 'STOPPED': 'STOPPED', 'STOPPING': 'STOPPING',
                            'STARTING': 'STARTING', 'RESTARTING': 'RESTARTING', 'UPDATING': 'UPDATING',
                            'ERROR': 'ERROR', 'CRASHED': 'ERROR', 'DELETING': 'DELETING'
                        }
                        status = status_map.get(status_raw, status_raw)
                        
                        # Estimate VM cost (handles STOPPED VMs correctly - disk-only cost)
                        zone_id = instance.get('zoneId', 'ru-central1-a')
                        vm_cost = self._estimate_instance_cost(cores, memory_gb, boot_disk_size_gb, zone_id,
                                                               disk_type=boot_disk_type, status=status)
                        
                        worker_vms_cost += vm_cost
                        worker_vms_count += 1
                        worker_vms_list.append({
                            'name': instance_name,
                            'id': instance.get('id'),
                            'vcpu': cores,
                            'ram_gb': round(memory_gb, 1),
                            'disk_gb': round(boot_disk_size_gb, 1),
                            'disk_type': boot_disk_type,
                            'zone': zone_id,
                            'status': status,
                            'cost': round(vm_cost, 2)
                        })
                        
                        logger.info(f"  Found worker VM '{instance_name}' for cluster '{cluster_name}': {vm_cost:.2f}₽/day")
            
            # Total cluster cost = master + storage + worker VMs
            estimated_daily_cost = master_daily_cost + csi_volumes_cost + worker_vms_cost
            
            logger.info(f"  K8s cluster '{cluster_name}' total cost: {estimated_daily_cost:.2f}₽/day (master: {master_daily_cost:.2f}₽, storage: {csi_volumes_cost:.2f}₽, workers: {worker_vms_cost:.2f}₽)")
            
            # Mark CSI volumes as inactive (they're now part of cluster, not standalone)
            # This prevents them from showing up as separate resources in the UI
            from app.core.models.resource import Resource
            if csi_volumes_list:
                for csi_vol in csi_volumes_list:
                    vol_name = csi_vol['name']
                    # Find and deactivate old volume resource if it exists
                    old_volume = Resource.query.filter_by(
                        provider_id=self.provider.id,
                        resource_name=vol_name,
                        resource_type='volume',
                        is_active=True
                    ).first()
                    if old_volume:
                        old_volume.is_active = False
                        logger.debug(f"  Deactivated standalone volume resource '{vol_name}' (now part of cluster)")
            
            # Mark worker VMs as inactive (they're now part of cluster, not standalone)
            if worker_vms_list:
                for worker_vm in worker_vms_list:
                    vm_id = worker_vm['id']
                    # Find and deactivate old VM resource if it exists
                    old_vm = Resource.query.filter_by(
                        provider_id=self.provider.id,
                        resource_id=vm_id,
                        resource_type='server',
                        is_active=True
                    ).first()
                    if old_vm:
                        old_vm.is_active = False
                        logger.debug(f"  Deactivated standalone VM resource '{worker_vm['name']}' (now part of cluster)")
            
            # Create resource metadata
            metadata = {
                'cluster': cluster,
                'folder_id': folder_id,
                'folder_name': folder_name,
                'cloud_id': cloud_id,
                'master_version': master_version,
                'master_zone': master_zone,
                'total_nodes': total_nodes,
                'total_vcpus': total_vcpus,
                'total_ram_gb': total_ram_gb,
                'total_storage_gb': total_storage_gb,
                'node_groups': node_groups,
                'created_at': cluster.get('createdAt'),
                'estimated_cost': True,
                # Cost breakdown
                'cost_breakdown': {
                    'master': round(master_daily_cost, 2),
                    'workers': round(worker_vms_cost, 2),
                    'storage': round(csi_volumes_cost, 2),
                    'total': round(estimated_daily_cost, 2)
                },
                'csi_volumes': csi_volumes_list,
                'csi_volumes_count': csi_volumes_count,
                'worker_vms': worker_vms_list,
                'worker_vms_count': worker_vms_count,
                'note': f'Total cost includes master ({master_daily_cost:.2f}₽), {worker_vms_count} worker VM(s) ({worker_vms_cost:.2f}₽), and {csi_volumes_count} CSI volume(s) ({csi_volumes_cost:.2f}₽). All components are aggregated for complete cluster cost tracking.'
            }
            
            resource = self._create_resource(
                resource_type='kubernetes-cluster',
                resource_id=cluster_id,
                name=cluster_name,
                metadata=metadata,
                sync_snapshot_id=sync_snapshot_id,
                region=master_zone,
                service_name='Managed Kubernetes'
            )
            
            if resource:
                resource.daily_cost = estimated_daily_cost
                resource.effective_cost = estimated_daily_cost
                resource.original_cost = estimated_daily_cost * 30
                resource.currency = 'RUB'
                resource.add_tag('folder_id', folder_id)
                resource.add_tag('folder_name', folder_name)
                resource.add_tag('cloud_id', cloud_id)
                resource.add_tag('cost_source', 'estimated')
                resource.add_tag('master_version', master_version)
                resource.add_tag('total_nodes', str(total_nodes))
                resource.add_tag('total_vcpus', str(total_vcpus))
                resource.add_tag('total_ram_gb', str(round(total_ram_gb, 2)))
            
            return resource
            
        except Exception as e:
            logger.error(f"Error processing Kubernetes cluster {cluster.get('id')}: {e}")
            return None
    
    def _process_postgresql_cluster(self, cluster: Dict, folder_id: str, 
                                  folder_name: str, cloud_id: str,
                                  sync_snapshot_id: int) -> Optional[Resource]:
        """
        Process PostgreSQL cluster resource
        
        Args:
            cluster: Cluster data from API
            folder_id: Folder ID
            folder_name: Folder name
            cloud_id: Cloud ID
            sync_snapshot_id: Sync snapshot ID
        
        Returns:
            Resource instance or None
        """
        try:
            cluster_id = cluster['id']
            cluster_name = cluster.get('name', cluster_id)
            
            # Extract version from config key (e.g., "postgresqlConfig_14" -> "14")
            config = cluster.get('config', {})
            version = 'unknown'
            for key in config.keys():
                if 'postgresqlConfig_' in key:
                    version = key.split('_')[1]
                    break
            
            # Get host specifications
            hosts = cluster.get('hosts', [])
            total_vcpus = 0
            total_ram_gb = 0
            total_storage_gb = 0
            disk_type = 'network-hdd'  # Default
            
            for host in hosts:
                resources = host.get('resources', {})
                
                # Parse resourcePresetId (e.g., "c3-c2-m4" = class3-2vCPU-4GB)
                preset_id = resources.get('resourcePresetId', '')
                if preset_id and '-' in preset_id:
                    parts = preset_id.split('-')
                    # Skip first "c" (class), find second "c" (vCPUs)
                    c_parts = [p for p in parts if p.startswith('c') and len(p) > 1 and p[1:].isdigit()]
                    vcpus_part = c_parts[1] if len(c_parts) > 1 else (c_parts[0] if c_parts else 'c2')
                    vcpus = int(vcpus_part[1:]) if len(vcpus_part) > 1 else 2
                    # Extract RAM from "m4" = 4 GB
                    ram_part = next((p for p in parts if p.startswith('m') and p[1:].isdigit()), 'm4')
                    ram_gb = int(ram_part[1:]) if len(ram_part) > 1 else 4
                else:
                    vcpus = 2
                    ram_gb = 4
                
                # Parse disk size (in bytes) and type
                disk_size_bytes = int(resources.get('diskSize', 0))
                disk_size_gb = disk_size_bytes / (1024**3)
                disk_type = resources.get('diskTypeId', 'network-hdd')
                
                total_vcpus += vcpus
                total_ram_gb += ram_gb
                total_storage_gb += disk_size_gb
            
            # Estimate daily cost with disk type
            estimated_daily_cost = self._estimate_database_cluster_cost(
                total_vcpus, total_ram_gb, total_storage_gb, 'postgresql', disk_type
            )
            
            # Create resource metadata
            metadata = {
                'cluster': cluster,
                'folder_id': folder_id,
                'folder_name': folder_name,
                'cloud_id': cloud_id,
                'version': version,
                'total_hosts': len(hosts),
                'total_vcpus': total_vcpus,
                'total_ram_gb': total_ram_gb,
                'total_storage_gb': total_storage_gb,
                'created_at': cluster.get('createdAt'),
                'estimated_cost': True
            }
            
            resource = self._create_resource(
                resource_type='postgresql-cluster',
                resource_id=cluster_id,
                name=cluster_name,
                metadata=metadata,
                sync_snapshot_id=sync_snapshot_id,
                region=hosts[0].get('zoneId', 'unknown') if hosts else 'unknown',
                service_name='Managed PostgreSQL'
            )
            
            if resource:
                resource.daily_cost = estimated_daily_cost
                resource.effective_cost = estimated_daily_cost
                resource.original_cost = estimated_daily_cost * 30
                resource.currency = 'RUB'
                resource.add_tag('folder_id', folder_id)
                resource.add_tag('folder_name', folder_name)
                resource.add_tag('cloud_id', cloud_id)
                resource.add_tag('cost_source', 'estimated')
                resource.add_tag('version', version)
                resource.add_tag('total_hosts', str(len(hosts)))
                resource.add_tag('total_vcpus', str(total_vcpus))
                resource.add_tag('total_ram_gb', str(round(total_ram_gb, 2)))
            
            return resource
            
        except Exception as e:
            logger.error(f"Error processing PostgreSQL cluster {cluster.get('id')}: {e}")
            return None
    
    def _process_mysql_cluster(self, cluster: Dict, folder_id: str, 
                              folder_name: str, cloud_id: str,
                              sync_snapshot_id: int) -> Optional[Resource]:
        """
        Process MySQL cluster resource
        
        Args:
            cluster: Cluster data from API
            folder_id: Folder ID
            folder_name: Folder name
            cloud_id: Cloud ID
            sync_snapshot_id: Sync snapshot ID
        
        Returns:
            Resource instance or None
        """
        try:
            cluster_id = cluster['id']
            cluster_name = cluster.get('name', cluster_id)
            
            # Extract version from config key (e.g., "mysqlConfig_8_0" -> "8.0")
            config = cluster.get('config', {})
            version = 'unknown'
            for key in config.keys():
                if 'mysqlConfig_' in key:
                    version = key.replace('mysqlConfig_', '').replace('_', '.')
                    break
            
            # Get host specifications
            hosts = cluster.get('hosts', [])
            total_vcpus = 0
            total_ram_gb = 0
            total_storage_gb = 0
            
            for host in hosts:
                resources = host.get('resources', {})
                
                # Parse resourcePresetId (e.g., "c3-c2-m4" = class3-2vCPU-4GB)
                preset_id = resources.get('resourcePresetId', '')
                if preset_id and '-' in preset_id:
                    parts = preset_id.split('-')
                    # Skip first "c" (class), find second "c" (vCPUs)
                    c_parts = [p for p in parts if p.startswith('c') and len(p) > 1 and p[1:].isdigit()]
                    vcpus_part = c_parts[1] if len(c_parts) > 1 else (c_parts[0] if c_parts else 'c2')
                    vcpus = int(vcpus_part[1:]) if len(vcpus_part) > 1 else 2
                    # Extract RAM from "m4" = 4 GB
                    ram_part = next((p for p in parts if p.startswith('m') and p[1:].isdigit()), 'm4')
                    ram_gb = int(ram_part[1:]) if len(ram_part) > 1 else 4
                else:
                    vcpus = 2
                    ram_gb = 4
                
                # Parse disk size (in bytes)
                disk_size_bytes = int(resources.get('diskSize', 0))
                disk_size_gb = disk_size_bytes / (1024**3)
                
                total_vcpus += vcpus
                total_ram_gb += ram_gb
                total_storage_gb += disk_size_gb
            
            # Estimate daily cost
            estimated_daily_cost = self._estimate_database_cluster_cost(
                total_vcpus, total_ram_gb, total_storage_gb, 'mysql'
            )
            
            # Create resource metadata
            metadata = {
                'cluster': cluster,
                'folder_id': folder_id,
                'folder_name': folder_name,
                'cloud_id': cloud_id,
                'version': version,
                'total_hosts': len(hosts),
                'total_vcpus': total_vcpus,
                'total_ram_gb': total_ram_gb,
                'total_storage_gb': total_storage_gb,
                'created_at': cluster.get('createdAt'),
                'estimated_cost': True
            }
            
            resource = self._create_resource(
                resource_type='mysql-cluster',
                resource_id=cluster_id,
                name=cluster_name,
                metadata=metadata,
                sync_snapshot_id=sync_snapshot_id,
                region=hosts[0].get('zoneId', 'unknown') if hosts else 'unknown',
                service_name='Managed MySQL'
            )
            
            if resource:
                resource.daily_cost = estimated_daily_cost
                resource.effective_cost = estimated_daily_cost
                resource.original_cost = estimated_daily_cost * 30
                resource.currency = 'RUB'
                resource.add_tag('folder_id', folder_id)
                resource.add_tag('folder_name', folder_name)
                resource.add_tag('cloud_id', cloud_id)
                resource.add_tag('cost_source', 'estimated')
                resource.add_tag('version', version)
                resource.add_tag('total_hosts', str(len(hosts)))
                resource.add_tag('total_vcpus', str(total_vcpus))
                resource.add_tag('total_ram_gb', str(round(total_ram_gb, 2)))
            
            return resource
            
        except Exception as e:
            logger.error(f"Error processing MySQL cluster {cluster.get('id')}: {e}")
            return None
    
    def _process_kafka_cluster(self, cluster: Dict, folder_id: str, 
                              folder_name: str, cloud_id: str,
                              sync_snapshot_id: int) -> Optional[Resource]:
        """
        Process Kafka cluster resource
        
        Args:
            cluster: Cluster data from API
            folder_id: Folder ID
            folder_name: Folder name
            cloud_id: Cloud ID
            sync_snapshot_id: Sync snapshot ID
        
        Returns:
            Resource instance or None
        """
        try:
            cluster_id = cluster['id']
            cluster_name = cluster.get('name', cluster_id)
            
            # Extract version from config
            config = cluster.get('config', {})
            version = config.get('version', 'unknown')
            
            # Get host specifications
            hosts = cluster.get('hosts', [])
            total_vcpus = 0
            total_ram_gb = 0
            total_storage_gb = 0
            disk_type = 'network-hdd'  # Default
            has_public_ip = False
            
            for host in hosts:
                resources = host.get('resources', {})
                
                # Parse resourcePresetId (e.g., "c3-c2-m4" = class3-2vCPU-4GB)
                preset_id = resources.get('resourcePresetId', '')
                if preset_id and '-' in preset_id:
                    parts = preset_id.split('-')
                    # Skip first "c" (class), find second "c" (vCPUs)
                    c_parts = [p for p in parts if p.startswith('c') and len(p) > 1 and p[1:].isdigit()]
                    vcpus_part = c_parts[1] if len(c_parts) > 1 else (c_parts[0] if c_parts else 'c2')
                    vcpus = int(vcpus_part[1:]) if len(vcpus_part) > 1 else 2
                    # Extract RAM from "m4" = 4 GB
                    ram_part = next((p for p in parts if p.startswith('m') and p[1:].isdigit()), 'm4')
                    ram_gb = int(ram_part[1:]) if len(ram_part) > 1 else 4
                else:
                    vcpus = 2
                    ram_gb = 4
                
                # Parse disk size (in bytes) and type
                disk_size_bytes = int(resources.get('diskSize', 0))
                disk_size_gb = disk_size_bytes / (1024**3)
                disk_type = resources.get('diskTypeId', 'network-hdd')
                
                total_vcpus += vcpus
                total_ram_gb += ram_gb
                total_storage_gb += disk_size_gb
                
                # Check for public IP assignment
                if host.get('assignPublicIp', False):
                    has_public_ip = True
            
            # Estimate daily cost with disk type
            estimated_daily_cost = self._estimate_database_cluster_cost(
                total_vcpus, total_ram_gb, total_storage_gb, 'kafka', disk_type
            )
            
            # Add public IP cost if cluster has one
            if has_public_ip:
                from app.providers.yandex.pricing import YandexPricing
                estimated_daily_cost += YandexPricing.KAFKA_PRICING['public_ip_per_day']
            
            # Create resource metadata
            metadata = {
                'cluster': cluster,
                'folder_id': folder_id,
                'folder_name': folder_name,
                'cloud_id': cloud_id,
                'version': version,
                'total_hosts': len(hosts),
                'total_vcpus': total_vcpus,
                'total_ram_gb': total_ram_gb,
                'total_storage_gb': total_storage_gb,
                'has_public_ip': has_public_ip,
                'created_at': cluster.get('createdAt'),
                'estimated_cost': True
            }
            
            resource = self._create_resource(
                resource_type='kafka-cluster',
                resource_id=cluster_id,
                name=cluster_name,
                metadata=metadata,
                sync_snapshot_id=sync_snapshot_id,
                region=hosts[0].get('zoneId', 'unknown') if hosts else 'unknown',
                service_name='Managed Kafka'
            )
            
            if resource:
                resource.daily_cost = estimated_daily_cost
                resource.effective_cost = estimated_daily_cost
                resource.original_cost = estimated_daily_cost * 30
                resource.currency = 'RUB'
                resource.add_tag('folder_id', folder_id)
                resource.add_tag('folder_name', folder_name)
                resource.add_tag('cloud_id', cloud_id)
                resource.add_tag('cost_source', 'har_based')
                resource.add_tag('version', version)
                resource.add_tag('total_hosts', str(len(hosts)))
                resource.add_tag('total_vcpus', str(total_vcpus))
                resource.add_tag('total_ram_gb', str(round(total_ram_gb, 2)))
                resource.add_tag('has_public_ip', str(has_public_ip))
            
            return resource
            
        except Exception as e:
            logger.error(f"Error processing Kafka cluster {cluster.get('id')}: {e}")
            return None
    
    def _process_managed_cluster(self, cluster: Dict, service_type: str,
                                folder_id: str, folder_name: str, cloud_id: str,
                                sync_snapshot_id: int) -> Optional[Resource]:
        """
        Process generic managed cluster resource (MongoDB, ClickHouse, Redis)
        
        Args:
            cluster: Cluster data from API
            service_type: Type of service (mongodb, clickhouse, redis)
            folder_id: Folder ID
            folder_name: Folder name
            cloud_id: Cloud ID
            sync_snapshot_id: Sync snapshot ID
        
        Returns:
            Resource instance or None
        """
        try:
            cluster_id = cluster['id']
            cluster_name = cluster.get('name', cluster_id)
            
            # Extract cluster specifications
            config = cluster.get('config', {})
            version = 'unknown'
            
            # Get version from config based on service type
            if service_type == 'mongodb':
                mongodb_config = config.get('mongodbConfig', {})
                version = mongodb_config.get('version', 'unknown')
            elif service_type == 'clickhouse':
                clickhouse_config = config.get('clickhouseConfig', {})
                version = clickhouse_config.get('version', 'unknown')
            elif service_type == 'redis':
                redis_config = config.get('redisConfig', {})
                version = redis_config.get('version', 'unknown')
            
            # Get host specifications
            hosts = cluster.get('hosts', [])
            total_vcpus = 0
            total_ram_gb = 0
            total_storage_gb = 0
            
            for host in hosts:
                resources = host.get('resources', {})
                vcpus = int(resources.get('resourcePresetId', '0').split('-')[-1]) if '-' in resources.get('resourcePresetId', '') else 2
                ram_bytes = int(resources.get('diskSize', 0)) * (1024**3)
                ram_gb = ram_bytes / (1024**3)
                disk_size_gb = int(resources.get('diskSize', 0))
                
                total_vcpus += vcpus
                total_ram_gb += ram_gb
                total_storage_gb += disk_size_gb
            
            # Estimate daily cost
            estimated_daily_cost = self._estimate_database_cluster_cost(
                total_vcpus, total_ram_gb, total_storage_gb, service_type
            )
            
            # Create resource metadata
            metadata = {
                'cluster': cluster,
                'folder_id': folder_id,
                'folder_name': folder_name,
                'cloud_id': cloud_id,
                'version': version,
                'total_hosts': len(hosts),
                'total_vcpus': total_vcpus,
                'total_ram_gb': total_ram_gb,
                'total_storage_gb': total_storage_gb,
                'created_at': cluster.get('createdAt'),
                'estimated_cost': True
            }
            
            resource = self._create_resource(
                resource_type=f'{service_type}-cluster',
                resource_id=cluster_id,
                name=cluster_name,
                metadata=metadata,
                sync_snapshot_id=sync_snapshot_id,
                region=hosts[0].get('zoneId', 'unknown') if hosts else 'unknown',
                service_name=f'Managed {service_type.title()}'
            )
            
            if resource:
                resource.daily_cost = estimated_daily_cost
                resource.effective_cost = estimated_daily_cost
                resource.original_cost = estimated_daily_cost * 30
                resource.currency = 'RUB'
                resource.add_tag('folder_id', folder_id)
                resource.add_tag('folder_name', folder_name)
                resource.add_tag('cloud_id', cloud_id)
                resource.add_tag('cost_source', 'estimated')
                resource.add_tag('version', version)
                resource.add_tag('total_hosts', str(len(hosts)))
                resource.add_tag('total_vcpus', str(total_vcpus))
                resource.add_tag('total_ram_gb', str(round(total_ram_gb, 2)))
            
            return resource
            
        except Exception as e:
            logger.error(f"Error processing {service_type} cluster {cluster.get('id')}: {e}")
            return None
    
    def _estimate_kubernetes_cluster_cost(self, total_vcpus: int, total_ram_gb: float, 
                                         total_storage_gb: float, zone_id: str) -> float:
        """
        Calculate Kubernetes cluster cost (MASTER ONLY)
        
        According to Yandex billing behavior:
        - "Managed Service for Kubernetes" = Master node cost only (~228 ₽/day)
        - "Compute Cloud" = Worker node VMs (billed as regular VMs)
        
        So this method only returns the master cost, not worker nodes.
        Worker nodes are processed as regular server resources.
        """
        # Kubernetes master cost (regional master)
        # From real billing: ~228 ₽/day
        # Documented: ~3500 ₽/month = ~115 ₽/day (but real is ~228 ₽)
        # Using real observed cost
        master_daily_cost = 228.0
        
        return master_daily_cost
    
    def _estimate_database_cluster_cost(self, total_vcpus: int, total_ram_gb: float, 
                                       total_storage_gb: float, db_type: str, disk_type: str = 'network-hdd') -> float:
        """
        Calculate database cluster cost using SKU-based or HAR-based pricing
        
        For PostgreSQL, uses HAR-derived pricing for maximum accuracy.
        For other databases, uses SKU-based pricing with fallback to documented pricing.
        """
        # Try SKU-based pricing first
        sku_cost = YandexSKUPricing.calculate_cluster_cost(
            total_vcpus=total_vcpus,
            total_ram_gb=total_ram_gb,
            total_storage_gb=total_storage_gb,
            cluster_type=db_type,
            platform_id='standard-v3'
        )
        
        if sku_cost and sku_cost.get('accuracy') == 'sku_based':
            return sku_cost['daily_cost']
        
        # Fallback to documented pricing (with HAR-based pricing for PostgreSQL)
        cost_data = YandexPricing.calculate_cluster_cost(
            total_vcpus=total_vcpus,
            total_ram_gb=total_ram_gb,
            total_storage_gb=total_storage_gb,
            cluster_type=db_type,
            platform_id='standard-v3',
            disk_type=disk_type
        )
        
        return cost_data['daily_cost']

