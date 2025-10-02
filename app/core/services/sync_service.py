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
        """Perform comprehensive resource synchronization"""
        try:
            logger.info(f"Starting sync for provider {self.provider_id}")
            
            # Create sync snapshot
            snapshot = self.create_sync_snapshot(sync_type)
            
            # Authenticate with provider
            if not self.client.authenticate():
                snapshot.mark_completed('error', 'Authentication failed')
                db.session.commit()
                return {'success': False, 'error': 'Authentication failed'}
            
            # Get all resources from provider
            resources_data = self.client.get_all_resources()
            
            # Process and store resources
            sync_result = self._process_resources(snapshot, resources_data)
            
            # Update snapshot with results
            self._update_snapshot_stats(snapshot, sync_result)
            
            # Mark sync as completed
            snapshot.mark_completed('success')
            
            # Update provider sync status
            self.provider.last_sync = datetime.utcnow()
            self.provider.sync_status = 'success'
            self.provider.sync_error = None
            
            db.session.commit()
            
            logger.info(f"Sync completed successfully for provider {self.provider_id}")
            return {
                'success': True,
                'snapshot_id': snapshot.id,
                'sync_result': sync_result,
                'message': f'Successfully synced {sync_result["total_resources"]} resources'
            }
            
        except Exception as e:
            logger.error(f"Sync failed for provider {self.provider_id}: {e}")
            
            # Update snapshot with error
            if 'snapshot' in locals():
                snapshot.mark_completed('error', str(e))
                db.session.commit()
            
            # Update provider sync status
            self.provider.sync_status = 'error'
            self.provider.sync_error = str(e)
            db.session.commit()
            
            return {'success': False, 'error': str(e)}
    
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
