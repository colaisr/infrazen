"""
Complete Sync Service for orchestrating synchronization across all organization providers
"""
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from app.core.models import db
from app.core.models.organization import Organization
from app.core.models.provider import CloudProvider
from app.core.models.complete_sync import CompleteSync, ProviderSyncReference
from app.providers import sync_orchestrator
from app.core.recommendations.orchestrator import RecommendationOrchestrator
from flask import current_app

logger = logging.getLogger(__name__)

class CompleteSyncService:
    """
    Service for managing complete sync operations across all organization providers
    """
    
    def __init__(self, organization_id: int, user_id: Optional[int] = None):
        """
        Initialize sync service for an organization
        
        Args:
            organization_id: Organization ID to sync
            user_id: Optional user ID for backward compatibility (will be determined from org if not provided)
        """
        self.organization_id = organization_id
        self.organization = Organization.query.get(organization_id)
        if not self.organization:
            raise ValueError(f"Organization with ID {organization_id} not found")
        
        # Get user_id from organization owner if not provided (for backward compatibility)
        if user_id is None:
            owner = self.organization.get_owner()
            if owner:
                self.user_id = owner.user_id
            else:
                # Fallback: get first active member
                member = self.organization.members.filter_by(is_active=True).first()
                self.user_id = member.user_id if member else None
        else:
            self.user_id = user_id
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def start_complete_sync(self, sync_type: str = 'manual', background: bool = False) -> Dict[str, any]:
        """
        Start a complete sync operation for all auto-sync enabled providers in the organization
        
        Args:
            sync_type: Type of sync (manual, scheduled, api)
            background: If True, run sync in background thread and return immediately (avoids nginx 504)
            
        Returns:
            Dict containing sync results (or minimal info if background=True)
        """
        try:
            self.logger.info(f"Starting complete sync for organization {self.organization_id} ({self.organization.name})")
            
            # Get all auto-sync enabled providers for this organization
            providers = self.get_organization_providers()
            
            if not providers:
                return {
                    'success': False,
                    'error': 'No auto-sync enabled providers found',
                    'message': 'No providers configured for automatic synchronization'
                }
            
            # Create complete sync record
            complete_sync = CompleteSync(
                organization_id=self.organization_id,
                user_id=self.user_id,  # Keep for backward compatibility
                sync_type=sync_type,
                sync_status='running',
                sync_started_at=datetime.now()
            )
            
            # Set sync configuration
            sync_config = {
                'sync_type': sync_type,
                'organization_id': self.organization_id,
                'organization_name': self.organization.name,
                'user_id': self.user_id,
                'providers_count': len(providers),
                'sync_timestamp': datetime.now().isoformat(),
                'providers': [{'id': p.id, 'name': p.connection_name, 'type': p.provider_type} for p in providers]
            }
            complete_sync.set_sync_config(sync_config)
            
            db.session.add(complete_sync)
            db.session.commit()
            
            self.logger.info(f"Created complete sync {complete_sync.id} for {len(providers)} providers")
            
            if background:
                def _run():
                    from app import create_app
                    app = create_app()
                    with app.app_context():
                        try:
                            svc = CompleteSyncService(self.organization_id, user_id=self.user_id)
                            svc.execute_sync_for_record(complete_sync.id)
                        except Exception as e:
                            app.logger.error(f"Background complete sync failed: {e}", exc_info=True)
                thread = threading.Thread(target=_run, daemon=True)
                thread.start()
                return {
                    'success': True,
                    'complete_sync_id': complete_sync.id,
                    'message': 'Синхронизация запущена в фоне. Обновите страницу через 1–2 минуты.',
                    'background': True,
                }
            
            # Execute sequential sync for each provider (synchronous)
            return self._execute_sequential_sync(complete_sync, providers)
            
        except Exception as e:
            self.logger.error(f"Complete sync failed for organization {self.organization_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Complete sync failed due to system error'
            }
    
    def execute_sync_for_record(self, complete_sync_id: int) -> None:
        """Execute sync for an existing complete_sync record (used by background thread)."""
        complete_sync = CompleteSync.query.filter_by(
            id=complete_sync_id,
            organization_id=self.organization_id
        ).first()
        if not complete_sync:
            self.logger.error(f"CompleteSync {complete_sync_id} not found")
            return
        providers = self.get_organization_providers()
        if not providers:
            complete_sync.sync_status = 'error'
            complete_sync.error_message = 'No providers to sync'
            complete_sync.mark_completed('error', 'No providers to sync')
            db.session.commit()
            return
        self._execute_sequential_sync(complete_sync, providers)

    def get_organization_providers(self) -> List[CloudProvider]:
        """
        Get all auto-sync enabled providers for the organization (excluding soft-deleted)
        
        Returns:
            List of CloudProvider instances
        """
        return CloudProvider.query.filter_by(
            organization_id=self.organization_id,
            auto_sync=True,
            is_active=True,
            is_deleted=False  # Exclude soft-deleted providers from sync
        ).order_by('created_at').all()
    
    def get_user_providers(self) -> List[CloudProvider]:
        """
        DEPRECATED: Use get_organization_providers() instead.
        Kept for backward compatibility.
        """
        return self.get_organization_providers()
    
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
            provider_refs_to_add = []  # Collect refs; sync_provider does db.session.remove()
            
            # Update complete sync with provider count
            complete_sync.total_providers_synced = len(providers)
            complete_sync_id = complete_sync.id  # Capture before sync (remove() detaches)
            
            # Sync each provider sequentially
            for order, provider in enumerate(providers, 1):
                # Capture before sync_provider (it calls db.session.remove() which detaches provider)
                provider_id = provider.id
                provider_name = provider.connection_name
                self.logger.info(f"Syncing provider {provider_id} ({provider_name}) - {order}/{len(providers)}")
                
                # Create provider sync reference
                provider_ref = ProviderSyncReference(
                    complete_sync_id=complete_sync_id,
                    provider_id=provider_id,
                    sync_order=order,
                    sync_status='running'
                )
                
                try:
                    # Execute individual provider sync
                    sync_result = sync_orchestrator.sync_provider(provider_id, 'complete_sync')
                    
                    if sync_result['success']:
                        # Store reference to generated snapshot
                        provider_ref.sync_snapshot_id = sync_result['sync_snapshot_id']
                        provider_ref.sync_status = 'success'
                        provider_ref.resources_synced = sync_result['resources_synced']
                        
                        # Get cost from various field names (providers use different names)
                        provider_cost = (
                            sync_result.get('total_cost') or 
                            sync_result.get('total_daily_cost') or 
                            sync_result.get('estimated_daily_cost') or 
                            0.0
                        )
                        provider_ref.provider_cost = provider_cost
                        provider_ref.sync_duration_seconds = sync_result.get('sync_duration_seconds', 0)
                        
                        # Aggregate costs
                        total_cost += provider_cost
                        cost_by_provider[provider_name] = provider_cost
                        resources_by_provider[provider_name] = provider_ref.resources_synced
                        total_resources += provider_ref.resources_synced
                        successful_providers += 1
                        
                        self.logger.info(f"Provider {provider_name} synced successfully: {provider_ref.resources_synced} resources, {provider_ref.provider_cost} RUB")
                        
                    else:
                        # Handle sync failure
                        provider_ref.sync_status = 'error'
                        provider_ref.error_message = sync_result.get('error', 'Unknown error')
                        provider_ref.set_error_details(sync_result.get('errors', {}))
                        
                        # Set sync_snapshot_id if available (even on error)
                        # Some providers create snapshots before failing
                        if sync_result.get('sync_snapshot_id'):
                            provider_ref.sync_snapshot_id = sync_result['sync_snapshot_id']
                        
                        failed_providers += 1
                        provider_errors.append({
                            'provider': provider_name,
                            'error': sync_result.get('error', 'Unknown error')
                        })
                        
                        self.logger.error(f"Provider {provider_name} sync failed: {sync_result.get('error')}")
                
                except Exception as e:
                    # Handle unexpected errors
                    provider_ref.sync_status = 'error'
                    provider_ref.error_message = str(e)
                    provider_ref.set_error_details({'exception': str(e)})
                    failed_providers += 1
                    provider_errors.append({
                        'provider': provider_name,
                        'error': str(e)
                    })
                    
                    self.logger.error(f"Provider {provider_name} sync exception: {e}")
                
                # Collect provider refs; add after loop (sync_provider does db.session.remove())
                if provider_ref.sync_snapshot_id is not None:
                    provider_refs_to_add.append(provider_ref)
                else:
                    self.logger.warning(f"Skipping provider_sync_reference for {provider_name} - no sync_snapshot_id")
            
            # Re-query complete_sync: sync_provider calls db.session.remove() which detaches
            # all objects. We need a session-bound instance for updates and recommendations.
            complete_sync = CompleteSync.query.get(complete_sync_id)
            if not complete_sync:
                raise ValueError(f"CompleteSync {complete_sync_id} not found after sync")
            
            for ref in provider_refs_to_add:
                db.session.add(ref)
            
            # Update complete sync with results (re-queried instance; initial updates were lost to remove())
            complete_sync.total_providers_synced = len(providers)
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
            # Run recommendations in background so API can return immediately (avoids client timeout)
            if current_app.config.get('RECOMMENDATIONS_ENABLED', True) and response['success']:
                complete_sync_id = complete_sync.id
                org_id = self.organization_id

                def _run_recommendations():
                    from app import create_app
                    app = create_app()
                    with app.app_context():
                        try:
                            logger.info(f"Running recommendations orchestrator for complete_sync {complete_sync_id}")
                            reco = RecommendationOrchestrator()
                            reco_summary = reco.run_for_sync(complete_sync_id)
                            cs = CompleteSync.query.filter_by(id=complete_sync_id, organization_id=org_id).first()
                            if cs:
                                cfg = cs.get_sync_config() or {}
                                cfg['recommendations_summary'] = reco_summary
                                cs.set_sync_config(cfg)
                                db.session.commit()
                        except Exception as e:
                            logger.error(f"Recommendations orchestrator failed: {e}", exc_info=True)

                t = threading.Thread(target=_run_recommendations, daemon=True)
                t.start()

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
            organization_id=self.organization_id
        ).first()
        
        if not complete_sync:
            return {
                'success': False,
                'error': 'Complete sync not found',
                'message': 'Complete sync does not exist or does not belong to organization'
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
        Get complete sync history for the organization
        
        Args:
            limit: Maximum number of syncs to return
            
        Returns:
            List of complete sync records
        """
        complete_syncs = CompleteSync.query.filter_by(
            organization_id=self.organization_id
        ).order_by(CompleteSync.sync_started_at.desc()).limit(limit).all()
        
        return [sync.to_dict() for sync in complete_syncs]
