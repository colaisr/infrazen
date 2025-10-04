"""
Comprehensive sync service for handling resource synchronization with snapshots
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from app.core.models import db
from app.core.models.provider import CloudProvider
from app.core.models.resource import Resource
from app.core.models.sync import SyncSnapshot, ResourceState
from app.providers.beget.client import BegetAPIClient

logger = logging.getLogger(__name__)

class SyncService:
    """Service for handling comprehensive resource synchronization"""
    
    def __init__(self, provider_id: int):
        self.provider_id = provider_id
        self.provider = CloudProvider.query.get(provider_id)
        if not self.provider:
            raise ValueError(f"Provider with ID {provider_id} not found")
        
        # Initialize provider client
        credentials = self.provider.get_credentials()
        if self.provider.provider_type == 'beget':
            self.client = BegetAPIClient(
                credentials.get('username'),
                credentials.get('password'),
                credentials.get('api_url', 'https://api.beget.com')
            )
        else:
            raise ValueError(f"Unsupported provider type: {self.provider.provider_type}")
    
    def create_sync_snapshot(self, sync_type: str = 'manual') -> SyncSnapshot:
        """Create a new sync snapshot"""
        snapshot = SyncSnapshot(
            provider_id=self.provider_id,
            sync_type=sync_type,
            sync_status='running',
            sync_started_at=datetime.utcnow()
        )
        
        # Set sync configuration
        sync_config = {
            'sync_type': sync_type,
            'provider_type': self.provider.provider_type,
            'connection_name': self.provider.connection_name,
            'sync_timestamp': datetime.utcnow().isoformat()
        }
        snapshot.set_sync_config(sync_config)
        
        db.session.add(snapshot)
        db.session.commit()
        
        logger.info(f"Created sync snapshot {snapshot.id} for provider {self.provider_id}")
        return snapshot
    
    def sync_resources(self, sync_type: str = 'manual') -> Dict:
        """Perform comprehensive resource synchronization with dual endpoints"""
        try:
            logger.info(f"Starting dual-endpoint sync for provider {self.provider_id}")
            
            # Create sync snapshot
            snapshot = self.create_sync_snapshot(sync_type)
            
            # Authenticate with provider
            if not self.client.authenticate():
                snapshot.mark_completed('error', 'Authentication failed')
                db.session.commit()
                return {'success': False, 'error': 'Authentication failed'}
            
            # Use the new dual-endpoint sync method
            sync_result = self.client.sync_resources()
            
            # Process the sync result with separate error handling
            return self._process_dual_endpoint_sync(sync_result, snapshot)
            
        except Exception as e:
            logger.error(f"Sync failed for provider {self.provider_id}: {e}")
            if 'snapshot' in locals():
                snapshot.mark_completed('error', str(e))
                db.session.commit()
            return {'success': False, 'error': str(e)}
    
    def _process_dual_endpoint_sync(self, sync_result: Dict, snapshot: SyncSnapshot) -> Dict:
        """Process sync result from dual endpoints with separate error handling"""
        try:
            logger.info("Processing dual-endpoint sync result")
            
            sync_errors = []
            total_resources = 0
            
            # Process Account Sync
            if sync_result.get('account_sync', {}).get('status') == 'success':
                logger.info("Processing account sync data")
                account_data = sync_result['account_sync']
                
                # Update provider metadata with account info
                if 'account_info' in account_data:
                    self._update_provider_metadata(account_data['account_info'])
                
                # Process domains
                if 'domains' in account_data:
                    domain_count = self._process_domains(snapshot, account_data['domains'])
                    total_resources += domain_count
                    logger.info(f"Processed {domain_count} domains from account sync")
                else:
                    logger.warning("No domains data in account sync")
            else:
                error_msg = sync_result.get('account_sync', {}).get('error', 'Account sync failed')
                sync_errors.append(f"Account sync: {error_msg}")
                logger.error(f"Account sync failed: {error_msg}")
            
            # Process VPS Sync
            if sync_result.get('vps_sync', {}).get('status') == 'success':
                logger.info("Processing VPS sync data")
                vps_data = sync_result['vps_sync']
                
                # Process VPS servers
                if 'vps_servers' in vps_data:
                    vps_count = self._process_vps_servers(snapshot, vps_data['vps_servers'])
                    total_resources += vps_count
                    logger.info(f"Processed {vps_count} VPS servers from VPS sync")
                else:
                    logger.warning("No VPS servers data in VPS sync")
                
                # Process CPU statistics
                if 'cpu_statistics' in vps_data:
                    cpu_count = self._process_vps_cpu_statistics(snapshot, vps_data['cpu_statistics'])
                    logger.info(f"Processed CPU statistics for {cpu_count} VPS servers")
                else:
                    logger.warning("No CPU statistics data in VPS sync")
                
                # Process memory statistics
                if 'memory_statistics' in vps_data:
                    memory_count = self._process_vps_memory_statistics(snapshot, vps_data['memory_statistics'])
                    logger.info(f"Processed memory statistics for {memory_count} VPS servers")
                else:
                    logger.warning("No memory statistics data in VPS sync")
            else:
                error_msg = sync_result.get('vps_sync', {}).get('error', 'VPS sync failed')
                sync_errors.append(f"VPS sync: {error_msg}")
                logger.error(f"VPS sync failed: {error_msg}")
            
            # Process Cloud Services Sync
            if sync_result.get('cloud_sync', {}).get('status') == 'success':
                logger.info("Processing cloud services sync data")
                cloud_data = sync_result['cloud_sync']
                
                # Process cloud services
                if 'cloud_services' in cloud_data:
                    cloud_count = self._process_cloud_services(snapshot, cloud_data['cloud_services'])
                    total_resources += cloud_count
                    logger.info(f"Processed {cloud_count} cloud services from cloud sync")
                else:
                    logger.warning("No cloud services data in cloud sync")
            else:
                error_msg = sync_result.get('cloud_sync', {}).get('error', 'Cloud services sync failed')
                sync_errors.append(f"Cloud services sync: {error_msg}")
                logger.error(f"Cloud services sync failed: {error_msg}")
            
            # Process Additional Resources Sync
            if sync_result.get('domains_sync', {}).get('status') == 'success':
                logger.info("Processing additional resources sync data")
                additional_data = sync_result['domains_sync']
                
                # Process databases, FTP, email accounts (if available and methods exist)
                additional_count = 0
                if 'databases' in additional_data and hasattr(self, '_process_databases'):
                    try:
                        additional_count += self._process_databases(snapshot, additional_data['databases'])
                    except Exception as e:
                        logger.warning(f"Database processing not available: {e}")
                elif 'databases' in additional_data:
                    logger.info("Database processing skipped - method not implemented")
                
                if 'ftp_accounts' in additional_data and hasattr(self, '_process_ftp_accounts'):
                    try:
                        additional_count += self._process_ftp_accounts(snapshot, additional_data['ftp_accounts'])
                    except Exception as e:
                        logger.warning(f"FTP processing not available: {e}")
                elif 'ftp_accounts' in additional_data:
                    logger.info("FTP processing skipped - method not implemented")
                
                if 'email_accounts' in additional_data and hasattr(self, '_process_email_accounts'):
                    try:
                        additional_count += self._process_email_accounts(snapshot, additional_data['email_accounts'])
                    except Exception as e:
                        logger.warning(f"Email processing not available: {e}")
                elif 'email_accounts' in additional_data:
                    logger.info("Email processing skipped - method not implemented")
                
                total_resources += additional_count
                logger.info(f"Processed {additional_count} additional resources")
            else:
                error_msg = sync_result.get('domains_sync', {}).get('error', 'Additional resources sync failed')
                sync_errors.append(f"Additional resources sync: {error_msg}")
                logger.error(f"Additional resources sync failed: {error_msg}")
            
            # Determine overall sync status
            if sync_errors:
                sync_status = 'partial_success' if total_resources > 0 else 'error'
                sync_message = f'Sync completed with {len(sync_errors)} errors: {total_resources} resources processed'
            else:
                sync_status = 'success'
                sync_message = f'Sync completed successfully: {total_resources} resources processed'
            
            # Update snapshot with results
            snapshot.mark_completed(sync_status, sync_message)
            
            # Update provider sync status
            self.provider.last_sync = datetime.utcnow()
            self.provider.sync_status = sync_status
            if sync_errors:
                self.provider.sync_error = '; '.join(sync_errors)
            else:
                self.provider.sync_error = None
            
            db.session.commit()
            
            logger.info(f"Sync completed: {sync_status}, {total_resources} resources, {len(sync_errors)} errors")
            
            return {
                'success': sync_status in ['success', 'partial_success'],
                'status': sync_status,
                'message': sync_message,
                'total_resources': total_resources,
                'errors': sync_errors,
                'snapshot_id': snapshot.id
            }
            
        except Exception as e:
            logger.error(f"Error processing dual-endpoint sync: {e}")
            snapshot.mark_completed('error', f'Processing failed: {str(e)}')
            db.session.commit()
            return {'success': False, 'error': f'Processing failed: {str(e)}'}
    
    def _process_vps_servers(self, snapshot: SyncSnapshot, vps_servers: List[Dict]) -> int:
        """Process VPS servers from new API"""
        processed_count = 0
        
        for vps in vps_servers:
            try:
                # Create or update VPS resource
                resource = self._create_or_update_resource(
                    resource_id=vps.get('id'),
                    resource_name=vps.get('name'),
                    resource_type='VPS',
                    service_name='Compute',
                    region=vps.get('region', 'unknown'),
                    status=vps.get('status', 'unknown'),
                    provider_config=vps
                )
                
                # Set cost information
                if vps.get('daily_cost'):
                    resource.set_daily_cost_baseline(
                        original_cost=vps.get('daily_cost'),
                        period='daily',
                        frequency='recurring'
                    )
                
                # Add VPS-specific tags
                self._add_resource_tags(resource, {
                    'vps_id': vps.get('id'),
                    'ip_address': vps.get('ip_address'),
                    'hostname': vps.get('hostname'),
                    'cpu_cores': str(vps.get('cpu_cores', 0)),
                    'ram_mb': str(vps.get('ram_mb', 0)),
                    'disk_gb': str(vps.get('disk_gb', 0)),
                    'software': vps.get('software', ''),
                    'software_version': vps.get('software_version', ''),
                    'ssh_access': str(vps.get('ssh_access_allowed', False)),
                    'region': vps.get('region', 'unknown'),
                    'created_at': vps.get('date_create', ''),
                    'disk_used_gb': str(vps.get('disk_used_gb', 0)),
                    'disk_left_gb': str(vps.get('disk_left_gb', 0)),
                    'bandwidth_gb': str(vps.get('bandwidth_gb', 0))
                })
                
                # Add software-specific tags if available
                if vps.get('software') and isinstance(vps.get('software'), dict):
                    software = vps.get('software', {})
                    self._add_resource_tags(resource, {
                        'software_name': software.get('name', ''),
                        'software_display_name': software.get('display_name', ''),
                        'software_version': software.get('version', ''),
                        'software_url': software.get('address', ''),
                        'software_status': software.get('status', ''),
                        'software_description': software.get('description', '')
                    })
                    
                    # Add admin credentials if available
                    if software.get('field_value'):
                        for field in software.get('field_value', []):
                            if field.get('variable') == 'beget_n8n_password':
                                self._add_resource_tags(resource, {
                                    'admin_password': field.get('value', '')
                                })
                            elif field.get('variable') == 'beget_email':
                                self._add_resource_tags(resource, {
                                    'admin_email': field.get('value', '')
                                })
                            elif field.get('variable') == 'beget_fqdn':
                                self._add_resource_tags(resource, {
                                    'software_domain': field.get('value', '')
                                })
                elif vps.get('software'):
                    # Handle case where software is a string (from old processing)
                    self._add_resource_tags(resource, {
                        'software_name': vps.get('software', ''),
                        'software_version': vps.get('software_version', ''),
                        'software_url': vps.get('software_url', '')
                    })
                
                # Create resource state
                self._create_resource_state(snapshot, resource, vps)
                
                processed_count += 1
                logger.debug(f"Processed VPS: {vps.get('name')}")
                
            except Exception as e:
                logger.error(f"Error processing VPS {vps.get('name', 'unknown')}: {e}")
                continue
        
        return processed_count
    
    def _process_vps_cpu_statistics(self, snapshot: SyncSnapshot, cpu_statistics: Dict) -> int:
        """Process CPU statistics for VPS servers"""
        processed_count = 0
        
        try:
            cpu_data = cpu_statistics.get('cpu_statistics', {})
            
            for vps_id, vps_cpu_data in cpu_data.items():
                try:
                    vps_name = vps_cpu_data.get('vps_name', 'Unknown')
                    cpu_stats = vps_cpu_data.get('cpu_statistics', {})
                    
                    if not cpu_stats:
                        logger.warning(f"No CPU statistics for VPS {vps_name}")
                        continue
                    
                    # Find the corresponding VPS resource
                    vps_resource = Resource.query.filter_by(
                        resource_id=vps_id,
                        resource_type='VPS'
                    ).first()
                    
                    if not vps_resource:
                        logger.warning(f"VPS resource not found for ID {vps_id}")
                        continue
                    
                    # Add CPU performance tags to the VPS resource
                    self._add_resource_tags(vps_resource, {
                        'cpu_avg_usage': str(cpu_stats.get('avg_cpu_usage', 0)),
                        'cpu_max_usage': str(cpu_stats.get('max_cpu_usage', 0)),
                        'cpu_min_usage': str(cpu_stats.get('min_cpu_usage', 0)),
                        'cpu_trend': str(cpu_stats.get('trend', 0)),
                        'cpu_performance_tier': cpu_stats.get('performance_tier', 'unknown'),
                        'cpu_data_points': str(cpu_stats.get('data_points', 0)),
                        'cpu_period': cpu_stats.get('period', 'HOUR'),
                        'cpu_collection_timestamp': cpu_stats.get('collection_timestamp', '')
                    })
                    
                    # Store raw CPU data in the snapshot
                    snapshot_data = {
                        'vps_id': vps_id,
                        'vps_name': vps_name,
                        'cpu_statistics': cpu_stats,
                        'collection_timestamp': cpu_stats.get('collection_timestamp', '')
                    }
                    
                    # Store in snapshot metadata
                    if not snapshot.metadata:
                        snapshot.metadata = {}
                    
                    if 'vps_cpu_statistics' not in snapshot.metadata:
                        snapshot.metadata['vps_cpu_statistics'] = {}
                    
                    snapshot.metadata['vps_cpu_statistics'][vps_id] = snapshot_data
                    
                    processed_count += 1
                    logger.debug(f"Processed CPU statistics for VPS: {vps_name}")
                    
                except Exception as e:
                    logger.error(f"Error processing CPU statistics for VPS {vps_id}: {e}")
                    continue
            
            # Update snapshot with CPU statistics summary
            if not snapshot.metadata:
                snapshot.metadata = {}
            
            snapshot.metadata['cpu_statistics_summary'] = {
                'total_vps': cpu_statistics.get('total_vps', 0),
                'vps_with_cpu_data': cpu_statistics.get('vps_with_cpu_data', 0),
                'period': cpu_statistics.get('period', 'HOUR'),
                'collection_timestamp': cpu_statistics.get('collection_timestamp', '')
            }
            
        except Exception as e:
            logger.error(f"Error processing VPS CPU statistics: {e}")
        
        return processed_count
    
    def _process_vps_memory_statistics(self, snapshot: SyncSnapshot, memory_statistics: Dict) -> int:
        """Process memory statistics for VPS servers"""
        processed_count = 0
        
        try:
            memory_data = memory_statistics.get('memory_statistics', {})
            
            for vps_id, vps_memory_data in memory_data.items():
                try:
                    vps_name = vps_memory_data.get('vps_name', 'Unknown')
                    memory_stats = vps_memory_data.get('memory_statistics', {})
                    
                    if not memory_stats:
                        logger.warning(f"No memory statistics for VPS {vps_name}")
                        continue
                    
                    # Find the corresponding VPS resource
                    vps_resource = Resource.query.filter_by(
                        resource_id=vps_id,
                        resource_type='VPS'
                    ).first()
                    
                    if not vps_resource:
                        logger.warning(f"VPS resource not found for ID {vps_id}")
                        continue
                    
                    # Add memory performance tags to the VPS resource
                    self._add_resource_tags(vps_resource, {
                        'memory_avg_usage_mb': str(memory_stats.get('avg_memory_usage_mb', 0)),
                        'memory_max_usage_mb': str(memory_stats.get('max_memory_usage_mb', 0)),
                        'memory_min_usage_mb': str(memory_stats.get('min_memory_usage_mb', 0)),
                        'memory_usage_percent': str(memory_stats.get('memory_usage_percent', 0)),
                        'memory_trend': str(memory_stats.get('trend', 0)),
                        'memory_tier': memory_stats.get('memory_tier', 'unknown'),
                        'memory_data_points': str(memory_stats.get('data_points', 0)),
                        'memory_period': memory_stats.get('period', 'HOUR'),
                        'memory_collection_timestamp': memory_stats.get('collection_timestamp', '')
                    })
                    
                    # Store raw memory data in the snapshot
                    snapshot_data = {
                        'vps_id': vps_id,
                        'vps_name': vps_name,
                        'memory_statistics': memory_stats,
                        'collection_timestamp': memory_stats.get('collection_timestamp', '')
                    }
                    
                    # Store in snapshot metadata
                    if not snapshot.metadata:
                        snapshot.metadata = {}
                    
                    if 'vps_memory_statistics' not in snapshot.metadata:
                        snapshot.metadata['vps_memory_statistics'] = {}
                    
                    snapshot.metadata['vps_memory_statistics'][vps_id] = snapshot_data
                    
                    processed_count += 1
                    logger.debug(f"Processed memory statistics for VPS: {vps_name}")
                    
                except Exception as e:
                    logger.error(f"Error processing memory statistics for VPS {vps_id}: {e}")
                    continue
            
            # Update snapshot with memory statistics summary
            if not snapshot.metadata:
                snapshot.metadata = {}
            
            snapshot.metadata['memory_statistics_summary'] = {
                'total_vps': memory_statistics.get('total_vps', 0),
                'vps_with_memory_data': memory_statistics.get('vps_with_memory_data', 0),
                'period': memory_statistics.get('period', 'HOUR'),
                'collection_timestamp': memory_statistics.get('collection_timestamp', '')
            }
            
        except Exception as e:
            logger.error(f"Error processing VPS memory statistics: {e}")
        
        return processed_count
    
    def _process_cloud_services(self, snapshot: SyncSnapshot, cloud_services: List[Dict]) -> int:
        """Process cloud services from cloud API"""
        processed_count = 0
        
        for service in cloud_services:
            try:
                # Create or update cloud service resource
                resource = self._create_or_update_resource(
                    resource_id=service.get('id'),
                    resource_name=service.get('name'),
                    resource_type=service.get('type'),
                    service_name=service.get('service_type', 'Cloud'),
                    region=service.get('region', 'unknown'),
                    status=service.get('status', 'unknown'),
                    provider_config=service
                )
                
                # Set cost information
                if service.get('daily_cost'):
                    resource.set_daily_cost_baseline(
                        original_cost=service.get('daily_cost'),
                        period='daily',
                        frequency='recurring'
                    )
                elif service.get('monthly_cost'):
                    resource.set_daily_cost_baseline(
                        original_cost=service.get('monthly_cost'),
                        period='monthly',
                        frequency='recurring'
                    )
                
                # Add cloud service-specific tags
                self._add_resource_tags(resource, {
                    'cloud_service_id': service.get('id'),
                    'service_type': service.get('type'),
                    'region': service.get('region', 'unknown'),
                    'created_at': service.get('created_at', ''),
                    'manage_enabled': str(service.get('manage_enabled', False))
                })
                
                # Add service-specific configuration tags
                if service.get('type') == 'MySQL Database':
                    mysql_config = service.get('mysql_config', {})
                    self._add_resource_tags(resource, {
                        'mysql_version': mysql_config.get('version', ''),
                        'mysql_host': mysql_config.get('host', ''),
                        'mysql_port': str(mysql_config.get('port', 3306)),
                        'mysql_cpu_count': str(mysql_config.get('cpu_count', 0)),
                        'mysql_memory_mb': str(mysql_config.get('memory_mb', 0)),
                        'mysql_disk_size_mb': str(mysql_config.get('disk_size_mb', 0)),
                        'mysql_disk_used_bytes': str(mysql_config.get('disk_used_bytes', 0)),
                        'mysql_disk_left_bytes': str(mysql_config.get('disk_left_bytes', 0)),
                        'mysql_pma_url': mysql_config.get('pma_url', ''),
                        'mysql_read_only': str(mysql_config.get('read_only', False))
                    })
                elif service.get('type') == 'S3 Storage':
                    s3_config = service.get('s3_config', {})
                    self._add_resource_tags(resource, {
                        's3_public': str(s3_config.get('public', False)),
                        's3_access_key': s3_config.get('access_key', ''),
                        's3_fqdn': s3_config.get('fqdn', ''),
                        's3_quota_used_size': str(s3_config.get('quota_used_size', 0)),
                        's3_ftp_enabled': str(bool(s3_config.get('ftp', {}).get('status') == 'ENABLED')),
                        's3_sftp_enabled': str(bool(s3_config.get('sftp', {}).get('status') == 'ENABLED'))
                    })
                
                # Create resource state
                self._create_resource_state(snapshot, resource, service)
                
                processed_count += 1
                logger.debug(f"Processed cloud service: {service.get('name')}")
                
            except Exception as e:
                logger.error(f"Error processing cloud service {service.get('name', 'unknown')}: {e}")
                continue
        
        return processed_count
    
    def _process_domains(self, snapshot: SyncSnapshot, domains: List[Dict]) -> int:
        """Process domains from account sync"""
        processed_count = 0
        
        for domain in domains:
            try:
                # Get domain name from the correct field
                domain_name = domain.get('name', domain.get('domain', domain.get('fqdn', 'unknown')))
                
                # Create or update domain resource
                resource = self._create_or_update_resource(
                    resource_id=domain.get('id', domain_name),
                    resource_name=domain_name,
                    resource_type='Domain',
                    service_name='DNS',
                    region='global',
                    status=domain.get('status', 'active'),
                    provider_config=domain
                )
                
                # Add domain-specific tags
                self._add_resource_tags(resource, {
                    'domain_name': domain_name,
                    'domain_id': domain.get('id'),
                    'status': domain.get('status', 'active'),
                    'expiry_date': domain.get('expiry_date', ''),
                    'auto_renew': str(domain.get('auto_renew', False))
                })
                
                # Create resource state
                self._create_resource_state(snapshot, resource, domain)
                
                processed_count += 1
                logger.debug(f"Processed domain: {domain.get('domain')}")
                
            except Exception as e:
                logger.error(f"Error processing domain {domain.get('domain', 'unknown')}: {e}")
                continue
        
        return processed_count
    
    def _process_resources(self, snapshot: SyncSnapshot, resources_data: Dict) -> Dict:
        """Process and store resources from provider data"""
        try:
            # Get existing resources for this provider
            existing_resources = {
                f"{r.provider_id}_{r.resource_id}_{r.resource_type}": r 
                for r in Resource.query.filter_by(provider_id=self.provider_id).all()
            }
            
            sync_result = {
                'total_resources': 0,
                'resources_created': 0,
                'resources_updated': 0,
                'resources_unchanged': 0,
                'resources_deleted': 0,
                'total_monthly_cost': 0.0,
                'resources_by_type': {},
                'resources_by_status': {}
            }
            
            # Process each resource type
            resource_types = ['vps_servers', 'domains', 'databases', 'ftp_accounts', 'email_accounts']
            
            for resource_type in resource_types:
                resources = resources_data.get(resource_type, [])
                sync_result['total_resources'] += len(resources)
                
                for resource_data in resources:
                    # Create unified resource data
                    unified_resource = self._create_unified_resource(resource_data, resource_type)
                    
                    # Check if resource exists
                    resource_key = f"{self.provider_id}_{unified_resource['resource_id']}_{unified_resource['resource_type']}"
                    existing_resource = existing_resources.get(resource_key)
                    
                    if existing_resource:
                        # Update existing resource
                        resource_state = self._update_existing_resource(
                            snapshot, existing_resource, unified_resource
                        )
                        if resource_state.state_action == 'updated':
                            sync_result['resources_updated'] += 1
                        else:
                            sync_result['resources_unchanged'] += 1
                    else:
                        # Create new resource
                        new_resource = self._create_new_resource(snapshot, unified_resource)
                        sync_result['resources_created'] += 1
                    
                    # Update statistics
                    sync_result['total_monthly_cost'] += unified_resource.get('effective_cost', 0)
                    
                    # Track by type and status
                    resource_type_name = unified_resource.get('resource_type', 'Unknown')
                    resource_status = unified_resource.get('status', 'unknown')
                    
                    sync_result['resources_by_type'][resource_type_name] = \
                        sync_result['resources_by_type'].get(resource_type_name, 0) + 1
                    sync_result['resources_by_status'][resource_status] = \
                        sync_result['resources_by_status'].get(resource_status, 0) + 1
            
            # Handle deleted resources (resources that exist in DB but not in current sync)
            current_resource_keys = set()
            for resource_type in resource_types:
                for resource_data in resources_data.get(resource_type, []):
                    unified_resource = self._create_unified_resource(resource_data, resource_type)
                    resource_key = f"{self.provider_id}_{unified_resource['resource_id']}_{unified_resource['resource_type']}"
                    current_resource_keys.add(resource_key)
            
            for resource_key, existing_resource in existing_resources.items():
                if resource_key not in current_resource_keys:
                    # Resource was deleted
                    self._mark_resource_deleted(snapshot, existing_resource)
                    sync_result['resources_deleted'] += 1
            
            return sync_result
            
        except Exception as e:
            logger.error(f"Error processing resources: {e}")
            raise
    
    def _create_unified_resource(self, resource_data: Dict, resource_type: str) -> Dict:
        """Create unified resource data from provider-specific data"""
        # Map resource type to service name
        service_mapping = {
            'vps_servers': 'Compute',
            'domains': 'Domain',
            'databases': 'Database',
            'ftp_accounts': 'Storage',
            'email_accounts': 'Email'
        }
        
        # Extract common fields
        unified = {
            'resource_id': str(resource_data.get('id', resource_data.get('server_id', ''))),
            'resource_name': resource_data.get('name', resource_data.get('domain', '')),
            'resource_type': resource_data.get('type', resource_type.replace('_', ' ').title()),
            'service_name': service_mapping.get(resource_type, 'Unknown'),
            'region': resource_data.get('region', 'default'),
            'status': resource_data.get('status', 'active'),
            'effective_cost': resource_data.get('monthly_cost', 0.0),
            'currency': resource_data.get('currency', 'RUB'),
            'billing_period': 'monthly',
            'provider_config': resource_data
        }
        
        return unified
    
    def _create_new_resource(self, snapshot: SyncSnapshot, unified_resource: Dict) -> Resource:
        """Create a new resource and resource state"""
        # Create resource
        resource = Resource(
            provider_id=self.provider_id,
            resource_id=unified_resource['resource_id'],
            resource_name=unified_resource['resource_name'],
            region=unified_resource['region'],
            service_name=unified_resource['service_name'],
            resource_type=unified_resource['resource_type'],
            status=unified_resource['status'],
            effective_cost=unified_resource['effective_cost'],
            currency=unified_resource['currency'],
            billing_period=unified_resource['billing_period'],
            last_sync=datetime.utcnow(),
            is_active=True
        )
        
        # Set daily cost baseline for FinOps analysis
        provider_config = unified_resource.get('provider_config', {})
        daily_cost = provider_config.get('daily_cost', 0)
        monthly_cost = provider_config.get('monthly_cost', 0)
        
        if daily_cost > 0:
            # Use daily price when available
            resource.set_daily_cost_baseline(daily_cost, 'daily', 'recurring')
        elif monthly_cost > 0:
            # Convert monthly to daily
            resource.set_daily_cost_baseline(monthly_cost, 'monthly', 'recurring')
        else:
            # Use effective_cost as fallback
            resource.set_daily_cost_baseline(unified_resource['effective_cost'], 'monthly', 'recurring')
        
        # Set provider-specific configuration
        resource.set_provider_config(unified_resource['provider_config'])
        
        db.session.add(resource)
        db.session.flush()  # Get the ID
        
        # Create resource state
        resource_state = ResourceState(
            sync_snapshot_id=snapshot.id,
            resource_id=resource.id,
            provider_resource_id=unified_resource['resource_id'],
            resource_type=unified_resource['resource_type'],
            resource_name=unified_resource['resource_name'],
            state_action='created',
            service_name=unified_resource['service_name'],
            region=unified_resource['region'],
            status=unified_resource['status'],
            effective_cost=unified_resource['effective_cost']
        )
        
        # Set current state as JSON
        resource_state.set_current_state(unified_resource)
        
        db.session.add(resource_state)
        
        return resource
    
    def _update_existing_resource(self, snapshot: SyncSnapshot, existing_resource: Resource, unified_resource: Dict) -> ResourceState:
        """Update existing resource and create resource state"""
        # Get previous state
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
            existing_resource.resource_name = unified_resource['resource_name']
            existing_resource.status = unified_resource['status']
            existing_resource.effective_cost = unified_resource['effective_cost']
            existing_resource.region = unified_resource['region']
            existing_resource.last_sync = datetime.utcnow()
            existing_resource.set_provider_config(unified_resource['provider_config'])
            
            # Update daily cost baseline
            provider_config = unified_resource.get('provider_config', {})
            daily_cost = provider_config.get('daily_cost', 0)
            monthly_cost = provider_config.get('monthly_cost', 0)
            
            if daily_cost > 0:
                existing_resource.set_daily_cost_baseline(daily_cost, 'daily', 'recurring')
            elif monthly_cost > 0:
                existing_resource.set_daily_cost_baseline(monthly_cost, 'monthly', 'recurring')
            else:
                existing_resource.set_daily_cost_baseline(unified_resource['effective_cost'], 'monthly', 'recurring')
        
        # Create resource state
        resource_state = ResourceState(
            sync_snapshot_id=snapshot.id,
            resource_id=existing_resource.id,
            provider_resource_id=unified_resource['resource_id'],
            resource_type=unified_resource['resource_type'],
            resource_name=unified_resource['resource_name'],
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
        
        return resource_state
    
    def _mark_resource_deleted(self, snapshot: SyncSnapshot, resource: Resource):
        """Mark resource as deleted and create resource state"""
        # Mark resource as inactive
        resource.is_active = False
        resource.status = 'deleted'
        resource.last_sync = datetime.utcnow()
        
        # Create resource state
        resource_state = ResourceState(
            sync_snapshot_id=snapshot.id,
            resource_id=resource.id,
            provider_resource_id=resource.resource_id,
            resource_type=resource.resource_type,
            resource_name=resource.resource_name,
            state_action='deleted',
            service_name=resource.service_name,
            region=resource.region,
            status='deleted',
            effective_cost=0.0
        )
        
        # Set previous and current states as JSON
        resource_state.set_previous_state(resource.to_dict())
        resource_state.set_current_state({'status': 'deleted', 'is_active': False})
        
        db.session.add(resource_state)
    
    def _update_provider_metadata(self, account_info: Dict):
        """Update provider metadata with account information"""
        try:
            import json
            
            # Get current metadata or create new
            current_metadata = {}
            if self.provider.provider_metadata:
                try:
                    current_metadata = json.loads(self.provider.provider_metadata)
                except (json.JSONDecodeError, TypeError):
                    current_metadata = {}
            
            # Update with account information
            current_metadata.update({
                'account_info': account_info,
                'last_account_update': datetime.utcnow().isoformat(),
                'account_status': account_info.get('account_status', 'unknown'),
                'balance': account_info.get('balance', 0),
                'currency': account_info.get('currency', 'RUB'),
                'service_limits': account_info.get('service_limits', {}),
                'usage_stats': account_info.get('usage_stats', {}),
                'security': account_info.get('security', {})
            })
            
            # Store updated metadata
            self.provider.provider_metadata = json.dumps(current_metadata)
            db.session.add(self.provider)
            db.session.commit()
            
            logger.info(f"Updated provider metadata for provider {self.provider_id}")
            
        except Exception as e:
            logger.error(f"Failed to update provider metadata: {e}")
    
    def _update_snapshot_stats(self, snapshot: SyncSnapshot, sync_result: Dict):
        """Update snapshot with sync statistics"""
        snapshot.total_resources_found = sync_result['total_resources']
        snapshot.resources_created = sync_result['resources_created']
        snapshot.resources_updated = sync_result['resources_updated']
        snapshot.resources_deleted = sync_result['resources_deleted']
        snapshot.resources_unchanged = sync_result['resources_unchanged']
        snapshot.total_monthly_cost = sync_result['total_monthly_cost']
        snapshot.set_total_resources_by_type(sync_result['resources_by_type'])
        snapshot.set_total_resources_by_status(sync_result['resources_by_status'])
    
    def _create_or_update_resource(self, resource_id: str, resource_name: str, resource_type: str, 
                                  service_name: str, region: str, status: str, provider_config: Dict) -> Resource:
        """Create or update a resource"""
        # Serialize provider_config to JSON string
        import json
        provider_config_json = json.dumps(provider_config) if provider_config else None
        
        # Check if resource already exists
        existing_resource = Resource.query.filter_by(
            provider_id=self.provider_id,
            resource_id=resource_id,
            resource_type=resource_type
        ).first()
        
        if existing_resource:
            # Update existing resource
            existing_resource.resource_name = resource_name
            existing_resource.service_name = service_name
            existing_resource.region = region
            existing_resource.status = status
            existing_resource.provider_config = provider_config_json
            existing_resource.updated_at = datetime.utcnow()
            return existing_resource
        else:
            # Create new resource
            new_resource = Resource(
                provider_id=self.provider_id,
                resource_id=resource_id,
                resource_name=resource_name,
                resource_type=resource_type,
                service_name=service_name,
                region=region,
                status=status,
                provider_config=provider_config_json
            )
            db.session.add(new_resource)
            return new_resource
    
    def _add_resource_tags(self, resource: Resource, tags: Dict):
        """Add tags to a resource"""
        for key, value in tags.items():
            if value:  # Only add non-empty tags
                resource.add_tag(key, str(value))
    
    def _create_resource_state(self, snapshot: SyncSnapshot, resource: Resource, data: Dict):
        """Create a resource state for tracking changes"""
        # Serialize data to JSON string
        import json
        data_json = json.dumps(data) if data else None
        
        resource_state = ResourceState(
            sync_snapshot_id=snapshot.id,
            resource_id=resource.id,
            provider_resource_id=resource.resource_id,
            resource_type=resource.resource_type,
            resource_name=resource.resource_name,
            state_action='created',
            status=resource.status,
            effective_cost=resource.effective_cost,
            service_name=resource.service_name,
            region=resource.region
        )
        db.session.add(resource_state)
    
    def get_sync_history(self, limit: int = 10) -> List[Dict]:
        """Get sync history for this provider"""
        snapshots = SyncSnapshot.query.filter_by(provider_id=self.provider_id)\
            .order_by(SyncSnapshot.sync_started_at.desc())\
            .limit(limit).all()
        
        return [snapshot.to_dict() for snapshot in snapshots]
    
    def get_latest_snapshot(self) -> Optional[SyncSnapshot]:
        """Get the latest sync snapshot for this provider"""
        return SyncSnapshot.query.filter_by(provider_id=self.provider_id)\
            .order_by(SyncSnapshot.sync_started_at.desc())\
            .first()
