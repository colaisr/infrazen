"""
Bulk Sync Service for orchestrating synchronization across all organizations
"""
import logging
from datetime import datetime
from typing import Dict, List
from app.core.models import db
from app.core.models.organization import Organization
from app.core.models.provider import CloudProvider
from app.core.services.complete_sync_service import CompleteSyncService

logger = logging.getLogger(__name__)

class BulkSyncService:
    """
    Service for managing bulk sync operations across all organizations
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def get_eligible_organizations(self) -> List[Organization]:
        """
        Get all organizations that have auto-sync enabled providers
        Excludes demo organizations (organizations with demo users or demo in name)
        
        Returns:
            List of Organization instances
        """
        from app.core.models.organization_member import OrganizationMember
        from app.core.models.user import User
        
        # Get organizations that have at least one auto-sync enabled provider
        # Exclude demo organizations (ID 3 or organizations with demo users)
        organizations = Organization.query.join(CloudProvider).filter(
            CloudProvider.organization_id == Organization.id,
            CloudProvider.auto_sync == True,
            CloudProvider.is_active == True,
            CloudProvider.is_deleted == False,
            # Exclude demo organization (ID 3) and organizations with "Demo" in name
            Organization.id != 3,
            ~Organization.name.like('%Demo%'),
            ~Organization.name.like('%demo%')
        ).distinct().order_by(Organization.id).all()
        
        # Additional filter: exclude organizations where all members are demo users
        eligible_orgs = []
        for org in organizations:
            # Check if organization has any non-demo members
            # Use explicit join condition to avoid ambiguity
            has_non_demo_member = OrganizationMember.query.join(
                User, OrganizationMember.user_id == User.id
            ).filter(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.is_active == True,
                User.role != 'demouser'
            ).first() is not None
            
            if has_non_demo_member:
                eligible_orgs.append(org)
            else:
                self.logger.info(f"Excluding organization {org.id} ({org.name}) - all members are demo users")
        
        self.logger.info(f"Found {len(eligible_orgs)} eligible organizations with auto-sync enabled providers (excluded demo organizations)")
        return eligible_orgs
    
    def get_eligible_users(self) -> List:
        """
        DEPRECATED: Use get_eligible_organizations() instead.
        Kept for backward compatibility.
        """
        return self.get_eligible_organizations()
    
    def sync_all_organizations(self, sync_type: str = 'scheduled') -> Dict[str, any]:
        """
        Execute synchronization for all organizations with auto-sync enabled providers
        
        Args:
            sync_type: Type of sync (scheduled, manual, api)
            
        Returns:
            Dict containing bulk sync results with detailed per-organization results
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Starting bulk sync for all organizations (type: {sync_type})")
            
            # Get eligible organizations
            eligible_orgs = self.get_eligible_organizations()
            
            if not eligible_orgs:
                self.logger.warning("No eligible organizations found for bulk sync")
                return {
                    'success': True,
                    'message': 'No eligible organizations found for synchronization',
                    'total_organizations': 0,
                    'successful_organizations': 0,
                    'failed_organizations': 0,
                    'skipped_organizations': 0,
                    'organization_results': [],
                    'duration_seconds': 0
                }
            
            # Complete sync calls db.session.remove() / commits that expire or detach ORM objects.
            # Capture ids/names now so later loop iterations never touch detached Organization rows.
            org_jobs = [(o.id, o.name) for o in eligible_orgs]
            
            # Initialize counters
            successful_orgs = 0
            failed_orgs = 0
            skipped_orgs = 0
            org_results = []
            
            # Process each organization sequentially
            for idx, (org_id, org_name) in enumerate(org_jobs, 1):
                org_start_time = datetime.now()
                
                self.logger.info(f"Processing organization {idx}/{len(org_jobs)}: {org_name} (ID: {org_id})")
                
                try:
                    # Create sync service for organization
                    sync_service = CompleteSyncService(org_id)
                    
                    # Get organization's providers to check if sync is needed
                    providers = sync_service.get_organization_providers()
                    
                    if not providers:
                        self.logger.info(f"Organization {org_name} has no auto-sync enabled providers, skipping")
                        skipped_orgs += 1
                        org_results.append({
                            'organization_id': org_id,
                            'organization_name': org_name,
                            'status': 'skipped',
                            'reason': 'No auto-sync enabled providers',
                            'duration_seconds': 0
                        })
                        continue
                    
                    # Execute sync
                    self.logger.info(f"Starting sync for organization {org_name} with {len(providers)} providers")
                    sync_result = sync_service.start_complete_sync(sync_type=sync_type)
                    
                    org_duration = (datetime.now() - org_start_time).total_seconds()
                    
                    if sync_result.get('success'):
                        successful_orgs += 1
                        org_results.append({
                            'organization_id': org_id,
                            'organization_name': org_name,
                            'status': 'success',
                            'complete_sync_id': sync_result.get('complete_sync_id'),
                            'sync_status': sync_result.get('sync_status'),
                            'providers_synced': sync_result.get('total_providers_synced'),
                            'successful_providers': sync_result.get('successful_providers'),
                            'failed_providers': sync_result.get('failed_providers'),
                            'resources_found': sync_result.get('total_resources_found'),
                            'total_daily_cost': sync_result.get('total_daily_cost'),
                            'duration_seconds': org_duration
                        })
                        self.logger.info(
                            f"✓ Organization {org_name} sync completed: "
                            f"{sync_result.get('successful_providers')}/{sync_result.get('total_providers_synced')} providers, "
                            f"{sync_result.get('total_resources_found')} resources, "
                            f"{org_duration:.1f}s"
                        )
                    else:
                        failed_orgs += 1
                        org_results.append({
                            'organization_id': org_id,
                            'organization_name': org_name,
                            'status': 'failed',
                            'error': sync_result.get('error', 'Unknown error'),
                            'message': sync_result.get('message'),
                            'duration_seconds': org_duration
                        })
                        self.logger.error(f"✗ Organization {org_name} sync failed: {sync_result.get('error')}")
                
                except Exception as e:
                    failed_orgs += 1
                    org_duration = (datetime.now() - org_start_time).total_seconds()
                    org_results.append({
                        'organization_id': org_id,
                        'organization_name': org_name,
                        'status': 'error',
                        'error': str(e),
                        'duration_seconds': org_duration
                    })
                    self.logger.error(f"✗ Organization {org_name} sync exception: {e}", exc_info=True)
            
            # Calculate total duration
            total_duration = (datetime.now() - start_time).total_seconds()
            
            # Prepare summary
            summary = {
                'success': True,
                'message': f'Bulk sync completed: {successful_orgs} successful, {failed_orgs} failed, {skipped_orgs} skipped',
                'total_organizations': len(org_jobs),
                'successful_organizations': successful_orgs,
                'failed_organizations': failed_orgs,
                'skipped_organizations': skipped_orgs,
                'organization_results': org_results,
                'duration_seconds': total_duration,
                'sync_type': sync_type,
                'started_at': start_time.isoformat(),
                'completed_at': datetime.now().isoformat()
            }
            
            self.logger.info(
                f"Bulk sync completed in {total_duration:.1f}s: "
                f"{successful_orgs} successful, {failed_orgs} failed, {skipped_orgs} skipped "
                f"out of {len(org_jobs)} organizations"
            )
            
            return summary
            
        except Exception as e:
            total_duration = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Bulk sync failed with exception: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': 'Bulk sync failed due to system error',
                'duration_seconds': total_duration
            }
    
    def sync_all_users(self, sync_type: str = 'scheduled') -> Dict[str, any]:
        """
        DEPRECATED: Use sync_all_organizations() instead.
        Kept for backward compatibility - maps to sync_all_organizations().
        """
        result = self.sync_all_organizations(sync_type)
        # Map organization results to user results for backward compatibility
        if 'organization_results' in result:
            result['user_results'] = result.pop('organization_results')
        if 'total_organizations' in result:
            result['total_users'] = result.pop('total_organizations')
        if 'successful_organizations' in result:
            result['successful_users'] = result.pop('successful_organizations')
        if 'failed_organizations' in result:
            result['failed_users'] = result.pop('failed_organizations')
        if 'skipped_organizations' in result:
            result['skipped_users'] = result.pop('skipped_organizations')
        return result
    
    def sync_specific_organizations(self, organization_ids: List[int], sync_type: str = 'manual') -> Dict[str, any]:
        """
        Execute synchronization for specific organizations by ID
        
        Args:
            organization_ids: List of organization IDs to sync
            sync_type: Type of sync (scheduled, manual, api)
            
        Returns:
            Dict containing sync results for specified organizations
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Starting sync for {len(organization_ids)} specific organizations")
            
            # Get organizations
            orgs = Organization.query.filter(
                Organization.id.in_(organization_ids)
            ).all()
            
            if not orgs:
                return {
                    'success': False,
                    'error': 'No organizations found',
                    'message': 'None of the specified organizations exist'
                }
            
            successful_orgs = 0
            failed_orgs = 0
            skipped_orgs = 0
            org_results = []
            
            # Process each organization
            for org in orgs:
                try:
                    sync_service = CompleteSyncService(org.id)
                    providers = sync_service.get_organization_providers()
                    
                    if not providers:
                        skipped_orgs += 1
                        org_results.append({
                            'organization_id': org.id,
                            'organization_name': org.name,
                            'status': 'skipped',
                            'reason': 'No auto-sync enabled providers'
                        })
                        continue
                    
                    sync_result = sync_service.start_complete_sync(sync_type=sync_type)
                    
                    if sync_result.get('success'):
                        successful_orgs += 1
                        org_results.append({
                            'organization_id': org.id,
                            'organization_name': org.name,
                            'status': 'success',
                            'complete_sync_id': sync_result.get('complete_sync_id')
                        })
                    else:
                        failed_orgs += 1
                        org_results.append({
                            'organization_id': org.id,
                            'organization_name': org.name,
                            'status': 'failed',
                            'error': sync_result.get('error')
                        })
                
                except Exception as e:
                    failed_orgs += 1
                    org_results.append({
                        'organization_id': org.id,
                        'organization_name': org.name,
                        'status': 'error',
                        'error': str(e)
                    })
            
            total_duration = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'message': f'Sync completed for {len(orgs)} organizations',
                'total_organizations': len(orgs),
                'successful_organizations': successful_orgs,
                'failed_organizations': failed_orgs,
                'skipped_organizations': skipped_orgs,
                'organization_results': org_results,
                'duration_seconds': total_duration
            }
            
        except Exception as e:
            self.logger.error(f"Specific organization sync failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': 'Sync failed for specific organizations'
            }





















