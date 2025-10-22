"""
Complete Sync Service for orchestrating synchronization across all user providers
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from app.core.models import db
from app.core.models.user import User
from app.core.models.provider import CloudProvider
from app.core.models.complete_sync import CompleteSync, ProviderSyncReference
from app.providers import sync_orchestrator
from app.core.recommendations.orchestrator import RecommendationOrchestrator
from flask import current_app

logger = logging.getLogger(__name__)

class CompleteSyncService:
    """
    Service for managing complete sync operations across all user providers
    """
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.user = User.query.get(user_id)
        if not self.user:
            raise ValueError(f"User with ID {user_id} not found")
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def start_complete_sync(self, sync_type: str = 'manual') -> Dict[str, any]:
        """
        Start a complete sync operation for all auto-sync enabled providers
        
        Args:
            sync_type: Type of sync (manual, scheduled, api)
            
        Returns:
            Dict containing sync results
        """
        try:
            self.logger.info(f"Starting complete sync for user {self.user_id}")
            
            # Get all auto-sync enabled providers for this user
            providers = self.get_user_providers()
            
            if not providers:
                return {
                    'success': False,
                    'error': 'No auto-sync enabled providers found',
                    'message': 'No providers configured for automatic synchronization'
                }
            
            # Create complete sync record
            complete_sync = CompleteSync(
                user_id=self.user_id,
                sync_type=sync_type,
                sync_status='running',
                sync_started_at=datetime.now()
            )
            
            # Set sync configuration
            sync_config = {
                'sync_type': sync_type,
                'user_id': self.user_id,
                'providers_count': len(providers),
                'sync_timestamp': datetime.now().isoformat(),
                'providers': [{'id': p.id, 'name': p.connection_name, 'type': p.provider_type} for p in providers]
            }
            complete_sync.set_sync_config(sync_config)
            
            db.session.add(complete_sync)
            db.session.commit()
            
            self.logger.info(f"Created complete sync {complete_sync.id} for {len(providers)} providers")
            
            # Execute sequential sync for each provider
            return self._execute_sequential_sync(complete_sync, providers)
            
        except Exception as e:
            self.logger.error(f"Complete sync failed for user {self.user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Complete sync failed due to system error'
            }
    
    def get_user_providers(self) -> List[CloudProvider]:
        """
        Get all auto-sync enabled providers for the user
        
        Returns:
            List of CloudProvider instances
        """
        return CloudProvider.query.filter_by(
            user_id=self.user_id,
            auto_sync=True,
            is_active=True
        ).order_by('created_at').all()
    
    def _execute_sequential_sync(self, complete_sync: CompleteSync, providers: List[CloudProvider]) -> Dict[str, any]:
        """
        Execute sequential sync for all providers
        
        Args:
            complete_sync: CompleteSync instance
            providers: List of providers to sync
            
        Returns:
            Dict containing sync results
        """
        try:
            total_cost = 0.0
            cost_by_provider = {}
            resources_by_provider = {}
            successful_providers = 0
            failed_providers = 0
            total_resources = 0
            provider_errors = []
            
            # Update complete sync with provider count
            complete_sync.total_providers_synced = len(providers)
            
            # Sync each provider sequentially
            for order, provider in enumerate(providers, 1):
                self.logger.info(f"Syncing provider {provider.id} ({provider.connection_name}) - {order}/{len(providers)}")
                
                # Create provider sync reference
                provider_ref = ProviderSyncReference(
                    complete_sync_id=complete_sync.id,
                    provider_id=provider.id,
                    sync_order=order,
                    sync_status='running'
                )
                
                try:
                    # Execute individual provider sync
                    sync_result = sync_orchestrator.sync_provider(provider.id, 'complete_sync')
                    
                    if sync_result['success']:
                        # Store reference to generated snapshot
                        provider_ref.sync_snapshot_id = sync_result['sync_snapshot_id']
                        provider_ref.sync_status = 'success'
                        provider_ref.resources_synced = sync_result['resources_synced']
                        provider_ref.provider_cost = sync_result.get('total_cost', 0.0)
                        provider_ref.sync_duration_seconds = sync_result.get('sync_duration_seconds', 0)
                        
                        # Aggregate costs
                        total_cost += provider_ref.provider_cost
                        cost_by_provider[provider.connection_name] = provider_ref.provider_cost
                        resources_by_provider[provider.connection_name] = provider_ref.resources_synced
                        total_resources += provider_ref.resources_synced
                        successful_providers += 1
                        
                        self.logger.info(f"Provider {provider.connection_name} synced successfully: {provider_ref.resources_synced} resources, {provider_ref.provider_cost} RUB")
                        
                    else:
                        # Handle sync failure
                        provider_ref.sync_status = 'error'
                        provider_ref.error_message = sync_result.get('error', 'Unknown error')
                        provider_ref.set_error_details(sync_result.get('errors', {}))
                        failed_providers += 1
                        provider_errors.append({
                            'provider': provider.connection_name,
                            'error': sync_result.get('error', 'Unknown error')
                        })
                        
                        self.logger.error(f"Provider {provider.connection_name} sync failed: {sync_result.get('error')}")
                
                except Exception as e:
                    # Handle unexpected errors
                    provider_ref.sync_status = 'error'
                    provider_ref.error_message = str(e)
                    provider_ref.set_error_details({'exception': str(e)})
                    failed_providers += 1
                    provider_errors.append({
                        'provider': provider.connection_name,
                        'error': str(e)
                    })
                    
                    self.logger.error(f"Provider {provider.connection_name} sync exception: {e}")
                
                # Add provider reference to database
                db.session.add(provider_ref)
            
            # Update complete sync with results
            complete_sync.successful_providers = successful_providers
            complete_sync.failed_providers = failed_providers
            complete_sync.total_resources_found = total_resources
            complete_sync.total_daily_cost = total_cost  # total_cost is already daily cost from individual syncs
            complete_sync.total_monthly_cost = total_cost * 30.0  # Convert daily to monthly
            complete_sync.set_cost_by_provider(cost_by_provider)
            complete_sync.set_resources_by_provider(resources_by_provider)
            
            # Determine final status
            if failed_providers == 0:
                complete_sync.sync_status = 'success'
                complete_sync.mark_completed('success')
            elif successful_providers == 0:
                complete_sync.sync_status = 'error'
                complete_sync.error_message = 'All provider syncs failed'
                complete_sync.set_error_details({'provider_errors': provider_errors})
                complete_sync.mark_completed('error', 'All provider syncs failed')
            else:
                complete_sync.sync_status = 'partial'
                complete_sync.error_message = f'{failed_providers} provider syncs failed'
                complete_sync.set_error_details({'provider_errors': provider_errors})
                complete_sync.mark_completed('partial', f'{failed_providers} provider syncs failed')
            
            db.session.commit()
            
            # Prepare response
            response = {
                'success': complete_sync.sync_status in ['success', 'partial'],
                'complete_sync_id': complete_sync.id,
                'sync_status': complete_sync.sync_status,
                'total_providers_synced': complete_sync.total_providers_synced,
                'successful_providers': complete_sync.successful_providers,
                'failed_providers': complete_sync.failed_providers,
                'total_resources_found': complete_sync.total_resources_found,
                'total_monthly_cost': complete_sync.total_monthly_cost,
                'total_daily_cost': complete_sync.total_daily_cost,
                'cost_by_provider': complete_sync.get_cost_by_provider(),
                'resources_by_provider': complete_sync.get_resources_by_provider(),
                'sync_duration_seconds': complete_sync.sync_duration_seconds,
                'error_message': complete_sync.error_message,
                'provider_errors': provider_errors
            }
            
            self.logger.info(f"Complete sync {complete_sync.id} completed: {complete_sync.sync_status}")
            # Post-sync: run recommendations orchestrator if enabled and sync had any success
            try:
                if current_app.config.get('RECOMMENDATIONS_ENABLED', True) and response['success']:
                    self.logger.info(f"Running recommendations orchestrator for complete_sync {complete_sync.id}")
                    reco = RecommendationOrchestrator()
                    reco_summary = reco.run_for_sync(complete_sync.id)
                    response['recommendations_summary'] = reco_summary
                    # Persist recommendations summary into sync_config for later retrieval via API
                    try:
                        cfg = complete_sync.get_sync_config() or {}
                        cfg['recommendations_summary'] = reco_summary
                        complete_sync.set_sync_config(cfg)
                        db.session.commit()
                    except Exception as persist_err:
                        self.logger.error(f"Failed to persist recommendations summary: {persist_err}")
            except Exception as reco_err:
                self.logger.error(f"Recommendations orchestrator failed: {reco_err}")
                response['recommendations_error'] = str(reco_err)

            return response
            
        except Exception as e:
            self.logger.error(f"Sequential sync execution failed: {e}")
            complete_sync.sync_status = 'error'
            complete_sync.error_message = str(e)
            complete_sync.set_error_details({'exception': str(e)})
            complete_sync.mark_completed('error', str(e))
            db.session.commit()
            
            return {
                'success': False,
                'error': str(e),
                'message': 'Complete sync execution failed'
            }
    
    def get_complete_sync_status(self, complete_sync_id: int) -> Dict[str, any]:
        """
        Get status of a specific complete sync
        
        Args:
            complete_sync_id: ID of the complete sync
            
        Returns:
            Dict containing sync status
        """
        complete_sync = CompleteSync.query.filter_by(
            id=complete_sync_id,
            user_id=self.user_id
        ).first()
        
        if not complete_sync:
            return {
                'success': False,
                'error': 'Complete sync not found',
                'message': 'Complete sync does not exist or does not belong to user'
            }
        
        return {
            'success': True,
            'complete_sync_id': complete_sync.id,
            'sync_status': complete_sync.sync_status,
            'sync_started_at': complete_sync.sync_started_at.isoformat() if complete_sync.sync_started_at else None,
            'sync_completed_at': complete_sync.sync_completed_at.isoformat() if complete_sync.sync_completed_at else None,
            'sync_duration_seconds': complete_sync.sync_duration_seconds,
            'total_providers_synced': complete_sync.total_providers_synced,
            'successful_providers': complete_sync.successful_providers,
            'failed_providers': complete_sync.failed_providers,
            'total_resources_found': complete_sync.total_resources_found,
            'total_monthly_cost': complete_sync.total_monthly_cost,
            'total_daily_cost': complete_sync.total_daily_cost,
            'cost_by_provider': complete_sync.get_cost_by_provider(),
            'resources_by_provider': complete_sync.get_resources_by_provider(),
            'error_message': complete_sync.error_message,
            'error_details': complete_sync.get_error_details()
        }
    
    def get_complete_sync_history(self, limit: int = 30) -> List[Dict[str, any]]:
        """
        Get complete sync history for the user
        
        Args:
            limit: Maximum number of syncs to return
            
        Returns:
            List of complete sync records
        """
        complete_syncs = CompleteSync.query.filter_by(
            user_id=self.user_id
        ).order_by(CompleteSync.sync_started_at.desc()).limit(limit).all()
        
        return [sync.to_dict() for sync in complete_syncs]
