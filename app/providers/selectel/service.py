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
        self.client = SelectelClient(
            api_key=self.credentials.get('api_key'),
            account_id=self.credentials.get('account_id'),
            service_username=self.credentials.get('service_username'),
            service_password=self.credentials.get('service_password')
        )
    
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
        Sync resources from Selectel API
        
        Returns:
            Dict containing sync results
        """
        try:
            # Create sync snapshot entry
            sync_snapshot = SyncSnapshot(
                provider_id=self.provider.id,
                sync_type='full',
                sync_status='running',
                sync_started_at=datetime.now()
            )
            db.session.add(sync_snapshot)
            db.session.commit()
            
            # Get all resources from API
            api_resources = self.client.get_all_resources()
            
            # Process and store resources
            synced_resources = []
            errors = []
            
            # Process account information
            if 'account' in api_resources:
                account_data = api_resources['account']
                account_resource = self._create_resource(
                    resource_type='account',
                    resource_id=account_data.get('account', {}).get('name', 'unknown'),
                    name=account_data.get('account', {}).get('name', 'Account'),
                    metadata=account_data,
                    sync_snapshot_id=sync_snapshot.id
                )
                if account_resource:
                    synced_resources.append(account_resource)
            
            # Process projects
            if 'projects' in api_resources:
                for project_data in api_resources['projects']:
                    project_resource = self._create_resource(
                        resource_type='project',
                        resource_id=project_data.get('id'),
                        name=project_data.get('name'),
                        metadata=project_data,
                        sync_snapshot_id=sync_snapshot.id
                    )
                    if project_resource:
                        synced_resources.append(project_resource)
            
            # Process users
            if 'users' in api_resources:
                for user_data in api_resources['users']:
                    user_resource = self._create_resource(
                        resource_type='user',
                        resource_id=user_data.get('id'),
                        name=user_data.get('name'),
                        metadata=user_data,
                        sync_snapshot_id=sync_snapshot.id
                    )
                    if user_resource:
                        synced_resources.append(user_resource)
            
            # Process roles
            if 'roles' in api_resources:
                for role_data in api_resources['roles']:
                    role_resource = self._create_resource(
                        resource_type='role',
                        resource_id=role_data.get('id'),
                        name=role_data.get('name'),
                        metadata=role_data,
                        sync_snapshot_id=sync_snapshot.id
                    )
                    if role_resource:
                        synced_resources.append(role_resource)
            
            # Process actual cloud resources - Servers (VMs with attached volumes)
            if 'servers' in api_resources:
                for server_data in api_resources['servers']:
                    # Extract complete VM information
                    server_resource = self._create_resource(
                        resource_type='server',
                        resource_id=server_data.get('id'),
                        name=server_data.get('name', f"Server {server_data.get('id', 'Unknown')}"),
                        metadata={
                            **server_data,
                            # Add computed fields for easy display
                            'vcpus': server_data.get('vcpus'),
                            'ram_mb': server_data.get('ram_mb'),
                            'flavor_name': server_data.get('flavor_name'),
                            'total_storage_gb': server_data.get('total_storage_gb'),
                            'ip_addresses': server_data.get('ip_addresses', []),
                            'attached_volumes': server_data.get('attached_volumes', []),
                            'network_interfaces': server_data.get('network_interfaces', [])
                        },
                        sync_snapshot_id=sync_snapshot.id,
                        region=server_data.get('region', 'ru-3'),
                        service_name='Compute'
                    )
                    if server_resource:
                        synced_resources.append(server_resource)
            
            # Note: Volumes and Networks are now integrated into server resources
            # No need to process them separately as they're part of each VM's metadata
            
            # Update sync snapshot
            sync_snapshot.sync_status = 'success'
            sync_snapshot.sync_completed_at = datetime.now()
            sync_snapshot.resources_created = len(synced_resources)
            sync_snapshot.resources_deleted = 0
            sync_snapshot.total_resources_found = len(synced_resources)
            sync_snapshot.calculate_duration()
            
            # Update provider last_sync timestamp
            self.provider.last_sync = datetime.now()
            self.provider.sync_status = 'success'
            self.provider.sync_error = None
            
            db.session.commit()
            
            return {
                'success': True,
                'resources_synced': len(synced_resources),
                'errors': len(errors),
                'sync_snapshot_id': sync_snapshot.id,
                'message': f'Successfully synced {len(synced_resources)} resources'
            }
            
        except Exception as e:
            logger.error(f"Selectel sync failed: {str(e)}")
            
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
            # Check if resource already exists
            existing_resource = Resource.query.filter_by(
                provider_id=self.provider.id,
                resource_type=resource_type,
                resource_id=resource_id
            ).first()
            
            # Create unified resource data
            unified_resource = {
                'resource_id': resource_id,
                'resource_name': name,
                'resource_type': resource_type,
                'service_name': service_name or ('Account' if resource_type == 'account' else resource_type.title()),
                'region': region or ('global' if resource_type == 'account' else 'unknown'),
                'status': 'active',
                'effective_cost': 0.0,
                'provider_config': metadata
            }
            
            if existing_resource:
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
