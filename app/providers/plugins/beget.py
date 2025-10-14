"""
Beget provider plugin
Wraps existing Beget functionality in the new plugin architecture
"""
import logging
import json
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
        """Sync resources from Beget using billing-first approach"""
        result = SyncResult(success=False, message="Sync not started", provider_type=self.get_provider_type())

        try:
            self.logger.info(f"Starting Beget billing-first resource sync for provider {self.provider_id}")

            # PHASE 1: Billing Data Collection
            self.logger.info("Phase 1: Collecting billing data")
            account_billing = self._collect_account_billing()
            if not account_billing:
                result.message = "Failed to collect account billing data"
                result.errors = ["Account billing data unavailable"]
                return result

            # PHASE 2: Resource Discovery with Cost Filtering
            self.logger.info("Phase 2: Discovering paid resources")
            paid_resources = self._discover_paid_resources()

            # PHASE 3: Resource Processing and Unification
            self.logger.info("Phase 3: Processing and unifying resources")
            unified_resources, cpu_statistics, memory_statistics, s3_statistics = self._process_paid_resources(paid_resources)

            # PHASE 4: Cost Validation
            self.logger.info("Phase 4: Validating costs against account billing")
            total_calculated_cost = sum(r.effective_cost for r in unified_resources)
            billing_validation = self._validate_costs_against_billing(total_calculated_cost, account_billing)

            result.success = True
            result.message = f"Successfully synced {len(unified_resources)} paid resources from Beget"
            result.resources_synced = len(unified_resources)
            result.total_cost = total_calculated_cost
            result.data = {
                'resources': [r.to_dict() for r in unified_resources],
                'account_billing': account_billing,
                'billing_validation': billing_validation,
                'cpu_statistics': cpu_statistics,
                'memory_statistics': memory_statistics,
                's3_statistics': s3_statistics,
                'sync_timestamp': datetime.now().isoformat(),
                'billing_first_phases': {
                    'phase_1_billing_collected': True,
                    'phase_2_paid_resources_found': len(paid_resources),
                    'phase_3_resources_unified': len(unified_resources),
                    'phase_4_costs_validated': billing_validation.get('valid', False)
                }
            }

            self.logger.info(f"Beget billing-first sync completed: {len(unified_resources)} paid resources, {total_calculated_cost:.2f} RUB/day")

        except Exception as e:
            error_msg = f"Beget billing-first sync failed: {str(e)}"
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

    def _collect_account_billing(self) -> Dict[str, Any]:
        """Phase 1: Collect account-level billing data"""
        try:
            account_info = self.client.get_detailed_account_info()
            if not account_info or 'error' in account_info:
                self.logger.warning("Failed to get account billing data")
                return {}

            # Extract billing-relevant data
            billing_data = {
                'account_id': account_info.get('account_id'),
                'balance': account_info.get('balance', 0),
                'currency': account_info.get('currency', 'RUB'),
                'daily_rate': account_info.get('daily_rate', 0),
                'monthly_rate': account_info.get('monthly_rate', 0),
                'yearly_rate': account_info.get('yearly_rate', 0),
                'days_to_block': account_info.get('days_to_block', 0),
                'account_status': account_info.get('account_status', 'unknown'),
                'plan_name': account_info.get('plan_name', 'Unknown'),
                'billing_timestamp': datetime.now().isoformat()
            }

            self.logger.info(f"Collected account billing: {billing_data['daily_rate']} RUB/day, balance: {billing_data['balance']} RUB")
            return billing_data

        except Exception as e:
            self.logger.error(f"Failed to collect account billing: {e}")
            return {}

    def _discover_paid_resources(self) -> Dict[str, List[Dict]]:
        """Phase 2: Discover only resources that have actual costs"""
        paid_resources = {
            'vps_servers': [],
            'cloud_services': [],
            'paid_domains': []  # Only domains with actual costs
        }

        try:
            # Get VPS servers - these always have costs in Beget
            vps_servers = self.client.get_vps_servers_new_api()
            paid_vps = []

            for vps in vps_servers:
                # Only include VPS if it has a cost > 0
                daily_cost = vps.get('daily_cost', 0)
                monthly_cost = vps.get('monthly_cost', 0)

                if daily_cost > 0 or monthly_cost > 0:
                    paid_vps.append(vps)
                    self.logger.debug(f"Including paid VPS: {vps.get('name')} - {daily_cost} RUB/day")
                else:
                    self.logger.debug(f"Skipping free VPS: {vps.get('name')}")

            paid_resources['vps_servers'] = paid_vps

            # Get cloud services - these may have costs
            cloud_services = self.client.get_cloud_services()
            paid_cloud_services = []

            for service in cloud_services:
                daily_cost = service.get('daily_cost', 0)
                monthly_cost = service.get('monthly_cost', 0)
                service_type = service.get('service_type', '')

                # Include paid services and S3 storage (even if free, as it's a trackable resource)
                if daily_cost > 0 or monthly_cost > 0 or service_type == 'Storage':
                    paid_cloud_services.append(service)
                    if daily_cost > 0 or monthly_cost > 0:
                        self.logger.debug(f"Including paid cloud service: {service.get('name')} - {daily_cost} RUB/day")
                    else:
                        self.logger.debug(f"Including S3 storage resource: {service.get('name')} - free but trackable")
                else:
                    self.logger.debug(f"Skipping free cloud service: {service.get('name')}")

            paid_resources['cloud_services'] = paid_cloud_services

            # Get domains - filter for only paid domains (not free subdomains)
            domains = self.client.get_domains()
            paid_domains = []

            for domain in domains:
                # Include domains that have renewal costs or are registered domains
                renewal_cost = domain.get('renewal_cost', 0)
                monthly_cost = domain.get('monthly_cost', 0)
                domain_type = domain.get('domain_type', '')

                # Only include if it has actual costs or is a registered domain
                if renewal_cost > 0 or monthly_cost > 0 or domain_type == 'registered':
                    paid_domains.append(domain)
                    self.logger.debug(f"Including domain: {domain.get('name')} - {renewal_cost} RUB/renewal")
                else:
                    self.logger.debug(f"Skipping free domain: {domain.get('name')}")

            paid_resources['paid_domains'] = paid_domains

            total_paid_resources = len(paid_vps) + len(paid_cloud_services) + len(paid_domains)
            self.logger.info(f"Discovered {total_paid_resources} paid resources: {len(paid_vps)} VPS, {len(paid_cloud_services)} cloud services, {len(paid_domains)} domains")

            return paid_resources

        except Exception as e:
            self.logger.error(f"Failed to discover paid resources: {e}")
            return paid_resources

    def _process_paid_resources(self, paid_resources: Dict[str, List[Dict]]) -> List[ProviderResource]:
        """Phase 3: Process and unify only paid resources"""
        unified_resources = []

        # Process VPS servers and collect CPU/memory statistics
        vps_servers_for_stats = []
        for vps in paid_resources['vps_servers']:
            try:
                unified_vps = self._create_unified_vps(vps)
                if unified_vps:
                    unified_resources.append(unified_vps)
                    vps_servers_for_stats.append(vps)
            except Exception as e:
                self.logger.warning(f"Failed to process paid VPS {vps.get('name', 'unknown')}: {e}")

        # Collect CPU and memory statistics for VPS servers
        cpu_statistics = {}
        memory_statistics = {}
        if vps_servers_for_stats:
            try:
                self.logger.info("Collecting CPU statistics for VPS servers...")
                cpu_statistics = self.client.get_all_vps_cpu_statistics(vps_servers_for_stats, period='HOUR')
                
                self.logger.info("Collecting memory statistics for VPS servers...")
                memory_statistics = self.client.get_all_vps_memory_statistics(vps_servers_for_stats, period='HOUR')
                
                self.logger.info(f"CPU statistics collected for {cpu_statistics.get('vps_with_cpu_data', 0)} VPS servers")
                self.logger.info(f"Memory statistics collected for {memory_statistics.get('vps_with_memory_data', 0)} VPS servers")
                
                # Attach CPU/memory statistics to VPS resources
                self._attach_performance_stats_to_resources(unified_resources, cpu_statistics, memory_statistics)
                
            except Exception as e:
                self.logger.warning(f"Failed to collect CPU/memory statistics: {e}")

        # Process cloud services and collect S3 statistics
        s3_services_for_stats = []
        for service in paid_resources['cloud_services']:
            try:
                unified_service = self._create_unified_cloud_service(service)
                if unified_service:
                    unified_resources.append(unified_service)
                    # Collect S3 services for statistics
                    if service.get('service_type') == 'Storage':
                        s3_services_for_stats.append(service)
            except Exception as e:
                self.logger.warning(f"Failed to process paid cloud service {service.get('name', 'unknown')}: {e}")

        # Collect S3 statistics
        s3_statistics = {}
        if s3_services_for_stats:
            try:
                self.logger.info("Collecting S3 statistics...")
                s3_statistics = self.client.get_all_s3_statistics(s3_services_for_stats, period='MONTH')
                
                self.logger.info(f"S3 statistics collected for {s3_statistics.get('s3_with_statistics', 0)} services")
                
                # Attach S3 statistics to storage resources
                self._attach_s3_stats_to_resources(unified_resources, s3_statistics)
                
            except Exception as e:
                self.logger.warning(f"Failed to collect S3 statistics: {e}")

        # Process paid domains
        for domain in paid_resources['paid_domains']:
            try:
                unified_domain = self._create_unified_domain(domain)
                if unified_domain:
                    unified_resources.append(unified_domain)
            except Exception as e:
                self.logger.warning(f"Failed to process paid domain {domain.get('name', 'unknown')}: {e}")

        self.logger.info(f"Unified {len(unified_resources)} paid resources")
        return unified_resources, cpu_statistics, memory_statistics, s3_statistics

    def _validate_costs_against_billing(self, total_calculated_cost: float, account_billing: Dict) -> Dict[str, Any]:
        """Phase 4: Validate calculated costs against account billing"""
        validation = {
            'valid': False,
            'total_calculated': total_calculated_cost,
            'account_daily_rate': account_billing.get('daily_rate', 0),
            'difference': 0,
            'tolerance_percent': 5.0,  # Allow 5% variance
            'issues': []
        }

        account_daily_rate = account_billing.get('daily_rate', 0)
        difference = abs(total_calculated_cost - account_daily_rate)
        tolerance_amount = account_daily_rate * (validation['tolerance_percent'] / 100)

        validation['difference'] = difference

        if difference <= tolerance_amount:
            validation['valid'] = True
            self.logger.info(f"Cost validation passed: calculated {total_calculated_cost:.2f}, account {account_daily_rate:.2f}, difference {difference:.2f}")
        else:
            validation['valid'] = False
            validation['issues'].append(f"Cost mismatch: calculated {total_calculated_cost:.2f}, account {account_daily_rate:.2f}, difference {difference:.2f}")
            self.logger.warning(f"Cost validation failed: {validation['issues'][0]}")

        return validation

    def _attach_performance_stats_to_resources(self, unified_resources: List[ProviderResource], 
                                             cpu_statistics: Dict, memory_statistics: Dict):
        """Attach CPU/memory statistics to VPS resources for UI display"""
        try:
            cpu_stats_data = cpu_statistics.get('cpu_statistics', {})
            memory_stats_data = memory_statistics.get('memory_statistics', {})
            
            for resource in unified_resources:
                if resource.resource_type == 'server':
                    vps_id = resource.resource_id
                    
                    # Attach CPU statistics
                    if vps_id in cpu_stats_data:
                        cpu_data = cpu_stats_data[vps_id].get('cpu_statistics', {})
                        if cpu_data:
                            resource.tags.update({
                                'cpu_avg_usage': str(cpu_data.get('avg_cpu_usage', 0)),
                                'cpu_max_usage': str(cpu_data.get('max_cpu_usage', 0)),
                                'cpu_min_usage': str(cpu_data.get('min_cpu_usage', 0)),
                                'cpu_trend': str(cpu_data.get('trend', 0)),
                                'cpu_performance_tier': cpu_data.get('performance_tier', 'unknown'),
                                'cpu_data_points': str(cpu_data.get('data_points', 0)),
                                'cpu_timestamp': cpu_data.get('timestamp', ''),
                                'cpu_raw_data': json.dumps(cpu_data.get('raw_data', {}))
                            })
                    
                    # Attach memory statistics
                    if vps_id in memory_stats_data:
                        memory_data = memory_stats_data[vps_id].get('memory_statistics', {})
                        if memory_data:
                            resource.tags.update({
                                'memory_avg_usage_mb': str(memory_data.get('avg_memory_usage_mb', 0)),
                                'memory_max_usage_mb': str(memory_data.get('max_memory_usage_mb', 0)),
                                'memory_min_usage_mb': str(memory_data.get('min_memory_usage_mb', 0)),
                                'memory_usage_percent': str(memory_data.get('memory_usage_percent', 0)),
                                'memory_trend': str(memory_data.get('trend', 0)),
                                'memory_tier': memory_data.get('memory_tier', 'unknown'),
                                'memory_data_points': str(memory_data.get('data_points', 0)),
                                'memory_timestamp': memory_data.get('timestamp', ''),
                                'memory_raw_data': json.dumps(memory_data.get('raw_data', {}))
                            })
                            
            self.logger.info(f"Attached performance statistics to {len(unified_resources)} resources")
            
        except Exception as e:
            self.logger.warning(f"Failed to attach performance statistics: {e}")

    def _attach_s3_stats_to_resources(self, unified_resources: List[ProviderResource], s3_statistics: Dict):
        """Attach S3 statistics to storage resources for UI display"""
        try:
            s3_stats_data = s3_statistics.get('s3_statistics', {})
            global_quota = s3_statistics.get('global_quota', {})
            
            for resource in unified_resources:
                if resource.resource_type == 'storage':
                    service_id = resource.resource_id
                    
                    # Attach S3 statistics
                    if service_id in s3_stats_data:
                        stats_data = s3_stats_data[service_id]
                        traffic_stats = stats_data.get('traffic_statistics', {})
                        request_stats = stats_data.get('request_statistics', {})
                        
                        # Process traffic statistics
                        if traffic_stats:
                            data_rx = traffic_stats.get('data_rx', {})
                            data_tx = traffic_stats.get('data_tx', {})
                            
                            if data_rx and data_tx:
                                rx_values = data_rx.get('value', [])
                                tx_values = data_tx.get('value', [])
                                
                                # Calculate totals and averages
                                total_rx = sum(rx_values) if rx_values else 0
                                total_tx = sum(tx_values) if tx_values else 0
                                total_traffic = total_rx + total_tx
                                
                                resource.tags.update({
                                    's3_total_traffic_bytes': str(total_traffic),
                                    's3_rx_bytes': str(total_rx),
                                    's3_tx_bytes': str(total_tx),
                                    's3_traffic_period': s3_statistics.get('period', 'MONTH'),
                                    's3_traffic_raw_data': json.dumps(traffic_stats)
                                })
                        
                        # Process request statistics
                        if request_stats:
                            method_get = request_stats.get('method_get', {})
                            method_post = request_stats.get('method_post', {})
                            method_put = request_stats.get('method_put', {})
                            method_delete = request_stats.get('method_delete', {})
                            
                            # Calculate total requests
                            total_requests = 0
                            if method_get:
                                total_requests += sum(method_get.get('value', []))
                            if method_post:
                                total_requests += sum(method_post.get('value', []))
                            if method_put:
                                total_requests += sum(method_put.get('value', []))
                            if method_delete:
                                total_requests += sum(method_delete.get('value', []))
                            
                            resource.tags.update({
                                's3_total_requests': str(total_requests),
                                's3_requests_period': s3_statistics.get('period', 'MONTH'),
                                's3_requests_raw_data': json.dumps(request_stats)
                            })
                        
                        # Attach global quota data
                        if global_quota:
                            resource.tags.update({
                                's3_quota_used_bytes': str(global_quota.get('used_size', 0)),
                                's3_quota_raw_data': json.dumps(global_quota)
                            })
                            
            self.logger.info(f"Attached S3 statistics to {len([r for r in unified_resources if r.resource_type == 'storage'])} storage resources")
            
        except Exception as e:
            self.logger.warning(f"Failed to attach S3 statistics: {e}")

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

        # Use daily cost for consistency across all resources
        daily_cost = float(vps_data.get('daily_cost', 0.0))
        monthly_cost = float(vps_data.get('monthly_cost', 0.0))

        # Use daily cost if available, otherwise convert monthly to daily
        if daily_cost > 0:
            effective_cost = daily_cost
            billing_period = 'daily'
        elif monthly_cost > 0:
            effective_cost = monthly_cost / 30.0  # Convert to daily
            billing_period = 'daily'
        else:
            effective_cost = 0.0
            billing_period = 'monthly'

        unified_resource = ProviderResource(
            resource_id=str(vps_data.get('id', '')),
            resource_name=vps_data.get('name', vps_data.get('display_name', 'Unknown')),
            resource_type='server',
            service_name='Compute',
            region='global',  # Beget is global
            status=unified_status,
            effective_cost=effective_cost,
            currency='RUB',
            billing_period=billing_period,
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
        # Calculate costs - domains are typically annual, so convert to daily
        monthly_cost = domain_data.get('monthly_cost', 0.0)
        renewal_cost = domain_data.get('renewal_cost', 0.0)

        # Use renewal cost as primary, convert to daily for consistency
        if renewal_cost > 0:
            # Assume renewal cost is annual, convert to daily
            daily_cost = renewal_cost / 365.0
            billing_period = 'daily'
            effective_cost = daily_cost
        elif monthly_cost > 0:
            # Use monthly cost, convert to daily
            daily_cost = monthly_cost / 30.0
            billing_period = 'daily'
            effective_cost = daily_cost
        else:
            # No cost - this shouldn't happen for paid domains
            effective_cost = 0.0
            billing_period = 'monthly'

        unified_resource = ProviderResource(
            resource_id=str(domain_data.get('id', domain_data.get('name', ''))),
            resource_name=domain_data.get('name', domain_data.get('fqdn', 'Unknown')),
            resource_type='domain',
            service_name='DNS',
            region='global',
            status=domain_data.get('status', 'active'),
            effective_cost=effective_cost,
            currency='RUB',
            billing_period=billing_period,
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

    def _create_unified_cloud_service(self, service_data: Dict[str, Any]) -> ProviderResource:
        """Create unified resource for cloud service"""
        service_type = service_data.get('service_type', 'Cloud Service')
        service_name = service_data.get('name', 'Unknown')

        # Determine the appropriate resource type based on service type
        if service_type == 'Database':
            resource_type = 'database'
            service_name_display = 'Database'
        elif service_type == 'Storage':
            resource_type = 'storage'
            service_name_display = 'Storage'
        else:
            resource_type = 'cloud_service'
            service_name_display = 'Cloud Service'

        # Calculate effective cost
        daily_cost = float(service_data.get('daily_cost', 0))
        
        # For S3 storage with zero cost, set a minimal cost to indicate it's tracked
        if service_type == 'Storage' and daily_cost == 0:
            daily_cost = 0.01  # Minimal cost to indicate resource is tracked
        
        unified_resource = ProviderResource(
            resource_id=str(service_data.get('id', service_data.get('name', ''))),
            resource_name=service_name,
            resource_type=resource_type,
            service_name=service_name_display,
            region='global',  # Beget is global
            status=service_data.get('status', 'unknown'),
            effective_cost=daily_cost,
            currency='RUB',
            billing_period='daily',  # Cloud services use daily billing
            provider_config=service_data,
            provider_type='beget'
        )

        # Add cloud service-specific tags
        unified_resource.tags.update({
            'service_type': service_data.get('service_type', 'Unknown'),
            'cloud_service_id': str(service_data.get('id', '')),
            'region': service_data.get('region', 'global'),
            'manage_enabled': str(service_data.get('manage_enabled', False)),
            'daily_cost': str(service_data.get('daily_cost', 0)),
            'monthly_cost': str(service_data.get('monthly_cost', 0))
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

    def get_pricing_data(self) -> List[Dict[str, Any]]:
        """
        Get current pricing data from Beget for price comparison
        
        Returns standardized pricing data for cross-provider comparison
        """
        try:
            self.logger.info("Starting Beget pricing data collection")
            
            pricing_data = []
            
            # Get VPS pricing from the API
            try:
                vps_plans = self.client.get_vps_plans()
                if vps_plans:
                    for plan in vps_plans:
                        pricing_record = self._create_vps_pricing_record(plan)
                        if pricing_record:
                            pricing_data.append(pricing_record)
                            
            except Exception as e:
                self.logger.warning(f"Failed to get VPS pricing: {e}")
            
            # Add manual pricing data for known Beget offerings
            # This is based on current Beget pricing as of 2025
            manual_pricing = self._get_manual_beget_pricing()
            pricing_data.extend(manual_pricing)
            
            self.logger.info(f"Collected {len(pricing_data)} pricing records from Beget")
            return pricing_data
            
        except Exception as e:
            self.logger.error(f"Failed to get Beget pricing data: {e}")
            return []

    def _create_vps_pricing_record(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create standardized pricing record from VPS plan data"""
        try:
            # Extract specifications
            config = plan_data.get('configuration', {})
            cpu_cores = config.get('cpu_count', 0)
            ram_mb = config.get('memory', 0)
            ram_gb = ram_mb / 1024 if ram_mb > 0 else 0
            disk_gb = config.get('disk_gb', 0)
            
            # Extract pricing
            monthly_cost = float(plan_data.get('monthly_cost', 0))
            daily_cost = monthly_cost / 30 if monthly_cost > 0 else 0
            
            if monthly_cost <= 0:
                return None  # Skip free plans
                
            return {
                'provider': 'beget',
                'resource_type': 'server',
                'provider_sku': plan_data.get('name', f'VPS-{cpu_cores}C-{int(ram_gb)}G'),
                'region': 'global',
                'cpu_cores': int(cpu_cores),
                'ram_gb': int(ram_gb),
                'storage_gb': int(disk_gb),
                'storage_type': 'SSD',
                'extended_specs': {
                    'bandwidth_gb': plan_data.get('bandwidth_gb', 0),
                    'software': plan_data.get('software', ''),
                    'backup_enabled': plan_data.get('backup_enabled', False)
                },
                'hourly_cost': daily_cost / 24,
                'monthly_cost': monthly_cost,
                'currency': 'RUB',
                'confidence_score': 0.9,  # High confidence from API
                'source': 'billing_api',
                'source_url': 'https://beget.com/vps',
                'notes': f"Beget VPS plan: {plan_data.get('name', 'Unknown')}"
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to create VPS pricing record: {e}")
            return None

    def _get_manual_beget_pricing(self) -> List[Dict[str, Any]]:
        """Get manual pricing data for Beget offerings not available via API"""
        # Based on current Beget pricing (October 2025)
        # These are fallback prices when API data is not available
        
        return [
            # VPS Plans
            {
                'provider': 'beget',
                'resource_type': 'server',
                'provider_sku': 'VPS-S',
                'region': 'global',
                'cpu_cores': 1,
                'ram_gb': 1,
                'storage_gb': 10,
                'storage_type': 'SSD',
                'extended_specs': {
                    'bandwidth_gb': 1000,
                    'backup_enabled': True
                },
                'hourly_cost': 0.83,  # 25 RUB/day / 24
                'monthly_cost': 600.0,
                'currency': 'RUB',
                'confidence_score': 0.7,  # Manual data
                'source': 'manual',
                'source_url': 'https://beget.com/vps',
                'notes': 'Beget VPS-S plan (manual pricing)'
            },
            {
                'provider': 'beget',
                'resource_type': 'server',
                'provider_sku': 'VPS-M',
                'region': 'global',
                'cpu_cores': 2,
                'ram_gb': 2,
                'storage_gb': 20,
                'storage_type': 'SSD',
                'extended_specs': {
                    'bandwidth_gb': 2000,
                    'backup_enabled': True
                },
                'hourly_cost': 1.67,  # 50 RUB/day / 24
                'monthly_cost': 1200.0,
                'currency': 'RUB',
                'confidence_score': 0.7,
                'source': 'manual',
                'source_url': 'https://beget.com/vps',
                'notes': 'Beget VPS-M plan (manual pricing)'
            },
            {
                'provider': 'beget',
                'resource_type': 'server',
                'provider_sku': 'VPS-L',
                'region': 'global',
                'cpu_cores': 2,
                'ram_gb': 4,
                'storage_gb': 50,
                'storage_type': 'SSD',
                'extended_specs': {
                    'bandwidth_gb': 5000,
                    'backup_enabled': True
                },
                'hourly_cost': 2.33,  # 70 RUB/day / 24
                'monthly_cost': 2100.0,
                'currency': 'RUB',
                'confidence_score': 0.7,
                'source': 'manual',
                'source_url': 'https://beget.com/vps',
                'notes': 'Beget VPS-L plan (manual pricing)'
            },
            {
                'provider': 'beget',
                'resource_type': 'server',
                'provider_sku': 'VPS-XL',
                'region': 'global',
                'cpu_cores': 4,
                'ram_gb': 8,
                'storage_gb': 100,
                'storage_type': 'SSD',
                'extended_specs': {
                    'bandwidth_gb': 10000,
                    'backup_enabled': True
                },
                'hourly_cost': 4.17,  # 125 RUB/day / 24
                'monthly_cost': 3750.0,
                'currency': 'RUB',
                'confidence_score': 0.7,
                'source': 'manual',
                'source_url': 'https://beget.com/vps',
                'notes': 'Beget VPS-XL plan (manual pricing)'
            },
            
            # Storage Plans
            {
                'provider': 'beget',
                'resource_type': 'storage',
                'provider_sku': 'S3-Storage',
                'region': 'global',
                'cpu_cores': None,
                'ram_gb': None,
                'storage_gb': 1000,  # Per GB pricing
                'storage_type': 'SSD',
                'extended_specs': {
                    'storage_type': 'S3-compatible',
                    'api_access': True
                },
                'hourly_cost': 0.0,  # Pay-per-use
                'monthly_cost': 50.0,  # Per GB per month
                'currency': 'RUB',
                'confidence_score': 0.8,
                'source': 'manual',
                'source_url': 'https://beget.com/cloud',
                'notes': 'Beget S3 storage (per GB pricing)'
            }
        ]
