"""
Unified sync orchestrator for all provider plugins
"""
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

import sqlalchemy.exc
from app.core.models import db
from app.core.models.provider import CloudProvider
from app.core.models.sync import SyncSnapshot
from app.core.models.resource import Resource
from .plugin_system import ProviderPluginManager, SyncResult
from .resource_registry import resource_registry, ProviderResource
from . import plugin_manager as default_plugin_manager

logger = logging.getLogger(__name__)


class SyncOrchestrator:
    """Unified sync orchestrator for all provider types"""

    def __init__(self, plugin_manager: ProviderPluginManager = None):
        # If caller doesn't pass a plugin manager, use the shared module instance.
        self.plugin_manager = plugin_manager or default_plugin_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def sync_provider(self, provider_id: int, sync_type: str = 'manual') -> Dict[str, Any]:
        """
        Sync a specific provider using its plugin

        Args:
            provider_id: Database ID of the provider
            sync_type: Type of sync (manual, scheduled, api)

        Returns:
            Dict containing sync results
        """
        try:
            # Get provider from database
            provider = CloudProvider.query.get(provider_id)
            if not provider:
                return {
                    'success': False,
                    'error': f'Provider {provider_id} not found',
                    'message': 'Provider does not exist'
                }

            self.logger.info(f"Starting {sync_type} sync for provider {provider_id} ({provider.provider_type})")

            # Create sync snapshot with organization_id from provider
            sync_snapshot = SyncSnapshot(
                provider_id=provider_id,
                organization_id=provider.organization_id,
                sync_type=sync_type,
                sync_status='running',
                sync_started_at=datetime.now()
            )

            # Set sync configuration
            sync_config = {
                'sync_type': sync_type,
                'provider_type': provider.provider_type,
                'connection_name': provider.connection_name,
                'sync_timestamp': datetime.now().isoformat()
            }
            sync_snapshot.set_sync_config(sync_config)

            db.session.add(sync_snapshot)
            db.session.commit()
            sync_snapshot_id = sync_snapshot.id

            # Get provider credentials
            credentials = provider.get_credentials()

            # Create plugin instance
            plugin = self.plugin_manager.create_plugin_instance(
                provider.provider_type,
                provider_id,
                credentials,
                {'connection_name': provider.connection_name}
            )

            if not plugin:
                error_msg = f'No plugin available for provider type: {provider.provider_type}'
                self.logger.error(error_msg)
                sync_snapshot.mark_completed('error', error_msg)
                db.session.commit()

                return {
                    'success': False,
                    'error': error_msg,
                    'message': 'Plugin not available'
                }

            # Test connection first
            self.logger.info(f"Testing connection for provider {provider_id}")
            connection_test = plugin.test_connection()

            if not connection_test.get('success', False):
                error_msg = connection_test.get('message', 'Connection test failed')
                self.logger.error(f"Connection test failed for provider {provider_id}: {error_msg}")
                sync_snapshot.mark_completed('error', f'Connection failed: {error_msg}')
                db.session.commit()

                return {
                    'success': False,
                    'error': error_msg,
                    'message': 'Connection test failed'
                }

            # Update provider metadata with connection info
            provider.provider_metadata = json.dumps({
                'last_connection_test': datetime.now().isoformat(),
                'connection_status': 'success',
                'account_info': connection_test.get('account_info', {})
            })
            db.session.add(provider)
            db.session.commit()

            # Release DB connection before long sync. Beget MySQL wait_timeout=30s;
            # sync can take 50+ seconds of HTTP calls, so holding a connection causes
            # "Lost connection to MySQL server during query" when we try to commit after.
            # Invalidate the connection so the pool discards it (it will be dead after sync).
            try:
                conn = db.session.connection()
                conn.invalidate()
            except Exception:
                pass
            db.session.remove()

            # Perform sync (no DB access - all HTTP)
            self.logger.info(f"Performing resource sync for provider {provider_id}")
            sync_result = plugin.sync_resources()

            # Re-query with fresh session for processing (retry on stale connection)
            provider = None
            sync_snapshot = None
            for attempt in range(3):
                try:
                    provider = CloudProvider.query.get(provider_id)
                    sync_snapshot = SyncSnapshot.query.get(sync_snapshot_id)
                    break
                except sqlalchemy.exc.OperationalError as oe:
                    if '2013' not in str(oe) or attempt == 2:
                        raise
                    db.session.remove()
                    time.sleep(0.5 * (attempt + 1))
            if not provider or not sync_snapshot:
                return {
                    'success': False,
                    'error': 'Provider or snapshot not found after sync',
                    'message': 'Database lookup failed after sync'
                }

            # Process sync results
            processed_result = self._process_sync_result(sync_result, sync_snapshot, provider)

            # Update provider sync status
            provider.last_sync = datetime.now()
            provider.sync_status = 'success' if processed_result['success'] else 'error'
            provider.sync_error = None if processed_result['success'] else processed_result.get('error', 'Unknown error')
            db.session.add(provider)

            db.session.commit()

            self.logger.info(f"Sync completed for provider {provider_id}: {processed_result['message']}")

            return processed_result

        except Exception as e:
            error_msg = f'Sync failed for provider {provider_id}: {str(e)}'
            self.logger.error(error_msg, exc_info=True)

            # Update sync snapshot if it exists (re-query in case session was removed)
            try:
                snapshot = SyncSnapshot.query.get(sync_snapshot_id) if 'sync_snapshot_id' in locals() else None
                if snapshot:
                    snapshot.mark_completed('error', str(e))
                    db.session.commit()
            except Exception:
                pass

            return {
                'success': False,
                'error': str(e),
                'message': 'Sync failed unexpectedly'
            }

    def sync_all_providers(self, provider_ids: List[int] = None, max_workers: int = 3) -> Dict[str, Any]:
        """
        Sync multiple providers in parallel

        Args:
            provider_ids: List of provider IDs to sync (all if None)
            max_workers: Maximum number of parallel syncs

        Returns:
            Dict containing results for all providers
        """
        if provider_ids is None:
            # Get all active providers
            providers = CloudProvider.query.filter_by(is_active=True).all()
            provider_ids = [p.id for p in providers]

        if not provider_ids:
            return {
                'success': True,
                'message': 'No providers to sync',
                'results': {}
            }

        self.logger.info(f"Starting parallel sync for {len(provider_ids)} providers")

        results = {}
        errors = []

        # Use ThreadPoolExecutor for parallel execution
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all sync tasks
            future_to_provider = {
                executor.submit(self.sync_provider, provider_id, 'batch'): provider_id
                for provider_id in provider_ids
            }

            # Collect results as they complete
            for future in as_completed(future_to_provider):
                provider_id = future_to_provider[future]
                try:
                    result = future.result()
                    results[str(provider_id)] = result

                    if not result.get('success', False):
                        errors.append(f'Provider {provider_id}: {result.get("error", "Unknown error")}')

                except Exception as e:
                    error_msg = f'Provider {provider_id} sync failed with exception: {str(e)}'
                    self.logger.error(error_msg)
                    results[str(provider_id)] = {
                        'success': False,
                        'error': str(e),
                        'message': 'Sync failed with exception'
                    }
                    errors.append(error_msg)

        # Summarize results
        successful = sum(1 for r in results.values() if r.get('success', False))
        total = len(results)

        overall_success = len(errors) == 0
        message = f'Synced {successful}/{total} providers successfully'

        if errors:
            message += f' ({len(errors)} errors)'

        return {
            'success': overall_success,
            'message': message,
            'total_providers': total,
            'successful_syncs': successful,
            'failed_syncs': len(errors),
            'errors': errors,
            'results': results
        }

    def test_provider_connection(self, provider_id: int) -> Dict[str, Any]:
        """
        Test connection to a provider without performing full sync

        Args:
            provider_id: Database ID of the provider

        Returns:
            Dict containing connection test results
        """
        try:
            provider = CloudProvider.query.get(provider_id)
            if not provider:
                return {
                    'success': False,
                    'error': f'Provider {provider_id} not found'
                }

            credentials = provider.get_credentials()

            plugin = self.plugin_manager.create_plugin_instance(
                provider.provider_type,
                provider_id,
                credentials
            )

            if not plugin:
                return {
                    'success': False,
                    'error': f'No plugin available for provider type: {provider.provider_type}'
                }

            result = plugin.test_connection()

            # Update provider metadata
            if result.get('success'):
                metadata = json.loads(provider.provider_metadata or '{}')
                metadata.update({
                    'last_connection_test': datetime.now().isoformat(),
                    'connection_status': 'success',
                    'account_info': result.get('account_info', {})
                })
                provider.provider_metadata = json.dumps(metadata)
            else:
                metadata = json.loads(provider.provider_metadata or '{}')
                metadata.update({
                    'last_connection_test': datetime.now().isoformat(),
                    'connection_status': 'failed',
                    'last_error': result.get('message', 'Unknown error')
                })
                provider.provider_metadata = json.dumps(metadata)

            db.session.add(provider)
            db.session.commit()

            return result

        except Exception as e:
            self.logger.error(f"Connection test failed for provider {provider_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Connection test failed unexpectedly'
            }

    def get_provider_sync_status(self, provider_id: int) -> Dict[str, Any]:
        """
        Get sync status and history for a provider

        Args:
            provider_id: Database ID of the provider

        Returns:
            Dict containing sync status information
        """
        try:
            provider = CloudProvider.query.get(provider_id)
            if not provider:
                return {
                    'success': False,
                    'error': f'Provider {provider_id} not found'
                }

            # Get recent sync snapshots
            recent_snapshots = SyncSnapshot.query.filter_by(provider_id=provider_id)\
                .order_by(SyncSnapshot.sync_started_at.desc())\
                .limit(5).all()

            # Get resource counts
            resource_counts = db.session.query(
                Resource.resource_type,
                db.func.count(Resource.id).label('count')
            ).filter_by(provider_id=provider_id, is_active=True)\
             .group_by(Resource.resource_type).all()

            resource_counts_dict = {rc.resource_type: rc.count for rc in resource_counts}
            total_resources = sum(resource_counts_dict.values())

            # Get last successful sync
            last_successful = SyncSnapshot.query.filter_by(
                provider_id=provider_id,
                sync_status='success'
            ).order_by(SyncSnapshot.sync_completed_at.desc()).first()

            return {
                'success': True,
                'provider_id': provider_id,
                'provider_type': provider.provider_type,
                'connection_name': provider.connection_name,
                'current_status': provider.sync_status,
                'last_sync': provider.last_sync.isoformat() if provider.last_sync else None,
                'last_error': provider.sync_error,
                'total_resources': total_resources,
                'resource_counts': resource_counts_dict,
                'last_successful_sync': last_successful.sync_completed_at.isoformat() if last_successful else None,
                'recent_syncs': [s.to_dict() for s in recent_snapshots]
            }

        except Exception as e:
            self.logger.error(f"Failed to get sync status for provider {provider_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _process_sync_result(self, sync_result: SyncResult, sync_snapshot: SyncSnapshot,
                           provider: CloudProvider) -> Dict[str, Any]:
        """
        Process sync result and update database

        Args:
            sync_result: Result from plugin sync
            sync_snapshot: Sync snapshot to update
            provider: Provider instance

        Returns:
            Dict containing processed results
        """
        try:
            sync_data = sync_result.data if hasattr(sync_result, 'data') else {}

            # Update sync snapshot
            sync_snapshot.sync_status = 'success' if sync_result.success else 'error'
            sync_snapshot.sync_completed_at = datetime.now()
            sync_snapshot.sync_duration_seconds = int(
                (sync_snapshot.sync_completed_at - sync_snapshot.sync_started_at).total_seconds()
            )

            # Store sync metadata
            sync_config = json.loads(sync_snapshot.sync_config) if sync_snapshot.sync_config else {}
            # IMPORTANT:
            # Do NOT store full plugin payload (especially `resources`) in sync_config.
            # Cloud.ru returns thousands of per-consumption components and can exceed DB column limits.
            plugin_data_summary = {}
            try:
                if isinstance(sync_data, dict):
                    plugin_data_summary = {
                        'sync_timestamp': sync_data.get('sync_timestamp'),
                        'resources_count': len(sync_data.get('resources', []) or []),
                        'account_billing': sync_data.get('account_billing'),
                        'billing_validation': sync_data.get('billing_validation'),
                    }
            except Exception:
                plugin_data_summary = {}
            sync_config.update({
                'sync_success': sync_result.success,
                'resources_synced': sync_result.resources_synced,
                'total_cost': sync_result.total_cost,
                'errors': sync_result.errors,
                'plugin_data': plugin_data_summary
            })
            sync_snapshot.sync_config = json.dumps(sync_config)

            # Process and store resources if available
            resources_processed = 0
            resource_processing_errors = []

            if sync_data and 'resources' in sync_data and sync_data['resources']:
                try:
                    resources_processed = self._process_plugin_resources(
                        sync_data['resources'], sync_snapshot, provider
                    )
                except Exception as e:
                    error_msg = f"Resource processing failed: {str(e)}"
                    self.logger.error(error_msg, exc_info=True)
                    resource_processing_errors.append(error_msg)

            # Update snapshot statistics
            if hasattr(sync_result, 'resources_synced') and sync_result.resources_synced > 0:
                sync_snapshot.total_resources_found = sync_result.resources_synced
                sync_snapshot.resources_created = resources_processed
                
                # Set total monthly cost from sync result
                if hasattr(sync_result, 'total_cost') and sync_result.total_cost is not None:
                    sync_snapshot.total_monthly_cost = sync_result.total_cost

                # If resource processing failed but sync was successful, mark as partial success
                if resource_processing_errors and sync_result.success:
                    sync_result.success = True  # Keep success but add errors
                    sync_result.errors.extend(resource_processing_errors)
                    sync_result.message += f" (resource processing failed: {len(resource_processing_errors)} errors)"

            db.session.add(sync_snapshot)

            # Update provider metadata with account billing info (if available)
            if sync_data and 'account_billing' in sync_data and sync_data['account_billing']:
                try:
                    # Get existing metadata or create new
                    existing_metadata = json.loads(provider.provider_metadata) if provider.provider_metadata else {}
                    
                    # Update account_info with billing data
                    account_info = existing_metadata.get('account_info', {})
                    account_info.update(sync_data['account_billing'])
                    existing_metadata['account_info'] = account_info
                    existing_metadata['last_sync'] = datetime.now().isoformat()
                    
                    # Update provider metadata
                    provider.provider_metadata = json.dumps(existing_metadata)
                    self.logger.info(f"Updated provider metadata with account billing info: balance={sync_data['account_billing'].get('balance')} {sync_data['account_billing'].get('currency')}")
                except Exception as e:
                    self.logger.warning(f"Failed to update provider metadata with billing info: {e}")

            # Ensure sync snapshot is marked as completed
            if sync_snapshot.sync_status == 'running':
                if resource_processing_errors:
                    sync_snapshot.mark_completed('partial_success', f'Completed with {len(resource_processing_errors)} resource processing errors')
                else:
                    sync_snapshot.mark_completed('success', sync_result.message)

            db.session.commit()

            return {
                'success': sync_result.success,
                'message': sync_result.message,
                'resources_synced': sync_result.resources_synced,
                'total_cost': sync_result.total_cost,
                'errors': sync_result.errors,
                'sync_snapshot_id': sync_snapshot.id
            }

        except Exception as e:
            self.logger.error(f"Failed to process sync result: {e}")
            try:
                db.session.rollback()
                if 'sync_snapshot' in locals():
                    sync_snapshot.mark_completed('error', f'Processing failed: {str(e)}')
                    db.session.commit()
            except Exception as rollback_e:
                self.logger.error(f"Error during rollback/cleanup: {rollback_e}")

            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to process sync results'
            }

    def _process_plugin_resources(self, plugin_resources: List[Dict], sync_snapshot: SyncSnapshot,
                                provider: CloudProvider) -> int:
        """
        Process resources returned by plugin and save to database

        Args:
            plugin_resources: List of resource dictionaries from plugin
            sync_snapshot: The sync snapshot
            provider: The cloud provider

        Returns:
            Number of resources processed
        """
        try:
            processed_count = 0

            processed_resources = []
            for resource_data in plugin_resources:
                try:
                    # Create or update resource in database
                    resource = self._create_or_update_resource_from_plugin(
                        resource_data, sync_snapshot, provider
                    )
                    if resource:
                        processed_count += 1
                        processed_resources.append((resource, resource_data))
                    else:
                        self.logger.warning(f"Resource processing returned None for: {resource_data.get('resource_name', 'unknown')}")

                except Exception as e:
                    self.logger.error(f"Failed to process resource {resource_data.get('resource_name', 'unknown')}: {e}")
                    continue
            
            # Commit all resources so their IDs are stable and a ResourceState
            # savepoint rollback cannot undo a newly-inserted resource row.
            db.session.commit()

            # Create ResourceState records and finish resource processing.
            # Batch commit every 100 resources to avoid 2500+ nested savepoints
            # which cause "maximum recursion" and "invalid savepoint" errors.
            from app.core.models.sync import ResourceState
            BATCH_SIZE = 100
            for idx, (resource, resource_data) in enumerate(processed_resources):
                try:
                    if resource.id is None:
                        self.logger.error(f"Resource has no ID for {resource_data.get('resource_name', 'unknown')}")
                        continue

                    savepoint = db.session.begin_nested()
                    try:
                        resource_state = ResourceState(
                            sync_snapshot_id=sync_snapshot.id,
                            resource_id=resource.id,
                            provider_resource_id=resource_data['resource_id'],
                            resource_type=resource_data['resource_type'],
                            resource_name=resource_data['resource_name'],
                            state_action='created' if resource_data.get('is_new', False) else 'updated',
                            service_name=resource_data.get('service_name', resource_data['resource_type'].title()),
                            region=resource_data.get('region', 'unknown'),
                            status=resource_data.get('status', 'unknown'),
                            effective_cost=resource_data.get('effective_cost', 0.0)
                        )
                        db.session.add(resource_state)

                        resource.set_daily_cost_baseline(
                            original_cost=resource_data.get('effective_cost', 0.0),
                            period=resource_data.get('billing_period', 'monthly'),
                            frequency='recurring'
                        )

                        tags = resource_data.get('tags', {})
                        for key, value in tags.items():
                            resource.add_tag(key, str(value))

                        db.session.flush()
                    except Exception as inner_e:
                        savepoint.rollback()
                        self.logger.warning(f"Skipped ResourceState for {resource_data.get('resource_name', 'unknown')}: {inner_e}")
                        continue

                    if (idx + 1) % 100 == 0:
                        self.logger.info(f"Processed {idx + 1}/{len(processed_resources)} resources for provider {provider.id}")

                    # Batch commit to avoid savepoint accumulation (PostgreSQL limit)
                    if (idx + 1) % BATCH_SIZE == 0:
                        db.session.commit()
                except Exception as e:
                    self.logger.error(f"Failed to process resource {resource_data.get('resource_name', 'unknown')}: {e}")
                    continue

            # Cloud.ru: deactivate old raw resources not in this sync (unified replaces all)
            if provider.provider_type == 'cloud-ru' and processed_resources:
                processed_ids = {rd['resource_id'] for _, rd in processed_resources}
                deactivated = Resource.query.filter(
                    Resource.provider_id == provider.id,
                    Resource.resource_id.notin_(processed_ids),
                    Resource.is_active == True
                ).update({'is_active': False}, synchronize_session=False)
                if deactivated > 0:
                    self.logger.info(f"Cloud.ru: deactivated {deactivated} old resources not in current sync")

            self.logger.info(f"Processed {processed_count} resources for provider {provider.id}")
            return processed_count

        except Exception as e:
            self.logger.error(f"Failed to process plugin resources: {e}")
            return 0

    def _create_or_update_resource_from_plugin(self, resource_data: Dict, sync_snapshot: SyncSnapshot,
                                             provider: CloudProvider) -> Optional[Resource]:
        """
        Create a fresh resource from plugin data (always creates new, never updates)

        Args:
            resource_data: Resource data from plugin
            sync_snapshot: The sync snapshot
            provider: The cloud provider

        Returns:
            Resource instance or None if failed
        """
        try:
            # Enforce known provider resource types inventory
            from app.core.models.provider_resource_type import ProviderResourceType
            from app.core.models.unrecognized_resource import UnrecognizedResource
            from datetime import datetime
            import json

            incoming_type = resource_data.get('resource_type')
            if incoming_type:
                # Try exact match first
                known = ProviderResourceType.query.filter_by(
                    provider_type=provider.provider_type,
                    unified_type=incoming_type,
                    enabled=True
                ).first()
                # If not found, try alias match and remap to unified type
                if known is None:
                    try:
                        rows = ProviderResourceType.query.filter_by(provider_type=provider.provider_type, enabled=True).all()
                        for row in rows:
                            aliases = []
                            if row.raw_aliases:
                                try:
                                    aliases = json.loads(row.raw_aliases)
                                except Exception:
                                    aliases = []
                            if incoming_type and any(incoming_type.lower() == str(a).lower() for a in aliases):
                                # Remap to unified type for storage/processing
                                resource_data['resource_type'] = row.unified_type
                                known = row
                                break
                    except Exception:
                        pass

                if known is None:
                    # Route to unrecognized resources and also surface in UI as a visible 'unknown' resource
                    try:
                        unrec = UnrecognizedResource(
                            provider_id=provider.id,
                            resource_id=str(resource_data.get('resource_id', '')),
                            resource_name=resource_data.get('resource_name', 'Unknown'),
                            resource_type=incoming_type,
                            service_type=resource_data.get('service_name'),
                            billing_data=json.dumps(resource_data, ensure_ascii=False),
                            user_id=provider.user_id,
                            sync_snapshot_id=sync_snapshot.id,
                            discovered_at=datetime.utcnow()
                        )
                        db.session.add(unrec)
                        db.session.commit()
                        self.logger.info(f"Gated unknown type: {provider.provider_type}:{incoming_type} -> Unrecognized")
                    except Exception:
                        db.session.rollback()
                    # Continue processing but downgrade the type to 'unknown' so it appears in Resources
                    resource_data['resource_type'] = 'unknown'
            # Extract resource information
            resource_id = resource_data['resource_id']
            resource_name = resource_data['resource_name']
            resource_type = resource_data['resource_type']
            
            self.logger.info(f"Processing resource: {resource_name} ({resource_type}) - ID: {resource_id}")
            service_name = resource_data.get('service_name', resource_type.title())
            region = resource_data.get('region', 'unknown')
            tenant = resource_data.get('tenant')
            status = resource_data.get('status', 'unknown')
            effective_cost = resource_data.get('effective_cost', 0.0)
            currency = resource_data.get('currency', 'RUB')
            billing_period = resource_data.get('billing_period', 'monthly')
            provider_config = resource_data.get('provider_config', resource_data)
            tags = resource_data.get('tags', {})
            external_ip = resource_data.get('external_ip')

            # Get or create the base Resource record (for reference)
            existing_resource = Resource.query.filter_by(
                provider_id=provider.id,
                resource_id=resource_id
            ).first()
            
            if existing_resource:
                # Update the base resource record with latest info
                resource = existing_resource
                resource.resource_name = resource_name
                resource.resource_type = resource_type
                resource.service_name = service_name
                resource.region = region
                resource.tenant = tenant
                resource.status = status
                resource.effective_cost = effective_cost
                resource.currency = currency
                resource.billing_period = billing_period
                resource.provider_config = json.dumps(provider_config)
                resource.external_ip = external_ip
                resource.last_sync = datetime.now()
                resource.is_active = True
            else:
                # Create new base resource record with organization_id from provider
                resource = Resource(
                    provider_id=provider.id,
                    organization_id=provider.organization_id,
                    resource_id=resource_id,
                    resource_name=resource_name,
                    resource_type=resource_type,
                    service_name=service_name,
                    region=region,
                    tenant=tenant,
                    status=status,
                    effective_cost=effective_cost,
                    currency=currency,
                    billing_period=billing_period,
                    provider_config=json.dumps(provider_config),
                    external_ip=external_ip,
                    last_sync=datetime.now(),
                    is_active=True
                )
                db.session.add(resource)
            
            db.session.flush()  # Get the resource ID
            db.session.commit()  # Persist immediately so later savepoint rollbacks cannot undo

            # Store resource data for later processing to avoid autoflush conflicts
            resource_data['processed_resource'] = resource
            resource_data['tags'] = tags
            resource_data['effective_cost'] = effective_cost
            resource_data['billing_period'] = billing_period
            
            self.logger.info(f"Successfully processed resource: {resource_name}")
            return resource

        except Exception as e:
            self.logger.error(f"Failed to create/update resource: {e}")
            db.session.rollback()
            return None


# Global sync orchestrator instance
sync_orchestrator = SyncOrchestrator(default_plugin_manager)
