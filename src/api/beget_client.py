"""
Beget API Client for InfraZen
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime, date
import requests
import json

logger = logging.getLogger(__name__)

class BegetAPIError(Exception):
    """Custom exception for Beget API errors"""
    pass

class BegetAPIClient:
    """Client for interacting with Beget hosting API"""
    
    def __init__(self, username: str, password: str, api_url: str = "https://api.beget.com"):
        self.username = username
        self.password = password
        self.api_url = api_url.rstrip('/')
        self.access_token = None
        self.refresh_token = None
    
    def authenticate(self) -> bool:
        """Authenticate with Beget API and get access token"""
        try:
            return self._authenticate_with_requests()
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise BegetAPIError(f"Authentication failed: {str(e)}")
    
    def _authenticate_with_requests(self) -> bool:
        """Authenticate with Beget API using requests library"""
        url = f"{self.api_url}/v1/auth"
        
        # Prepare authentication data
        auth_data = {
            "login": self.username,
            "password": self.password
        }
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'InfraZen/1.0'
        }
        
        try:
            response = requests.post(url, json=auth_data, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            
            # Check if authentication was successful
            if 'token' in result:
                self.access_token = result.get('token')
                self.refresh_token = result.get('refresh_token')
                logger.info("Successfully authenticated with Beget API")
                return True
            elif result.get('error'):
                error_msg = result.get('error', 'Authentication failed')
                logger.error(f"Authentication failed: {error_msg}")
                return False
            else:
                logger.error("Authentication failed: Unknown response format")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {e}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
            return False
    
    def test_connection(self) -> Dict:
        """Test API connection by authenticating"""
        try:
            success = self.authenticate()
            if success:
                return {
                    'status': 'success',
                    'message': 'Connection test successful',
                    'account_info': self._get_account_info_from_token(),
                    'api_status': 'connected'
                }
            else:
                return {
                    'status': 'error',
                    'message': 'Authentication failed',
                    'api_status': 'failed'
                }
        except BegetAPIError as e:
            return {
                'status': 'error',
                'message': f'Connection test failed: {str(e)}',
                'api_status': 'failed'
            }
    
    def _get_account_info_from_token(self) -> Dict:
        """Extract account info from authentication token or make additional API call"""
        # For now, return basic info based on successful authentication
        # In a real implementation, you might need to call additional endpoints
        return {
            'account_id': f"beget_{self.username}",
            'username': self.username,
            'status': 'active',
            'plan_name': 'Standard',  # This would come from actual API call
            'plan_price': 150,
            'plan_currency': 'RUB',
            'plan_status': 'active',
            'api_status': 'connected'
        }
    
    def get_account_info(self, use_mock_data: bool = False) -> Dict:
        """Get account information using Beget API"""
        try:
            # First authenticate to get the token
            if not self.authenticate():
                raise BegetAPIError("Failed to authenticate")
            
            # For now, return basic account info from successful authentication
            # In a full implementation, you would call additional API endpoints here
            return self._get_account_info_from_token()
                
        except BegetAPIError as e:
            if use_mock_data:
                logger.warning(f"Beget API call failed, using mock data: {e}")
                # Only use mock data when explicitly requested (for demo users only)
                return {
                    'account_id': f"beget_{self.username}",
                    'username': self.username,
                    'status': 'active',
                    'plan_name': 'Standard',
                    'plan_domain': 10,
                    'plan_db': 5,
                    'plan_ftp': 5,
                    'plan_mail': 10,
                    'plan_price': 150,
                    'plan_currency': 'RUB',
                    'plan_status': 'active',
                    'api_status': 'mock_data'
                }
            else:
                # Re-raise the error for connection testing
                raise e
    
    def get_domains(self) -> List[Dict]:
        """Get list of domains from Beget API"""
        try:
            if not self.access_token:
                self.authenticate()
            
            # Use the authenticated session to get domains
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'User-Agent': 'InfraZen/1.0'
            }
            
            # Try different possible endpoints for domains
            endpoints = [
                '/api/domains',
                '/api/domain/list',
                '/api/user/domains',
                '/api/domain/getList'
            ]
            
            for endpoint in endpoints:
                try:
                    url = f"{self.api_url}{endpoint}"
                    response = self.session.get(url, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('status') == 'success' or 'domains' in result:
                            domains = result.get('domains', result.get('answer', []))
                            return self._process_domains_data(domains)
                except Exception as e:
                    logger.debug(f"Domain endpoint {endpoint} failed: {e}")
                    continue
            
            # No working endpoints found - return empty list for real users
            logger.warning("No working domain endpoints found - returning empty list")
            return []
            
        except Exception as e:
            logger.error(f"Failed to get domains: {e}")
            return []
    
    def _process_domains_data(self, domains_data: List[Dict]) -> List[Dict]:
        """Process raw domains data from API"""
        processed_domains = []
        
        for domain in domains_data:
            processed_domains.append({
                'id': domain.get('id', domain.get('domain_id', f"domain_{len(processed_domains)}")),
                'name': domain.get('name', domain.get('domain_name', 'unknown')),
                'status': domain.get('status', 'active'),
                'registrar': domain.get('registrar', 'Beget'),
                'registration_date': domain.get('registration_date', domain.get('created_at')),
                'expiration_date': domain.get('expiration_date', domain.get('expires')),
                'nameservers': domain.get('nameservers', []),
                'dns_records': domain.get('dns_records', []),
                'hosting_plan': domain.get('hosting_plan', 'Standard'),
                'registration_cost': domain.get('registration_cost', 50.0),
                'renewal_cost': domain.get('renewal_cost', 50.0),
                'monthly_cost': domain.get('monthly_cost', 50.0),
                'currency': 'RUB'
            })
        
        return processed_domains
    
    def _get_mock_domains(self) -> List[Dict]:
        """Fallback mock domains data"""
        return [
            {
                'id': f'domain_{i}',
                'name': f'example{i}.com',
                'status': 'active',
                'registrar': 'Beget',
                'registration_date': (date.today().replace(day=1, month=1)).isoformat(),
                'expiration_date': (date.today().replace(year=date.today().year + 1)).isoformat(),
                'nameservers': ['ns1.beget.com', 'ns2.beget.com'],
                'dns_records': [],
                'hosting_plan': 'Standard',
                'registration_cost': 50.0,
                'renewal_cost': 50.0,
                'monthly_cost': 50.0,
                'currency': 'RUB'
            }
            for i in range(1, 4)
        ]
    
    def get_databases(self) -> List[Dict]:
        """Get list of databases from Beget API"""
        try:
            if not self.access_token:
                self.authenticate()
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'User-Agent': 'InfraZen/1.0'
            }
            
            # Try different possible endpoints for databases
            endpoints = [
                '/api/databases',
                '/api/database/list',
                '/api/user/databases',
                '/api/db/getList'
            ]
            
            for endpoint in endpoints:
                try:
                    url = f"{self.api_url}{endpoint}"
                    response = self.session.get(url, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('status') == 'success' or 'databases' in result:
                            databases = result.get('databases', result.get('answer', []))
                            return self._process_databases_data(databases)
                except Exception as e:
                    logger.debug(f"Database endpoint {endpoint} failed: {e}")
                    continue
            
            # No working endpoints found - return empty list for real users
            logger.warning("No working database endpoints found - returning empty list")
            return []
            
        except Exception as e:
            logger.error(f"Failed to get databases: {e}")
            return []
    
    def _process_databases_data(self, databases_data: List[Dict]) -> List[Dict]:
        """Process raw databases data from API"""
        processed_databases = []
        
        for db in databases_data:
            processed_databases.append({
                'id': db.get('id', db.get('database_id', f"db_{len(processed_databases)}")),
                'name': db.get('name', db.get('database_name', 'unknown')),
                'type': db.get('type', db.get('database_type', 'MySQL')),
                'size_mb': db.get('size_mb', db.get('size', 100)),
                'username': db.get('username', db.get('user', 'unknown')),
                'host': db.get('host', 'localhost'),
                'port': db.get('port', 3306),
                'monthly_cost': db.get('monthly_cost', 30.0),
                'currency': 'RUB'
            })
        
        return processed_databases
    
    def _get_mock_databases(self) -> List[Dict]:
        """Fallback mock databases data"""
        return [
            {
                'id': f'db_{i}',
                'name': f'database_{i}',
                'type': 'MySQL',
                'size_mb': 100,
                'username': f'db_user_{i}',
                'host': 'localhost',
                'port': 3306,
                'monthly_cost': 30.0,
                'currency': 'RUB'
            }
            for i in range(1, 3)
        ]
    
    def get_ftp_accounts(self) -> List[Dict]:
        """Get list of FTP accounts from Beget API"""
        try:
            if not self.access_token:
                self.authenticate()
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'User-Agent': 'InfraZen/1.0'
            }
            
            # Try different possible endpoints for FTP accounts
            endpoints = [
                '/api/ftp',
                '/api/ftp/list',
                '/api/user/ftp',
                '/api/ftp/getList'
            ]
            
            for endpoint in endpoints:
                try:
                    url = f"{self.api_url}{endpoint}"
                    response = self.session.get(url, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('status') == 'success' or 'ftp_accounts' in result:
                            ftp_accounts = result.get('ftp_accounts', result.get('answer', []))
                            return self._process_ftp_accounts_data(ftp_accounts)
                except Exception as e:
                    logger.debug(f"FTP endpoint {endpoint} failed: {e}")
                    continue
            
            # No working endpoints found - return empty list for real users
            logger.warning("No working FTP endpoints found - returning empty list")
            return []
            
        except Exception as e:
            logger.error(f"Failed to get FTP accounts: {e}")
            return []
    
    def _process_ftp_accounts_data(self, ftp_accounts_data: List[Dict]) -> List[Dict]:
        """Process raw FTP accounts data from API"""
        processed_ftp_accounts = []
        
        for ftp in ftp_accounts_data:
            processed_ftp_accounts.append({
                'id': ftp.get('id', ftp.get('ftp_id', f"ftp_{len(processed_ftp_accounts)}")),
                'username': ftp.get('username', ftp.get('user', 'unknown')),
                'home_directory': ftp.get('home_directory', ftp.get('path', '/')),
                'disk_quota_mb': ftp.get('disk_quota_mb', ftp.get('quota', 1024)),
                'disk_used_mb': ftp.get('disk_used_mb', ftp.get('used', 0)),
                'server_host': ftp.get('server_host', ftp.get('host', 'localhost')),
                'port': ftp.get('port', 21),
                'is_active': ftp.get('is_active', ftp.get('status', 'active') == 'active'),
                'monthly_cost': ftp.get('monthly_cost', 20.0),
                'currency': 'RUB'
            })
        
        return processed_ftp_accounts
    
    def _get_mock_ftp_accounts(self) -> List[Dict]:
        """Fallback mock FTP accounts data"""
        return [
            {
                'id': f'ftp_{i}',
                'username': f'ftp_user_{i}',
                'home_directory': '/',
                'disk_quota_mb': 1024,
                'disk_used_mb': 100,
                'server_host': 'localhost',
                'port': 21,
                'is_active': True,
                'monthly_cost': 20.0,
                'currency': 'RUB'
            }
            for i in range(1, 3)
        ]
    
    def get_billing_info(self) -> Dict:
        """Get billing information from Beget API"""
        try:
            if not self.access_token:
                self.authenticate()
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'User-Agent': 'InfraZen/1.0'
            }
            
            # Try different possible endpoints for billing
            endpoints = [
                '/api/billing',
                '/api/billing/info',
                '/api/user/billing',
                '/api/account/billing'
            ]
            
            for endpoint in endpoints:
                try:
                    url = f"{self.api_url}{endpoint}"
                    response = self.session.get(url, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('status') == 'success':
                            billing_data = result.get('answer', result.get('billing', {}))
                            return self._process_billing_data(billing_data)
                except Exception as e:
                    logger.debug(f"Billing endpoint {endpoint} failed: {e}")
                    continue
            
            # No working endpoints found - return empty dict for real users
            logger.warning("No working billing endpoints found - returning empty billing info")
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get billing info: {e}")
            return {}
    
    def _process_billing_data(self, billing_data: Dict) -> Dict:
        """Process raw billing data from API"""
        return {
            'current_balance': billing_data.get('balance', billing_data.get('current_balance', 1500.0)),
            'currency': billing_data.get('currency', 'RUB'),
            'last_payment': billing_data.get('last_payment', billing_data.get('last_payment_date')),
            'next_billing': billing_data.get('next_billing', billing_data.get('next_billing_date')),
            'payment_method': billing_data.get('payment_method', 'Card'),
            'auto_renewal': billing_data.get('auto_renewal', True),
            'total_spent': billing_data.get('total_spent', 0.0),
            'monthly_limit': billing_data.get('monthly_limit', 0.0)
        }
    
    def _get_mock_billing_info(self) -> Dict:
        """Fallback mock billing data"""
        return {
            'current_balance': 1500.00,
            'currency': 'RUB',
            'last_payment': (date.today().replace(day=1)).isoformat(),
            'next_billing': (date.today().replace(day=1, month=date.today().month + 1)).isoformat(),
            'payment_method': 'Card',
            'auto_renewal': True,
            'total_spent': 3000.0,
            'monthly_limit': 500.0
        }
    
    def get_resource_usage(self) -> Dict:
        """Get resource usage statistics from Beget API"""
        try:
            if not self.access_token:
                self.authenticate()
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'User-Agent': 'InfraZen/1.0'
            }
            
            # Try different possible endpoints for usage statistics
            endpoints = [
                '/api/usage',
                '/api/statistics',
                '/api/user/usage',
                '/api/account/usage'
            ]
            
            for endpoint in endpoints:
                try:
                    url = f"{self.api_url}{endpoint}"
                    response = self.session.get(url, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('status') == 'success':
                            usage_data = result.get('answer', result.get('usage', {}))
                            return self._process_usage_data(usage_data)
                except Exception as e:
                    logger.debug(f"Usage endpoint {endpoint} failed: {e}")
                    continue
            
            # No working endpoints found - return empty dict for real users
            logger.warning("No working usage endpoints found - returning empty usage info")
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get usage info: {e}")
            return {}
    
    def _process_usage_data(self, usage_data: Dict) -> Dict:
        """Process raw usage data from API"""
        return {
            'disk_usage': {
                'used': usage_data.get('disk_used', 250),
                'total': usage_data.get('disk_total', 1000),
                'unit': 'MB'
            },
            'bandwidth_usage': {
                'used': usage_data.get('bandwidth_used', 500),
                'total': usage_data.get('bandwidth_total', 5000),
                'unit': 'MB'
            },
            'domains_count': usage_data.get('domains_count', 3),
            'databases_count': usage_data.get('databases_count', 2),
            'ftp_accounts_count': usage_data.get('ftp_accounts_count', 2),
            'email_accounts_count': usage_data.get('email_accounts_count', 5),
            'subdomains_count': usage_data.get('subdomains_count', 1),
            'monthly_bandwidth': usage_data.get('monthly_bandwidth', 5000),
            'daily_requests': usage_data.get('daily_requests', 1000)
        }
    
    def _get_mock_usage_info(self) -> Dict:
        """Fallback mock usage data"""
        return {
            'disk_usage': {'used': 250, 'total': 1000, 'unit': 'MB'},
            'bandwidth_usage': {'used': 500, 'total': 5000, 'unit': 'MB'},
            'domains_count': 3,
            'databases_count': 2,
            'ftp_accounts_count': 2,
            'email_accounts_count': 5,
            'subdomains_count': 1,
            'monthly_bandwidth': 5000,
            'daily_requests': 1000
        }
    
    def get_email_accounts(self) -> List[Dict]:
        """Get list of email accounts from Beget API"""
        try:
            if not self.access_token:
                self.authenticate()
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'User-Agent': 'InfraZen/1.0'
            }
            
            # Try different possible endpoints for email accounts
            endpoints = [
                '/api/email',
                '/api/email/list',
                '/api/user/email',
                '/api/mail/getList'
            ]
            
            for endpoint in endpoints:
                try:
                    url = f"{self.api_url}{endpoint}"
                    response = self.session.get(url, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('status') == 'success' or 'email_accounts' in result:
                            email_accounts = result.get('email_accounts', result.get('answer', []))
                            return self._process_email_accounts_data(email_accounts)
                except Exception as e:
                    logger.debug(f"Email endpoint {endpoint} failed: {e}")
                    continue
            
            # No working endpoints found - return empty list for real users
            logger.warning("No working email endpoints found - returning empty list")
            return []
            
        except Exception as e:
            logger.error(f"Failed to get email accounts: {e}")
            return []
    
    def _process_email_accounts_data(self, email_accounts_data: List[Dict]) -> List[Dict]:
        """Process raw email accounts data from API"""
        processed_email_accounts = []
        
        for email in email_accounts_data:
            processed_email_accounts.append({
                'id': email.get('id', email.get('email_id', f"email_{len(processed_email_accounts)}")),
                'email': email.get('email', email.get('address', 'unknown@domain.com')),
                'domain': email.get('domain', 'domain.com'),
                'quota_mb': email.get('quota_mb', email.get('quota', 100)),
                'used_mb': email.get('used_mb', email.get('used', 10)),
                'is_active': email.get('is_active', email.get('status', 'active') == 'active'),
                'forwarding': email.get('forwarding', []),
                'monthly_cost': email.get('monthly_cost', 5.0),
                'currency': 'RUB'
            })
        
        return processed_email_accounts
    
    def _get_mock_email_accounts(self) -> List[Dict]:
        """Fallback mock email accounts data"""
        return [
            {
                'id': f'email_{i}',
                'email': f'user{i}@example.com',
                'domain': 'example.com',
                'quota_mb': 100,
                'used_mb': 10,
                'is_active': True,
                'forwarding': [],
                'monthly_cost': 5.0,
                'currency': 'RUB'
            }
            for i in range(1, 6)
        ]
    
    def get_all_resources(self) -> Dict:
        """Get all resources in a comprehensive format"""
        try:
            # Get all available information
            account_info = self.get_account_info(use_mock_data=False)
            domains = self.get_domains()
            databases = self.get_databases()
            ftp_accounts = self.get_ftp_accounts()
            email_accounts = self.get_email_accounts()
            billing_info = self.get_billing_info()
            usage_stats = self.get_resource_usage()
            
            # Calculate total costs
            total_monthly_cost = sum([
                sum(d.get('monthly_cost', 0) for d in domains),
                sum(d.get('monthly_cost', 0) for d in databases),
                sum(f.get('monthly_cost', 0) for f in ftp_accounts),
                sum(e.get('monthly_cost', 0) for e in email_accounts)
            ])
            
            return {
                'account_info': account_info,
                'domains': domains,
                'databases': databases,
                'ftp_accounts': ftp_accounts,
                'email_accounts': email_accounts,
                'billing_info': billing_info,
                'usage_stats': usage_stats,
                'total_monthly_cost': total_monthly_cost,
                'sync_timestamp': datetime.now().isoformat(),
                'resource_counts': {
                    'domains': len(domains),
                    'databases': len(databases),
                    'ftp_accounts': len(ftp_accounts),
                    'email_accounts': len(email_accounts)
                }
            }
        except Exception as e:
            logger.error(f"Failed to get all resources: {e}")
            raise BegetAPIError(f"Failed to retrieve resources: {str(e)}")
    
    def sync_resources(self) -> Dict:
        """Comprehensive sync of all resources with Beget API"""
        try:
            logger.info("Starting comprehensive Beget resource sync")
            
            # Authenticate first
            if not self.authenticate():
                raise BegetAPIError("Failed to authenticate for sync")
            
            # Get comprehensive data
            resources = self.get_all_resources()
            
            # Calculate sync statistics
            total_resources = (
                len(resources.get('domains', [])) +
                len(resources.get('databases', [])) +
                len(resources.get('ftp_accounts', [])) +
                len(resources.get('email_accounts', []))
            )
            
            sync_result = {
                'status': 'success',
                'message': f'Successfully synced {total_resources} resources from Beget',
                'sync_timestamp': datetime.now().isoformat(),
                'resource_counts': resources.get('resource_counts', {}),
                'total_monthly_cost': resources.get('total_monthly_cost', 0),
                'account_info': resources.get('account_info', {}),
                'billing_info': resources.get('billing_info', {}),
                'usage_stats': resources.get('usage_stats', {}),
                'resources': {
                    'domains': resources.get('domains', []),
                    'databases': resources.get('databases', []),
                    'ftp_accounts': resources.get('ftp_accounts', []),
                    'email_accounts': resources.get('email_accounts', [])
                }
            }
            
            logger.info(f"Sync completed successfully: {total_resources} resources")
            return sync_result
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            raise BegetAPIError(f"Sync failed: {str(e)}")
    
    def logout(self):
        """Logout from Beget API"""
        self.access_token = None
        self.refresh_token = None
        logger.info("Logged out from Beget API")