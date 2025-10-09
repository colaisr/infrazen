"""
Selectel provider plugin
Wraps existing Selectel functionality in the new plugin architecture
"""
import logging
from typing import Dict, List, Any
from datetime import datetime

from ..plugin_system import ProviderPlugin, SyncResult
from ..selectel.client import SelectelClient
from ..resource_registry import resource_registry, ProviderResource

logger = logging.getLogger(__name__)


class SelectelProviderPlugin(ProviderPlugin):
    """Selectel provider plugin implementation"""

    __version__ = "1.0.0"

    def __init__(self, provider_id: int, credentials: Dict[str, Any], config: Dict[str, Any] = None):
        super().__init__(provider_id, credentials, config)

        # Add account_id to credentials for OpenStack authentication
        credentials_with_account = credentials.copy()
        credentials_with_account['account_id'] = config.get('account_id') if config else None

        # Initialize Selectel client
        self.client = SelectelClient(credentials_with_account)

    def get_provider_type(self) -> str:
        return "selectel"

    def get_provider_name(self) -> str:
        return "Selectel Cloud"

    def get_required_credentials(self) -> List[str]:
        return ['username', 'password', 'account_id']

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            'supports_resources': True,
            'supports_metrics': True,
            'supports_cost_data': True,
            'supports_logs': False,
            'supports_vms': True,
            'supports_volumes': True,
            'supports_kubernetes': True,
            'supports_databases': True,
            'supports_s3': True,
            'supports_load_balancers': True,
            'api_endpoints': ['billing', 'compute', 'storage', 'network'],
            'regions': ['ru-1', 'ru-2', 'ru-3', 'ru-7', 'ru-8', 'ru-9', 'kz-1'],
            'billing_model': 'pay-as-you-go',
            'sync_method': 'billing_first'
        }

    def get_resource_mappings(self) -> Dict[str, Any]:
        return {
            'server': {
                'type': 'server',
                'service': 'Compute',
                'category': 'infrastructure'
            },
            'volume': {
                'type': 'volume',
                'service': 'Block Storage',
                'category': 'storage'
            },
            'file_storage': {
                'type': 'file_storage',
                'service': 'File Storage',
                'category': 'storage'
            },
            'database': {
                'type': 'database',
                'service': 'Database',
                'category': 'data'
            },
            'kubernetes_cluster': {
                'type': 'kubernetes_cluster',
                'service': 'Kubernetes',
                'category': 'containers'
            },
            'kubernetes_nodegroup': {
                'type': 'kubernetes_nodegroup',
                'service': 'Kubernetes',
                'category': 'containers'
            },
            's3_bucket': {
                'type': 's3_bucket',
                'service': 'Object Storage',
                'category': 'storage'
            },
            'load_balancer': {
                'type': 'load_balancer',
                'service': 'Network',
                'category': 'networking'
            },
            'floating_ip': {
                'type': 'floating_ip',
                'service': 'Network',
                'category': 'networking'
            }
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Selectel APIs"""
        try:
            result = self.client.test_connection()

            return {
                'success': result.get('success', False),
                'message': result.get('message', 'Connection test completed'),
                'account_info': result.get('account_info', {}),
                'api_status': 'connected' if result.get('success') else 'failed',
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Selectel connection test failed: {e}")
            return {
                'success': False,
                'message': f'Connection test failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }

    def sync_resources(self) -> SyncResult:
        """Perform billing-first sync for Selectel"""
        result = SyncResult(success=False, message="Sync not started", provider_type=self.get_provider_type())

        try:
            self.logger.info(f"Starting Selectel billing-first sync for provider {self.provider_id}")

            # Use the existing SelectelService sync method
            from ..selectel.service import SelectelService
            from app.core.models.provider import CloudProvider

            # Get provider instance
            provider = CloudProvider.query.get(self.provider_id)
            if not provider:
                result.message = f"Provider {self.provider_id} not found"
                result.errors = ["Provider not found in database"]
                return result

            # Create service instance
            service = SelectelService(provider)

            # Perform sync
            sync_result = service.sync_resources()

            # Convert to plugin result format
            result.success = sync_result.get('success', False)
            result.message = sync_result.get('message', 'Sync completed')
            result.resources_synced = sync_result.get('resources_synced', 0)
            result.total_cost = sync_result.get('total_daily_cost', 0.0)
            result.errors = sync_result.get('errors', [])

            # Add sync data
            result.data = {
                'sync_details': sync_result,
                'sync_snapshot_id': sync_result.get('sync_snapshot_id'),
                'orphan_volumes': sync_result.get('orphan_volumes', 0),
                'zombie_resources': sync_result.get('zombie_resources', 0),
                'service_types': sync_result.get('service_types', []),
                'sync_timestamp': datetime.now().isoformat()
            }

            self.logger.info(f"Selectel sync completed: {result.resources_synced} resources, {result.total_cost:.2f} RUB/day")

        except Exception as e:
            error_msg = f"Selectel sync failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            result.message = error_msg
            result.errors = [str(e)]

        return result
