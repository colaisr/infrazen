"""
Beget provider plugin
Wraps existing Beget functionality in the new plugin architecture
"""
import logging
from typing import Dict, List, Any
from datetime import datetime

from ..plugin_system import ProviderPlugin, SyncResult
from ..beget.client import BegetAPIClient
from ..resource_registry import resource_registry, ProviderResource

logger = logging.getLogger(__name__)


class BegetProviderPlugin(ProviderPlugin):
    """Beget provider plugin implementation"""

    __version__ = "1.0.0"

    def __init__(self, provider_id: int, credentials: Dict[str, Any], config: Dict[str, Any] = None):
        super().__init__(provider_id, credentials, config)

        # Initialize Beget client
        self.client = BegetAPIClient(
            credentials.get('username'),
            credentials.get('password'),
            credentials.get('api_url', 'https://api.beget.com')
        )

    def get_provider_type(self) -> str:
        return "beget"

    def get_provider_name(self) -> str:
        return "Beget Hosting"

    def get_required_credentials(self) -> List[str]:
        return ['username', 'password']

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            'supports_resources': True,
            'supports_metrics': True,
            'supports_cost_data': True,
            'supports_logs': False,
            'supports_vps': True,
            'supports_domains': True,
            'supports_databases': True,
            'supports_ftp': True,
            'supports_email': True,
            'api_endpoints': ['v1/auth', 'v1/vps', 'api/domain', 'api/database'],
            'regions': ['global'],  # Beget is global
            'billing_model': 'prepaid'
        }

    def get_resource_mappings(self) -> Dict[str, Any]:
        return {
            'vps': {
                'type': 'server',
                'service': 'Compute',
                'category': 'infrastructure'
            },
            'domain': {
                'type': 'domain',
                'service': 'DNS',
                'category': 'networking'
            },
            'database': {
                'type': 'database',
                'service': 'Database',
                'category': 'data'
            },
            'ftp': {
                'type': 'storage',
                'service': 'Storage',
                'category': 'data'
            },
            'email': {
                'type': 'email',
                'service': 'Email',
                'category': 'communication'
            }
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Beget API"""
        try:
            result = self.client.test_connection()

            return {
                'success': result.get('status') == 'success',
                'message': result.get('message', 'Connection test completed'),
                'account_info': result.get('account_info', {}),
                'api_status': result.get('api_status', 'unknown'),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Beget connection test failed: {e}")
            return {
                'success': False,
                'message': f'Connection test failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }

    def sync_resources(self) -> SyncResult:
        """Sync all resources from Beget"""
        result = SyncResult(success=False, message="Sync not started", provider_type=self.get_provider_type())

        try:
            self.logger.info(f"Starting Beget resource sync for provider {self.provider_id}")

            # Get all resources from Beget
            all_resources = self.client.get_all_resources()

            if not all_resources:
                result.message = "No resources found or sync failed"
                result.errors = ["Failed to retrieve resources from Beget API"]
                return result

            # Process resources into unified format
            unified_resources = self._process_beget_resources(all_resources)

            result.success = True
            result.message = f"Successfully synced {len(unified_resources)} resources from Beget"
            result.resources_synced = len(unified_resources)
            result.data = {
                'resources': [r.to_dict() for r in unified_resources],
                'raw_data': all_resources,
                'sync_timestamp': datetime.now().isoformat()
            }

            # Calculate total cost
            total_cost = sum(r.effective_cost for r in unified_resources)
            result.total_cost = total_cost

            self.logger.info(f"Beget sync completed: {len(unified_resources)} resources, {total_cost:.2f} RUB")

        except Exception as e:
            error_msg = f"Beget sync failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            result.message = error_msg
            result.errors = [str(e)]

        return result

    def _process_beget_resources(self, raw_data: Dict[str, Any]) -> List[ProviderResource]:
        """Process raw Beget data into unified resources"""
        unified_resources = []

        # Process VPS servers
        if 'vps_servers' in raw_data:
            for vps in raw_data['vps_servers']:
                try:
                    unified_vps = self._create_unified_vps(vps)
                    if unified_vps:
                        unified_resources.append(unified_vps)
                except Exception as e:
                    self.logger.warning(f"Failed to process VPS {vps.get('name', 'unknown')}: {e}")

        # Process domains
        if 'domains' in raw_data:
            for domain in raw_data['domains']:
                try:
                    unified_domain = self._create_unified_domain(domain)
                    if unified_domain:
                        unified_resources.append(unified_domain)
                except Exception as e:
                    self.logger.warning(f"Failed to process domain {domain.get('name', 'unknown')}: {e}")

        # Process databases
        if 'databases' in raw_data:
            for db in raw_data['databases']:
                try:
                    unified_db = self._create_unified_database(db)
                    if unified_db:
                        unified_resources.append(unified_db)
                except Exception as e:
                    self.logger.warning(f"Failed to process database {db.get('name', 'unknown')}: {e}")

        # Process FTP accounts
        if 'ftp_accounts' in raw_data:
            for ftp in raw_data['ftp_accounts']:
                try:
                    unified_ftp = self._create_unified_ftp(ftp)
                    if unified_ftp:
                        unified_resources.append(unified_ftp)
                except Exception as e:
                    self.logger.warning(f"Failed to process FTP {ftp.get('username', 'unknown')}: {e}")

        # Process email accounts
        if 'email_accounts' in raw_data:
            for email in raw_data['email_accounts']:
                try:
                    unified_email = self._create_unified_email(email)
                    if unified_email:
                        unified_resources.append(unified_email)
                except Exception as e:
                    self.logger.warning(f"Failed to process email {email.get('email', 'unknown')}: {e}")

        return unified_resources

    def _create_unified_vps(self, vps_data: Dict[str, Any]) -> ProviderResource:
        """Create unified resource for VPS server"""
        # Extract CPU/RAM from configuration
        config = vps_data.get('configuration', {})
        vcpus = config.get('cpu_count', 0)
        ram_mb = config.get('memory', 0)

        # Calculate total storage from attached volumes
        attached_volumes = vps_data.get('attached_volumes', [])
        total_storage_gb = sum(v.get('size_gb', 0) for v in attached_volumes)

        # Determine status
        raw_status = vps_data.get('status', 'unknown')
        unified_status = resource_registry._map_status(raw_status.lower(), 'beget')

        unified_resource = ProviderResource(
            resource_id=str(vps_data.get('id', '')),
            resource_name=vps_data.get('name', vps_data.get('display_name', 'Unknown')),
            resource_type='server',
            service_name='Compute',
            region='global',  # Beget is global
            status=unified_status,
            effective_cost=float(vps_data.get('monthly_cost', 0.0)),
            currency='RUB',
            billing_period='monthly',
            provider_config=vps_data,
            provider_type='beget'
        )

        # Add VPS-specific tags
        unified_resource.tags.update({
            'vps_id': str(vps_data.get('id', '')),
            'ip_address': vps_data.get('ip_address', ''),
            'hostname': vps_data.get('hostname', ''),
            'cpu_cores': str(vcpus),
            'ram_mb': str(ram_mb),
            'disk_gb': str(vps_data.get('disk_gb', 0)),
            'total_storage_gb': str(total_storage_gb),
            'software': vps_data.get('software', ''),
            'software_version': vps_data.get('software_version', ''),
            'bandwidth_gb': str(vps_data.get('bandwidth_gb', 0)),
            'monthly_cost': str(vps_data.get('monthly_cost', 0)),
            'daily_cost': str(vps_data.get('daily_cost', 0))
        })

        return unified_resource

    def _create_unified_domain(self, domain_data: Dict[str, Any]) -> ProviderResource:
        """Create unified resource for domain"""
        # Calculate costs
        monthly_cost = domain_data.get('monthly_cost', 0.0)
        renewal_cost = domain_data.get('renewal_cost', 0.0)

        unified_resource = ProviderResource(
            resource_id=str(domain_data.get('id', domain_data.get('name', ''))),
            resource_name=domain_data.get('name', domain_data.get('fqdn', 'Unknown')),
            resource_type='domain',
            service_name='DNS',
            region='global',
            status=domain_data.get('status', 'active'),
            effective_cost=monthly_cost + renewal_cost,  # Include both
            currency='RUB',
            billing_period='monthly',
            provider_config=domain_data,
            provider_type='beget'
        )

        # Add domain-specific tags
        unified_resource.tags.update({
            'domain_name': domain_data.get('name', ''),
            'registrar': domain_data.get('registrar', 'Beget'),
            'registration_date': domain_data.get('registration_date', ''),
            'expiration_date': domain_data.get('expiration_date', ''),
            'auto_renewal': str(domain_data.get('auto_renewal', False)),
            'domain_age_days': str(domain_data.get('domain_age_days', 0)),
            'days_until_expiry': str(domain_data.get('days_until_expiry', 0)),
            'monthly_cost': str(monthly_cost),
            'renewal_cost': str(renewal_cost)
        })

        return unified_resource

    def _create_unified_database(self, db_data: Dict[str, Any]) -> ProviderResource:
        """Create unified resource for database"""
        unified_resource = ProviderResource(
            resource_id=str(db_data.get('id', db_data.get('name', ''))),
            resource_name=db_data.get('name', 'Unknown'),
            resource_type='database',
            service_name='Database',
            region='global',
            status='active',  # Assume active if returned
            effective_cost=float(db_data.get('monthly_cost', 0.0)),
            currency='RUB',
            billing_period='monthly',
            provider_config=db_data,
            provider_type='beget'
        )

        # Add database-specific tags
        unified_resource.tags.update({
            'database_name': db_data.get('name', ''),
            'database_type': db_data.get('type', 'MySQL'),
            'username': db_data.get('username', ''),
            'host': db_data.get('host', 'localhost'),
            'port': str(db_data.get('port', 3306)),
            'size_mb': str(db_data.get('size_mb', 0)),
            'monthly_cost': str(db_data.get('monthly_cost', 0))
        })

        return unified_resource

    def _create_unified_ftp(self, ftp_data: Dict[str, Any]) -> ProviderResource:
        """Create unified resource for FTP account"""
        unified_resource = ProviderResource(
            resource_id=str(ftp_data.get('id', ftp_data.get('username', ''))),
            resource_name=ftp_data.get('username', 'Unknown'),
            resource_type='storage',
            service_name='Storage',
            region='global',
            status='active' if ftp_data.get('is_active', True) else 'inactive',
            effective_cost=float(ftp_data.get('monthly_cost', 0.0)),
            currency='RUB',
            billing_period='monthly',
            provider_config=ftp_data,
            provider_type='beget'
        )

        # Add FTP-specific tags
        unified_resource.tags.update({
            'ftp_username': ftp_data.get('username', ''),
            'home_directory': ftp_data.get('home_directory', '/'),
            'disk_quota_mb': str(ftp_data.get('disk_quota_mb', 0)),
            'disk_used_mb': str(ftp_data.get('disk_used_mb', 0)),
            'server_host': ftp_data.get('server_host', ''),
            'port': str(ftp_data.get('port', 21)),
            'monthly_cost': str(ftp_data.get('monthly_cost', 0))
        })

        return unified_resource

    def _create_unified_email(self, email_data: Dict[str, Any]) -> ProviderResource:
        """Create unified resource for email account"""
        unified_resource = ProviderResource(
            resource_id=str(email_data.get('id', email_data.get('email', ''))),
            resource_name=email_data.get('email', 'Unknown'),
            resource_type='email',
            service_name='Email',
            region='global',
            status='active' if email_data.get('is_active', True) else 'inactive',
            effective_cost=float(email_data.get('monthly_cost', 0.0)),
            currency='RUB',
            billing_period='monthly',
            provider_config=email_data,
            provider_type='beget'
        )

        # Add email-specific tags
        unified_resource.tags.update({
            'email_address': email_data.get('email', ''),
            'domain': email_data.get('domain', ''),
            'quota_mb': str(email_data.get('quota_mb', 0)),
            'used_mb': str(email_data.get('used_mb', 0)),
            'monthly_cost': str(email_data.get('monthly_cost', 0))
        })

        return unified_resource
