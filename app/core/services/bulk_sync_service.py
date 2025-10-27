"""
Bulk Sync Service for orchestrating synchronization across all active users
"""
import logging
from datetime import datetime
from typing import Dict, List
from app.core.models import db
from app.core.models.user import User
from app.core.services.complete_sync_service import CompleteSyncService

logger = logging.getLogger(__name__)

class BulkSyncService:
    """
    Service for managing bulk sync operations across all active users
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def get_eligible_users(self) -> List[User]:
        """
        Get all active users eligible for bulk sync (excludes demo users)
        
        Returns:
            List of User instances
        """
        users = User.query.filter(
            User.is_active == True,
            User.role != 'demouser'
        ).order_by(User.id).all()
        
        self.logger.info(f"Found {len(users)} eligible users for bulk sync")
        return users
    
    def sync_all_users(self, sync_type: str = 'scheduled') -> Dict[str, any]:
        """
        Execute synchronization for all active users (excluding demo users)
        
        Args:
            sync_type: Type of sync (scheduled, manual, api)
            
        Returns:
            Dict containing bulk sync results with detailed per-user results
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Starting bulk sync for all active users (type: {sync_type})")
            
            # Get eligible users
            eligible_users = self.get_eligible_users()
            
            if not eligible_users:
                self.logger.warning("No eligible users found for bulk sync")
                return {
                    'success': True,
                    'message': 'No eligible users found for synchronization',
                    'total_users': 0,
                    'successful_users': 0,
                    'failed_users': 0,
                    'skipped_users': 0,
                    'user_results': [],
                    'duration_seconds': 0
                }
            
            # Initialize counters
            successful_users = 0
            failed_users = 0
            skipped_users = 0
            user_results = []
            
            # Process each user sequentially
            for idx, user in enumerate(eligible_users, 1):
                user_start_time = datetime.now()
                
                self.logger.info(f"Processing user {idx}/{len(eligible_users)}: {user.email} (ID: {user.id})")
                
                try:
                    # Create sync service for user
                    sync_service = CompleteSyncService(user.id)
                    
                    # Get user's providers to check if sync is needed
                    providers = sync_service.get_user_providers()
                    
                    if not providers:
                        self.logger.info(f"User {user.email} has no auto-sync enabled providers, skipping")
                        skipped_users += 1
                        user_results.append({
                            'user_id': user.id,
                            'user_email': user.email,
                            'status': 'skipped',
                            'reason': 'No auto-sync enabled providers',
                            'duration_seconds': 0
                        })
                        continue
                    
                    # Execute sync
                    self.logger.info(f"Starting sync for user {user.email} with {len(providers)} providers")
                    sync_result = sync_service.start_complete_sync(sync_type=sync_type)
                    
                    user_duration = (datetime.now() - user_start_time).total_seconds()
                    
                    if sync_result.get('success'):
                        successful_users += 1
                        user_results.append({
                            'user_id': user.id,
                            'user_email': user.email,
                            'status': 'success',
                            'complete_sync_id': sync_result.get('complete_sync_id'),
                            'sync_status': sync_result.get('sync_status'),
                            'providers_synced': sync_result.get('total_providers_synced'),
                            'successful_providers': sync_result.get('successful_providers'),
                            'failed_providers': sync_result.get('failed_providers'),
                            'resources_found': sync_result.get('total_resources_found'),
                            'total_daily_cost': sync_result.get('total_daily_cost'),
                            'duration_seconds': user_duration
                        })
                        self.logger.info(
                            f"✓ User {user.email} sync completed: "
                            f"{sync_result.get('successful_providers')}/{sync_result.get('total_providers_synced')} providers, "
                            f"{sync_result.get('total_resources_found')} resources, "
                            f"{user_duration:.1f}s"
                        )
                    else:
                        failed_users += 1
                        user_results.append({
                            'user_id': user.id,
                            'user_email': user.email,
                            'status': 'failed',
                            'error': sync_result.get('error', 'Unknown error'),
                            'message': sync_result.get('message'),
                            'duration_seconds': user_duration
                        })
                        self.logger.error(f"✗ User {user.email} sync failed: {sync_result.get('error')}")
                
                except Exception as e:
                    failed_users += 1
                    user_duration = (datetime.now() - user_start_time).total_seconds()
                    user_results.append({
                        'user_id': user.id,
                        'user_email': user.email,
                        'status': 'error',
                        'error': str(e),
                        'duration_seconds': user_duration
                    })
                    self.logger.error(f"✗ User {user.email} sync exception: {e}", exc_info=True)
            
            # Calculate total duration
            total_duration = (datetime.now() - start_time).total_seconds()
            
            # Prepare summary
            summary = {
                'success': True,
                'message': f'Bulk sync completed: {successful_users} successful, {failed_users} failed, {skipped_users} skipped',
                'total_users': len(eligible_users),
                'successful_users': successful_users,
                'failed_users': failed_users,
                'skipped_users': skipped_users,
                'user_results': user_results,
                'duration_seconds': total_duration,
                'sync_type': sync_type,
                'started_at': start_time.isoformat(),
                'completed_at': datetime.now().isoformat()
            }
            
            self.logger.info(
                f"Bulk sync completed in {total_duration:.1f}s: "
                f"{successful_users} successful, {failed_users} failed, {skipped_users} skipped "
                f"out of {len(eligible_users)} users"
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
    
    def sync_specific_users(self, user_ids: List[int], sync_type: str = 'manual') -> Dict[str, any]:
        """
        Execute synchronization for specific users by ID
        
        Args:
            user_ids: List of user IDs to sync
            sync_type: Type of sync (scheduled, manual, api)
            
        Returns:
            Dict containing sync results for specified users
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Starting sync for {len(user_ids)} specific users")
            
            # Get users
            users = User.query.filter(
                User.id.in_(user_ids),
                User.is_active == True,
                User.role != 'demouser'
            ).all()
            
            if not users:
                return {
                    'success': False,
                    'error': 'No eligible users found',
                    'message': 'None of the specified users are eligible for sync'
                }
            
            successful_users = 0
            failed_users = 0
            skipped_users = 0
            user_results = []
            
            # Process each user
            for user in users:
                try:
                    sync_service = CompleteSyncService(user.id)
                    providers = sync_service.get_user_providers()
                    
                    if not providers:
                        skipped_users += 1
                        user_results.append({
                            'user_id': user.id,
                            'user_email': user.email,
                            'status': 'skipped',
                            'reason': 'No auto-sync enabled providers'
                        })
                        continue
                    
                    sync_result = sync_service.start_complete_sync(sync_type=sync_type)
                    
                    if sync_result.get('success'):
                        successful_users += 1
                        user_results.append({
                            'user_id': user.id,
                            'user_email': user.email,
                            'status': 'success',
                            'complete_sync_id': sync_result.get('complete_sync_id')
                        })
                    else:
                        failed_users += 1
                        user_results.append({
                            'user_id': user.id,
                            'user_email': user.email,
                            'status': 'failed',
                            'error': sync_result.get('error')
                        })
                
                except Exception as e:
                    failed_users += 1
                    user_results.append({
                        'user_id': user.id,
                        'user_email': user.email,
                        'status': 'error',
                        'error': str(e)
                    })
            
            total_duration = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'message': f'Sync completed for {len(users)} users',
                'total_users': len(users),
                'successful_users': successful_users,
                'failed_users': failed_users,
                'skipped_users': skipped_users,
                'user_results': user_results,
                'duration_seconds': total_duration
            }
            
        except Exception as e:
            self.logger.error(f"Specific user sync failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': 'Sync failed for specific users'
            }






