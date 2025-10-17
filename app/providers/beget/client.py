"""
Beget API Client for InfraZen
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime, date
import requests
import json
import base64

logger = logging.getLogger(__name__)

class BegetAPIError(Exception):
    """Custom exception for Beget API errors"""
    pass

def decode_jwt_payload(token: str) -> Dict:
    """Decode JWT token payload without verification (for extracting user info)"""
    try:
        # Split token into parts
        parts = token.split('.')
        if len(parts) != 3:
            return {}
        
        # Decode payload (second part)
        payload = parts[1]
        # Add padding if needed
        payload += '=' * (4 - len(payload) % 4)
        decoded_bytes = base64.urlsafe_b64decode(payload)
        return json.loads(decoded_bytes.decode('utf-8'))
    except Exception as e:
        logger.error(f"Failed to decode JWT token: {e}")
        return {}

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
        print(f"DEBUG: Authenticating user {self.username} with Beget API at {self.api_url}/v1/auth")
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
            response = requests.post(url, json=auth_data, headers=headers, timeout=60)
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            
            # DEBUG: Log the full API response
            logger.info(f"DEBUG: Full Beget API response: {result}")
            
            # Check if authentication was successful
            if 'token' in result:
                self.access_token = result.get('token')
                self.refresh_token = result.get('refresh_token')
                logger.info(f"Successfully authenticated with Beget API - Token: {self.access_token[:20]}..." if self.access_token else "No token")
                return True
            elif result.get('error'):
                error_msg = result.get('error', 'Authentication failed')
                logger.error(f"Authentication failed: {error_msg}")
                return False
            else:
                logger.error(f"Authentication failed: Unknown response format - {result}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {e}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
            return False
    
    
    def test_connection(self) -> Dict:
        """Test API connection by authenticating"""
        print(f"DEBUG: test_connection called for user {self.username}")
        
        # Development bypass for test credentials
        if self.username in ['test', 'demo', 'colaiswv'] and self.password in ['test', 'demo']:
            print(f"DEBUG: Using development bypass for test credentials")
            return {
                'status': 'success',
                'message': 'Connection test successful (development mode)',
                'account_info': {
                    'customer_login': self.username,
                    'customer_id': '12345',
                    'domains_count': 2,
                    'databases_count': 1,
                    'ftp_accounts_count': 1
                },
                'api_status': 'connected'
            }
        
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
        """Extract account info from authentication token"""
        logger.info(f"DEBUG: Authentication successful for user {self.username}")
        logger.info(f"DEBUG: Access token received: {self.access_token[:20]}..." if self.access_token else "No access token")
        
        # Decode JWT token to get user info
        user_info = {}
        if self.access_token:
            jwt_payload = decode_jwt_payload(self.access_token)
            user_info = {
                'customer_id': jwt_payload.get('customerId', ''),
                'customer_login': jwt_payload.get('customerLogin', self.username),
                'environment': jwt_payload.get('env', 'web'),
                'ip_address': jwt_payload.get('ip', ''),
                'token_expires': jwt_payload.get('exp', 0)
            }
            logger.info(f"DEBUG: Extracted user info from JWT: {user_info}")
        
        return {
            'account_id': f"beget_{self.username}",
            'username': self.username,
            'customer_id': user_info.get('customer_id', ''),
            'customer_login': user_info.get('customer_login', self.username),
            'status': 'active',
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
            logger.error(f"DEBUG: Beget API call failed: {e}")
            # Re-raise the error - no mock data for real users
            raise e
    
    def get_detailed_account_info(self) -> Dict:
        """Get detailed account information using direct API endpoint"""
        try:
            url = "https://api.beget.com/api/user/getAccountInfo"
            params = {
                'login': self.username,
                'passwd': self.password,
                'output_format': 'json'
            }
            
            logger.info(f"Fetching detailed account info from: {url}")
            
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Account info API response: {result}")
                
                # Check for authentication errors
                if result.get('status') == 'error':
                    if result.get('error_code') == 'AUTH_ERROR':
                        logger.warning("Authentication failed for account info")
                        return {'error': 'Authentication failed', 'status': 'error'}
                    else:
                        logger.error(f"API Error: {result.get('error_text', 'Unknown error')}")
                        return {'error': result.get('error_text', 'Unknown error'), 'status': 'error'}
                
                # Process successful response
                if 'answer' in result:
                    account_data = result['answer']
                    return self._process_account_info(account_data)
                elif 'result' in result:
                    return self._process_account_info(result['result'])
                else:
                    logger.warning(f"Unexpected account info response format: {result}")
                    return {'error': 'Unexpected response format', 'status': 'error'}
                    
            except Exception as e:
                logger.error(f"Account info API failed: {e}")
                return {'error': str(e), 'status': 'error'}
                
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return {'error': str(e), 'status': 'error'}
    
    def _process_account_info(self, account_data: Dict) -> Dict:
        """Process account information data from Beget API response"""
        try:
            # Extract the actual result data from the nested structure
            result_data = account_data.get('result', account_data)
            
            processed_info = {
                # Account details
                'account_id': self.username,  # Use the authenticated username
                'account_status': 'active' if result_data.get('user_balance', 0) > 0 else 'blocked',
                'account_type': result_data.get('plan_name', 'Unknown'),
                'plan_name': result_data.get('plan_name', 'Unknown'),
                
                # Billing information
                'balance': result_data.get('user_balance', 0),
                'currency': 'RUB',
                'daily_rate': result_data.get('user_rate_current', 0),
                'monthly_rate': result_data.get('user_rate_month', 0),
                'yearly_rate': result_data.get('user_rate_year', 0),
                'is_yearly_plan': result_data.get('user_is_year_plan', '0') == '1',
                'days_to_block': result_data.get('user_days_to_block', 0),
                
                # Service limits and usage
                'service_limits': {
                    'domains': {
                        'used': result_data.get('user_domains', 0),
                        'limit': result_data.get('plan_domain', 0)
                    },
                    'sites': {
                        'used': result_data.get('user_sites', 0),
                        'limit': result_data.get('plan_site', 0)
                    },
                    'mysql': {
                        'used': result_data.get('user_mysqlsize', 0),
                        'limit': result_data.get('plan_mysql', 0)
                    },
                    'ftp': {
                        'used': result_data.get('user_ftp', 0),
                        'limit': result_data.get('plan_ftp', 0)
                    },
                    'mail': {
                        'used': result_data.get('user_mail', 0),
                        'limit': result_data.get('plan_mail', 0)
                    },
                    'quota': {
                        'used': result_data.get('user_quota', 0),
                        'limit': result_data.get('plan_quota', 0)
                    }
                },
                
                # Server information
                'server_info': {
                    'name': result_data.get('server_name', ''),
                    'cpu': result_data.get('server_cpu_name', ''),
                    'memory_total_mb': result_data.get('server_memory', 0),
                    'memory_used_mb': result_data.get('server_memorycurrent', 0),
                    'load_average': result_data.get('server_loadaverage', 0),
                    'uptime_days': result_data.get('server_uptime', 0)
                },
                
                # Software versions
                'software_versions': {
                    'apache': result_data.get('server_apache_version', ''),
                    'nginx': result_data.get('server_nginx_version', ''),
                    'mysql': result_data.get('server_mysql_version', ''),
                    'php': result_data.get('server_php_version', ''),
                    'python': result_data.get('server_python_version', ''),
                    'perl': result_data.get('server_perl_version', '')
                },
                
                # Security and access
                'security': {
                    'bash_access': result_data.get('user_bash', ''),
                    'control_panel': result_data.get('plan_cp', 0) > 0,
                    'api_enabled': True  # If we can call the API, it's enabled
                },
                
                # FinOps insights
                'finops_insights': {
                    'daily_cost': result_data.get('user_rate_current', 0),
                    'monthly_cost': result_data.get('user_rate_month', 0),
                    'yearly_cost': result_data.get('user_rate_year', 0),
                    'current_balance': result_data.get('user_balance', 0),
                    'days_until_block': result_data.get('user_days_to_block', 0),
                    'cost_per_day': result_data.get('user_rate_current', 0)
                },
                
                'raw_data': result_data  # Keep original for debugging
            }
            
            logger.info(f"Processed account info: {processed_info}")
            return processed_info
            
        except Exception as e:
            logger.error(f"Error processing account info: {e}")
            return {'error': f'Processing error: {str(e)}', 'status': 'error'}
    
    def get_vps_servers(self) -> List[Dict]:
        """Get list of VPS servers from Beget API"""
        try:
            if not self.access_token:
                self.authenticate()
            
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'User-Agent': 'InfraZen/1.0'
            }
            
            # Use documented Beget API endpoint for VPS servers
            url = f"{self.api_url}/v1/vps/server/list"
            
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Successfully retrieved VPS servers from {url}")
                
                # Process the VPS servers data
                if 'vps' in result:
                    return self._process_vps_servers_data(result['vps'])
                elif 'servers' in result:
                    return self._process_vps_servers_data(result['servers'])
                elif isinstance(result, list):
                    return self._process_vps_servers_data(result)
                else:
                    logger.warning(f"Unexpected VPS servers response format: {result}")
                    return []
                    
            except Exception as e:
                logger.error(f"VPS servers endpoint failed: {e}")
                return []
            
        except Exception as e:
            logger.error(f"Failed to get VPS servers: {e}")
            return []
    
    def _process_vps_servers_data(self, servers_data: List[Dict]) -> List[Dict]:
        """Process raw VPS servers data from API"""
        processed_servers = []
        
        for server in servers_data:
            config = server.get('configuration', {})
            processed_servers.append({
                'id': server.get('id'),
                'name': server.get('display_name', server.get('hostname')),
                'status': server.get('status', 'active'),
                'ip_address': server.get('ip_address'),
                'hostname': server.get('hostname'),
                'os': server.get('software', {}).get('display_name', 'Unknown'),
                'cpu_cores': config.get('cpu_count', 0),
                'ram_mb': config.get('memory', 0),
                'disk_gb': config.get('disk_size', 0) / 1024 if config.get('disk_size') else 0,  # Convert MB to GB
                'disk_used_gb': int(server.get('disk_used', 0)) / 1024 if server.get('disk_used') else 0,
                'disk_left_gb': int(server.get('disk_left', 0)) / 1024 if server.get('disk_left') else 0,
                'bandwidth_gb': config.get('bandwidth_public', 0),
                'location': server.get('region', 'Unknown'),
                'created_at': server.get('date_create'),
                'monthly_cost': config.get('price_month', 0),
                'daily_cost': config.get('price_day', 0),
                'currency': 'RUB',
                'type': 'vps',
                'software': server.get('software', {}).get('name', 'Unknown'),
                'software_domain': server.get('software_domain', ''),
                'description': server.get('description', '')
            })
        
        return processed_servers

    def get_domains(self) -> List[Dict]:
        """Get list of domains from Beget API using real endpoint"""
        try:
            
            # Use the real Beget API endpoint with login/password authentication
            url = "https://api.beget.com/api/domain/getList"
            params = {
                'login': self.username,
                'passwd': self.password,
                'output_format': 'json'
            }
            
            logger.info(f"Fetching domains from real Beget API: {url}")
            
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"API Response: {result}")
                
                # Check for authentication errors
                if result.get('status') == 'error':
                    if result.get('error_code') == 'AUTH_ERROR':
                        logger.warning("Authentication failed - returning empty list")
                        return []
                    else:
                        logger.error(f"API Error: {result.get('error_text', 'Unknown error')}")
                        return []
                
                # Process the domains data based on Beget API response format
                if 'answer' in result:
                    domains_data = result['answer']
                    if isinstance(domains_data, list):
                        return self._process_domains_data(domains_data)
                    elif isinstance(domains_data, dict) and 'domains' in domains_data:
                        return self._process_domains_data(domains_data['domains'])
                    elif isinstance(domains_data, dict) and 'result' in domains_data:
                        return self._process_domains_data(domains_data['result'])
                    else:
                        logger.warning(f"Unexpected domains response format: {domains_data}")
                        return []
                elif 'result' in result:
                    return self._process_domains_data(result['result'])
                elif 'domains' in result:
                    return self._process_domains_data(result['domains'])
                elif isinstance(result, list):
                    return self._process_domains_data(result)
                else:
                    logger.warning(f"Unexpected API response format: {result}")
                    return []
                    
            except Exception as e:
                logger.error(f"Real domain API failed: {e}")
                # Return empty list instead of mock data
                logger.warning("Returning empty list due to API failure")
                return []
            
        except Exception as e:
            logger.error(f"Failed to get domains: {e}")
            return []
    
    def _process_domains_data(self, domains_data: List[Dict]) -> List[Dict]:
        """Process raw domains data from API with FinOps-relevant information"""
        processed_domains = []
        
        for domain in domains_data:
            # Handle real Beget API format
            domain_name = domain.get('fqdn', domain.get('name', domain.get('domain_name', 'unknown')))
            registration_date = domain.get('date_register', domain.get('registration_date', domain.get('created_at')))
            expiration_date = domain.get('date_expire', domain.get('expiration_date', domain.get('expires')))
            auto_renewal = domain.get('auto_renew', domain.get('auto_renewal', False))
            is_under_control = domain.get('is_under_control', 0)
            registrar = domain.get('registrar', 'Beget')
            
            # Determine domain status based on real data
            if expiration_date and expiration_date != 'null':
                status = 'active'
            elif is_under_control == 1:
                status = 'active'
            else:
                status = 'inactive'
            
            # Calculate costs based on domain type
            if registrar == 'beget' and expiration_date:
                # Registered domain
                monthly_cost = 0.0  # No monthly cost for domains
                renewal_cost = 50.0  # Estimated renewal cost
            else:
                # Subdomain or free domain
                monthly_cost = 0.0
                renewal_cost = 0.0
            
            processed_domains.append({
                'id': domain.get('id', f"domain_{len(processed_domains)}"),
                'name': domain_name,
                'status': status,
                'registrar': registrar,
                'registration_date': registration_date,
                'expiration_date': expiration_date,
                'nameservers': domain.get('nameservers', []),
                'dns_records': domain.get('dns_records', []),
                'hosting_plan': domain.get('hosting_plan', 'Standard'),
                'registration_cost': domain.get('registration_cost', 0.0),
                'renewal_cost': renewal_cost,
                'monthly_cost': monthly_cost,
                'currency': 'RUB',
                # FinOps-relevant domain metrics
                'domain_type': 'registered' if expiration_date and expiration_date != 'null' else 'subdomain',
                'auto_renewal': auto_renewal,
                'privacy_protection': domain.get('privacy_protection', False),
                'ssl_certificate': domain.get('ssl_certificate', False),
                'dns_management': domain.get('dns_management', True),
                'email_forwarding': domain.get('email_forwarding', False),
                'subdomains_count': len(domain.get('subdomains', [])),
                'dns_records_count': len(domain.get('dns_records', [])),
                'last_updated': domain.get('date_add', domain.get('last_updated', domain.get('updated_at'))),
                'domain_age_days': self._calculate_domain_age(registration_date),
                'days_until_expiry': self._calculate_days_until_expiry(expiration_date),
                'is_under_control': is_under_control,
                'registrar_status': domain.get('registrar_status', 'unknown'),
                'register_order_status': domain.get('register_order_status', 'unknown')
            })
        
        return processed_domains
    
    def _calculate_domain_age(self, registration_date: str) -> int:
        """Calculate domain age in days"""
        try:
            if not registration_date:
                return 0
            from datetime import datetime
            reg_date = datetime.fromisoformat(registration_date.replace('Z', '+00:00'))
            return (datetime.now() - reg_date).days
        except:
            return 0
    
    def _calculate_days_until_expiry(self, expiration_date: str) -> int:
        """Calculate days until domain expiry"""
        try:
            if not expiration_date:
                return 0
            from datetime import datetime
            exp_date = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
            return (exp_date - datetime.now()).days
        except:
            return 0
    
    def get_domain_info(self, domain_name: str) -> Dict:
        """Get detailed domain information using real Beget API"""
        try:
            # Use the real Beget API endpoint for domain info
            url = "https://api.beget.com/api/domain/getInfo"
            params = {
                'login': self.username,
                'passwd': self.password,
                'output_format': 'json',
                'domain': domain_name
            }
            
            logger.info(f"Fetching domain info for {domain_name} from real API")
            
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Successfully retrieved domain info for {domain_name}")
                
                # Process the domain info based on Beget API response format
                if 'answer' in result:
                    return self._process_domain_info(result['answer'])
                else:
                    return self._process_domain_info(result)
                    
            except Exception as e:
                logger.error(f"Real domain info API failed: {e}")
                return {}
            
        except Exception as e:
            logger.error(f"Failed to get domain info: {e}")
            return {}
    
    def _process_domain_info(self, domain_info: Dict) -> Dict:
        """Process detailed domain information for FinOps analysis"""
        return {
            'domain_name': domain_info.get('domain_name', ''),
            'status': domain_info.get('status', 'unknown'),
            'registrar': domain_info.get('registrar', 'Beget'),
            'registration_date': domain_info.get('registration_date', ''),
            'expiration_date': domain_info.get('expiration_date', ''),
            'nameservers': domain_info.get('nameservers', []),
            'dns_records': domain_info.get('dns_records', []),
            'auto_renewal': domain_info.get('auto_renewal', False),
            'privacy_protection': domain_info.get('privacy_protection', False),
            'ssl_certificate': domain_info.get('ssl_certificate', False),
            'dns_management': domain_info.get('dns_management', False),
            'email_forwarding': domain_info.get('email_forwarding', False),
            'subdomains': domain_info.get('subdomains', []),
            'domain_age_days': self._calculate_domain_age(domain_info.get('registration_date')),
            'days_until_expiry': self._calculate_days_until_expiry(domain_info.get('expiration_date')),
            'renewal_cost': domain_info.get('renewal_cost', 0),
            'monthly_cost': domain_info.get('monthly_cost', 0),
            'currency': 'RUB'
        }
    
    
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
    
    
    def get_all_resources(self) -> Dict:
        """Get all resources in a comprehensive format with FinOps analysis"""
        try:
            # Get all available information
            account_info = self.get_account_info(use_mock_data=False)
            vps_servers = self.get_vps_servers()  # Get VPS servers first
            domains = self.get_domains()  # Enhanced domain data
            databases = self.get_databases()
            ftp_accounts = self.get_ftp_accounts()
            email_accounts = self.get_email_accounts()
            billing_info = self.get_billing_info()
            usage_stats = self.get_resource_usage()
            
            # Calculate total costs with enhanced domain costs
            total_monthly_cost = sum([
                sum(v.get('monthly_cost', 0) for v in vps_servers),  # Include VPS costs
                sum(d.get('monthly_cost', 0) for d in domains),  # Domain costs
                sum(d.get('renewal_cost', 0) for d in domains),  # Domain renewal costs
                sum(d.get('monthly_cost', 0) for d in databases),
                sum(f.get('monthly_cost', 0) for f in ftp_accounts),
                sum(e.get('monthly_cost', 0) for e in email_accounts)
            ])
            
            # Calculate FinOps metrics for domains
            domain_metrics = self._calculate_domain_metrics(domains)
            
            return {
                'account_info': account_info,
                'vps_servers': vps_servers,  # Include VPS servers
                'domains': domains,  # Enhanced domain data
                'databases': databases,
                'ftp_accounts': ftp_accounts,
                'email_accounts': email_accounts,
                'billing_info': billing_info,
                'usage_stats': usage_stats,
                'total_monthly_cost': total_monthly_cost,
                'domain_metrics': domain_metrics,  # FinOps domain analysis
                'sync_timestamp': datetime.now().isoformat(),
                'resource_counts': {
                    'vps_servers': len(vps_servers),  # Include VPS count
                    'domains': len(domains),
                    'databases': len(databases),
                    'ftp_accounts': len(ftp_accounts),
                    'email_accounts': len(email_accounts)
                }
            }
        except Exception as e:
            logger.error(f"Failed to get all resources: {e}")
            raise BegetAPIError(f"Failed to retrieve resources: {str(e)}")
    
    def _calculate_domain_metrics(self, domains: List[Dict]) -> Dict:
        """Calculate FinOps metrics for domain analysis"""
        if not domains:
            return {}
        
        total_domains = len(domains)
        active_domains = len([d for d in domains if d.get('status') == 'active'])
        expiring_soon = len([d for d in domains if d.get('days_until_expiry', 0) < 30])
        auto_renewal_enabled = len([d for d in domains if d.get('auto_renewal', False)])
        ssl_enabled = len([d for d in domains if d.get('ssl_certificate', False)])
        
        total_domain_cost = sum(d.get('monthly_cost', 0) + d.get('renewal_cost', 0) for d in domains)
        avg_domain_age = sum(d.get('domain_age_days', 0) for d in domains) / total_domains if total_domains > 0 else 0
        
        return {
            'total_domains': total_domains,
            'active_domains': active_domains,
            'expiring_soon': expiring_soon,
            'auto_renewal_enabled': auto_renewal_enabled,
            'ssl_enabled': ssl_enabled,
            'total_domain_cost': total_domain_cost,
            'avg_domain_age_days': avg_domain_age,
            'cost_per_domain': total_domain_cost / total_domains if total_domains > 0 else 0
        }
    
    def get_vps_servers_new_api(self) -> List[Dict]:
        """Get VPS servers using the new VPS API endpoint"""
        try:
            if not self.access_token:
                self.authenticate()
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'User-Agent': 'InfraZen/1.0',
                'Accept': 'application/json, text/plain, */*'
            }
            
            url = f"{self.api_url}/v1/vps/server/list"
            
            logger.info(f"Fetching VPS servers from new API: {url}")
            
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Successfully retrieved VPS servers from new API")
                
                if 'vps' in result:
                    return self._process_vps_servers_new_api(result['vps'])
                else:
                    logger.warning(f"Unexpected VPS API response format: {result}")
                    return []
                    
            except Exception as e:
                logger.error(f"VPS API failed: {e}")
                return []
            
        except Exception as e:
            logger.error(f"Failed to get VPS servers from new API: {e}")
            return []
    
    def _process_vps_servers_new_api(self, vps_servers: List[Dict]) -> List[Dict]:
        """Process VPS servers data from new API"""
        processed_servers = []
        
        for vps in vps_servers:
            config = vps.get('configuration', {})
            software = vps.get('software', {})
            
            # Extract admin credentials if available
            admin_credentials = {}
            if 'field_value' in software:
                for field in software['field_value']:
                    if field.get('variable') == 'beget_n8n_password':
                        admin_credentials['admin_password'] = field.get('value', '')
                    elif field.get('variable') == 'beget_email':
                        admin_credentials['admin_email'] = field.get('value', '')
            
            processed_servers.append({
                'id': vps.get('id'),
                'name': vps.get('display_name', vps.get('hostname')),
                'status': vps.get('status', 'unknown'),
                'ip_address': vps.get('ip_address'),
                'hostname': vps.get('hostname'),
                'region': vps.get('region', 'unknown'),
                'cpu_cores': config.get('cpu_count', 0),
                'ram_mb': config.get('memory', 0),
                'disk_gb': config.get('disk_size', 0) / 1024 if config.get('disk_size') else 0,  # Convert MB to GB
                'disk_used_gb': int(vps.get('disk_used', 0)) / 1024 if vps.get('disk_used') else 0,
                'disk_left_gb': int(vps.get('disk_left', 0)) / 1024 if vps.get('disk_left') else 0,
                'bandwidth_gb': config.get('bandwidth_public', 0),
                'location': vps.get('region', 'Unknown'),
                'created_at': vps.get('date_create'),
                'monthly_cost': config.get('price_month', 0),
                'daily_cost': config.get('price_day', 0),
                'currency': 'RUB',
                'type': 'vps',
                'software': software.get('display_name', 'Unknown'),
                'software_version': software.get('version', 'Unknown'),
                'software_url': software.get('address', ''),
                'admin_credentials': admin_credentials,
                'ssh_access_allowed': vps.get('beget_ssh_access_allowed', False),
                'manage_enabled': vps.get('manage_enabled', False),
                'description': vps.get('description', ''),
                'technical_domain': vps.get('technical_domain', ''),
                'software_domain': vps.get('software_domain', '')
            })
        
        return processed_servers

    def sync_resources(self) -> Dict:
        """Comprehensive sync of all resources with Beget API using both endpoints"""
        try:
            logger.info("Starting comprehensive Beget resource sync with dual endpoints")
            
            # Authenticate first
            if not self.authenticate():
                raise BegetAPIError("Failed to authenticate for sync")
            
            sync_result = {
                'status': 'success',
                'message': 'Successfully synced resources from Beget',
                'sync_timestamp': datetime.now().isoformat(),
                'account_sync': {'status': 'pending'},
                'vps_sync': {'status': 'pending'},
                'domains_sync': {'status': 'pending'},
                'resources': {},
                'errors': []
            }
            
            # Sync 1: Account Information (existing endpoint)
            try:
                logger.info("Syncing account information...")
                account_info = self.get_detailed_account_info()
                domains = self.get_domains()
                
                sync_result['account_sync'] = {
                    'status': 'success',
                    'account_info': account_info,
                    'domains': domains,
                    'domains_count': len(domains)
                }
                sync_result['resources']['account_info'] = account_info
                sync_result['resources']['domains'] = domains
                
                logger.info(f"Account sync successful: {len(domains)} domains")
                
            except Exception as e:
                error_msg = f"Account sync failed: {str(e)}"
                logger.error(error_msg)
                sync_result['account_sync'] = {'status': 'error', 'error': error_msg}
                sync_result['errors'].append(error_msg)
            
            # Sync 2: VPS Information (new endpoint)
            try:
                logger.info("Syncing VPS information...")
                vps_servers = self.get_vps_servers_new_api()
                
                # Collect CPU and memory statistics for all VPS servers
                logger.info("Collecting CPU statistics for VPS servers...")
                cpu_statistics = self.get_all_vps_cpu_statistics(vps_servers, period='DAY')
                
                logger.info("Collecting memory statistics for VPS servers...")
                memory_statistics = self.get_all_vps_memory_statistics(vps_servers, period='DAY')
                
                sync_result['vps_sync'] = {
                    'status': 'success',
                    'vps_servers': vps_servers,
                    'vps_count': len(vps_servers),
                    'cpu_statistics': cpu_statistics,
                    'memory_statistics': memory_statistics
                }
                sync_result['resources']['vps_servers'] = vps_servers
                sync_result['resources']['vps_cpu_statistics'] = cpu_statistics
                sync_result['resources']['vps_memory_statistics'] = memory_statistics
                
                # Calculate VPS costs
                total_daily_cost = sum(vps.get('daily_cost', 0) for vps in vps_servers)
                total_monthly_cost = sum(vps.get('monthly_cost', 0) for vps in vps_servers)
                
                sync_result['vps_sync']['total_daily_cost'] = total_daily_cost
                sync_result['vps_sync']['total_monthly_cost'] = total_monthly_cost
                
                logger.info(f"VPS sync successful: {len(vps_servers)} VPS instances, {total_daily_cost} RUB/day")
                logger.info(f"CPU statistics collected for {cpu_statistics.get('vps_with_cpu_data', 0)} VPS servers")
                
            except Exception as e:
                error_msg = f"VPS sync failed: {str(e)}"
                logger.error(error_msg)
                sync_result['vps_sync'] = {'status': 'error', 'error': error_msg}
                sync_result['errors'].append(error_msg)
            
            # Sync 3: Cloud Services (new endpoint)
            try:
                logger.info("Syncing cloud services...")
                cloud_services = self.get_cloud_services()
                
                sync_result['cloud_sync'] = {
                    'status': 'success',
                    'cloud_services': cloud_services,
                    'cloud_count': len(cloud_services)
                }
                sync_result['resources']['cloud_services'] = cloud_services
                
                # Calculate cloud services costs
                total_daily_cost = sum(service.get('daily_cost', 0) for service in cloud_services)
                total_monthly_cost = sum(service.get('monthly_cost', 0) for service in cloud_services)
                
                sync_result['cloud_sync']['total_daily_cost'] = total_daily_cost
                sync_result['cloud_sync']['total_monthly_cost'] = total_monthly_cost
                
                logger.info(f"Cloud services sync successful: {len(cloud_services)} cloud services, {total_daily_cost} RUB/day")
                
            except Exception as e:
                error_msg = f"Cloud services sync failed: {str(e)}"
                logger.error(error_msg)
                sync_result['cloud_sync'] = {'status': 'error', 'error': error_msg}
                sync_result['errors'].append(error_msg)
            
            # Sync 4: Additional resources (existing endpoints)
            try:
                logger.info("Syncing additional resources...")
                databases = self.get_databases()
                ftp_accounts = self.get_ftp_accounts()
                email_accounts = self.get_email_accounts()
                
                sync_result['domains_sync'] = {
                    'status': 'success',
                    'databases': databases,
                    'ftp_accounts': ftp_accounts,
                    'email_accounts': email_accounts,
                    'databases_count': len(databases),
                    'ftp_count': len(ftp_accounts),
                    'email_count': len(email_accounts)
                }
                sync_result['resources']['databases'] = databases
                sync_result['resources']['ftp_accounts'] = ftp_accounts
                sync_result['resources']['email_accounts'] = email_accounts
                
                logger.info(f"Additional resources sync successful: {len(databases)} databases, {len(ftp_accounts)} FTP, {len(email_accounts)} email")
                
            except Exception as e:
                error_msg = f"Additional resources sync failed: {str(e)}"
                logger.error(error_msg)
                sync_result['domains_sync'] = {'status': 'error', 'error': error_msg}
                sync_result['errors'].append(error_msg)
            
            # Calculate overall statistics
            total_resources = (
                len(sync_result['resources'].get('vps_servers', [])) +
                len(sync_result['resources'].get('domains', [])) +
                len(sync_result['resources'].get('cloud_services', [])) +
                len(sync_result['resources'].get('databases', [])) +
                len(sync_result['resources'].get('ftp_accounts', [])) +
                len(sync_result['resources'].get('email_accounts', []))
            )
            
            sync_result['total_resources'] = total_resources
            sync_result['message'] = f'Successfully synced {total_resources} resources from Beget'
            
            # Determine overall status
            if sync_result['errors']:
                sync_result['status'] = 'partial_success'
                sync_result['message'] += f' (with {len(sync_result["errors"])} errors)'
            else:
                sync_result['status'] = 'success'
            
            logger.info(f"Sync completed: {total_resources} resources, {len(sync_result['errors'])} errors")
            return sync_result
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            raise BegetAPIError(f"Sync failed: {str(e)}")
    
    def get_cloud_services(self) -> List[Dict]:
        """Get cloud services from Beget Cloud API"""
        try:
            if not self.access_token:
                self.authenticate()
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json, text/plain, */*',
                'User-Agent': 'InfraZen/1.0'
            }
            
            url = f"{self.api_url}/v1/cloud"
            
            logger.info(f"Fetching cloud services from: {url}")
            
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Successfully retrieved cloud services from {url}")
                
                # Process the cloud services data
                if 'service' in result:
                    return self._process_cloud_services_data(result['service'])
                else:
                    logger.warning(f"Unexpected cloud services response format: {result}")
                    return []
                    
            except Exception as e:
                logger.error(f"Cloud services endpoint failed: {e}")
                return []
            
        except Exception as e:
            logger.error(f"Failed to get cloud services: {e}")
            return []
    
    def _process_cloud_services_data(self, services_data: List[Dict]) -> List[Dict]:
        """Process raw cloud services data from API"""
        processed_services = []
        
        for service in services_data:
            service_type = service.get('type', 'Unknown')
            service_id = service.get('id')
            service_name = service.get('display_name', 'Unknown')
            status = service.get('status', 'unknown')
            region = service.get('region', 'unknown')
            
            # Extract cost information
            daily_cost = service.get('price_day', 0)
            monthly_cost = service.get('price_month', 0)
            
            # Process based on service type
            if service_type == 'MYSQL5':
                processed_service = self._process_mysql_service(service, service_id, service_name, status, region, daily_cost, monthly_cost)
            elif service_type == 'S_3':
                processed_service = self._process_s3_service(service, service_id, service_name, status, region, daily_cost, monthly_cost)
            else:
                # Generic cloud service
                processed_service = {
                    'id': service_id,
                    'name': service_name,
                    'type': 'Cloud Service',
                    'service_type': service_type,
                    'status': status,
                    'region': region,
                    'daily_cost': daily_cost,
                    'monthly_cost': monthly_cost,
                    'currency': 'RUB',
                    'created_at': service.get('created_at'),
                    'manage_enabled': service.get('manage_enabled', False),
                    'provider_config': service
                }
            
            processed_services.append(processed_service)
        
        return processed_services
    
    def _process_mysql_service(self, service: Dict, service_id: str, service_name: str, status: str, region: str, daily_cost: float, monthly_cost: float) -> Dict:
        """Process MySQL cloud database service"""
        mysql_config = service.get('mysql5', {})
        configuration = mysql_config.get('configuration', {})
        address_info = mysql_config.get('address_info', {})
        
        # Extract public and private IPs
        public_ips = []
        private_ips = []
        if address_info:
            public_ips = [ip.get('ip') for ip in address_info.get('public', []) if ip.get('ip')]
            private_ips = [ip.get('ip') for ip in address_info.get('private', []) if ip.get('ip')]
        
        return {
            'id': service_id,
            'name': service_name,
            'type': 'MySQL Database',
            'service_type': 'Database',
            'status': status,
            'region': region,
            'daily_cost': daily_cost,
            'monthly_cost': monthly_cost,
            'currency': 'RUB',
            'created_at': service.get('created_at'),
            'manage_enabled': service.get('manage_enabled', False),
            
            # MySQL-specific configuration
            'mysql_config': {
                'version': configuration.get('version', '5.7'),
                'display_version': configuration.get('display_version', '5.7'),
                'cpu_count': configuration.get('cpu_count', 0),
                'memory_mb': configuration.get('memory', 0),
                'disk_size_mb': configuration.get('disk_size', 0),
                'host': mysql_config.get('host', ''),
                'port': mysql_config.get('port', 3306),
                'pma_url': mysql_config.get('pma_url', ''),
                'disk_used_bytes': mysql_config.get('disk_used', 0),
                'disk_left_bytes': mysql_config.get('disk_left', 0),
                'read_only': mysql_config.get('read_only', False),
                'public_ips': public_ips,
                'private_ips': private_ips
            },
            
            'provider_config': service
        }
    
    def _process_s3_service(self, service: Dict, service_id: str, service_name: str, status: str, region: str, daily_cost: float, monthly_cost: float) -> Dict:
        """Process S3-compatible storage service"""
        s3_config = service.get('s3', {})
        
        return {
            'id': service_id,
            'name': service_name,
            'type': 'S3 Storage',
            'service_type': 'Storage',
            'status': status,
            'region': region,
            'daily_cost': daily_cost,
            'monthly_cost': monthly_cost,
            'currency': 'RUB',
            'created_at': service.get('created_at'),
            'manage_enabled': service.get('manage_enabled', False),
            
            # S3-specific configuration
            's3_config': {
                'public': s3_config.get('public', False),
                'access_key': s3_config.get('access_key', ''),
                'secret_key': s3_config.get('secret_key', ''),
                'fqdn': s3_config.get('fqdn', ''),
                'quota_used_size': s3_config.get('quota_used_size', 0),
                'ftp': s3_config.get('ftp', {}),
                'sftp': s3_config.get('sftp', {}),
                'cors': s3_config.get('cors', [])
            },
            
            'provider_config': service
        }
    
    def get_s3_quota(self) -> Dict:
        """Get S3 storage quota information"""
        try:
            if not self.access_token:
                self.authenticate()
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json, text/plain, */*',
                'User-Agent': 'InfraZen/1.0'
            }
            
            url = f"{self.api_url}/v1/cloud/s3/quota"
            
            logger.info(f"Fetching S3 quota from: {url}")
            
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Successfully retrieved S3 quota from {url}")
                
                return result
                    
            except Exception as e:
                logger.error(f"Failed to fetch S3 quota from {url}: {e}")
                return {}
                
        except Exception as e:
            logger.error(f"S3 quota fetch failed: {e}")
            return {}

    def get_s3_traffic_statistics(self, service_id: str, period: str = 'MONTH') -> Dict:
        """Get S3 traffic usage statistics"""
        try:
            if not self.access_token:
                self.authenticate()
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json, text/plain, */*',
                'User-Agent': 'InfraZen/1.0'
            }
            
            url = f"{self.api_url}/v1/cloud/s3/{service_id}/statistic/traffic-usage"
            params = {
                'service_id': service_id,
                'period': period
            }
            
            logger.info(f"Fetching S3 traffic statistics from: {url}")
            
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Successfully retrieved S3 traffic statistics from {url}")
                
                return result
                    
            except Exception as e:
                logger.error(f"Failed to fetch S3 traffic statistics from {url}: {e}")
                return {}
                
        except Exception as e:
            logger.error(f"S3 traffic statistics fetch failed: {e}")
            return {}

    def get_s3_request_statistics(self, service_id: str, period: str = 'MONTH') -> Dict:
        """Get S3 request count statistics"""
        try:
            if not self.access_token:
                self.authenticate()
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json, text/plain, */*',
                'User-Agent': 'InfraZen/1.0'
            }
            
            url = f"{self.api_url}/v1/cloud/s3/{service_id}/statistic/count-request"
            params = {
                'service_id': service_id,
                'period': period
            }
            
            logger.info(f"Fetching S3 request statistics from: {url}")
            
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Successfully retrieved S3 request statistics from {url}")
                
                return result
                    
            except Exception as e:
                logger.error(f"Failed to fetch S3 request statistics from {url}: {e}")
                return {}
                
        except Exception as e:
            logger.error(f"S3 request statistics fetch failed: {e}")
            return {}

    def get_all_s3_statistics(self, s3_services: List[Dict], period: str = 'MONTH') -> Dict:
        """Get comprehensive S3 statistics for all services"""
        try:
            s3_statistics = {}
            quota_data = self.get_s3_quota()
            
            for service in s3_services:
                service_id = service.get('id')
                service_name = service.get('name', 'Unknown')
                
                if service_id:
                    try:
                        traffic_stats = self.get_s3_traffic_statistics(service_id, period)
                        request_stats = self.get_s3_request_statistics(service_id, period)
                        
                        s3_statistics[service_id] = {
                            'vps_name': service_name,
                            'service_id': service_id,
                            'traffic_statistics': traffic_stats,
                            'request_statistics': request_stats,
                            'quota_data': quota_data
                        }
                        
                        logger.debug(f"Collected S3 statistics for {service_name}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to collect S3 statistics for {service_name}: {e}")
            
            return {
                'total_s3_services': len(s3_services),
                's3_with_statistics': len(s3_statistics),
                's3_statistics': s3_statistics,
                'global_quota': quota_data,
                'period': period
            }
            
        except Exception as e:
            logger.error(f"Failed to collect S3 statistics: {e}")
            return {}
    
    def get_vps_cpu_statistics(self, vps_id: str, period: str = 'HOUR') -> Dict:
        """Get CPU statistics for a specific VPS"""
        try:
            if not self.access_token:
                self.authenticate()
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json, text/plain, */*',
                'User-Agent': 'InfraZen/1.0'
            }
            
            url = f"{self.api_url}/v1/vps/statistic/cpu/{vps_id}"
            params = {
                'id': vps_id,
                'period': period
            }
            
            logger.info(f"Fetching CPU statistics for VPS {vps_id} with period {period}")
            
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Successfully retrieved CPU statistics for VPS {vps_id}")
                
                # Process the CPU statistics data
                if 'cpu' in result:
                    return self._process_cpu_statistics_data(result['cpu'], vps_id, period)
                else:
                    logger.warning(f"Unexpected CPU statistics response format: {result}")
                    return {}
                    
            except Exception as e:
                logger.error(f"CPU statistics endpoint failed for VPS {vps_id}: {e}")
                return {}
            
        except Exception as e:
            logger.error(f"Failed to get CPU statistics for VPS {vps_id}: {e}")
            return {}
    
    def _process_cpu_statistics_data(self, cpu_data: Dict, vps_id: str, period: str) -> Dict:
        """Process CPU statistics data from API"""
        try:
            dates = cpu_data.get('date', [])
            values = cpu_data.get('value', [])
            
            if not dates or not values or len(dates) != len(values):
                logger.warning(f"Invalid CPU data structure for VPS {vps_id}")
                return {}
            
            # Calculate statistics
            cpu_values = [float(v) for v in values if v is not None]
            
            if not cpu_values:
                logger.warning(f"No valid CPU values for VPS {vps_id}")
                return {}
            
            # Calculate metrics
            avg_cpu = sum(cpu_values) / len(cpu_values)
            max_cpu = max(cpu_values)
            min_cpu = min(cpu_values)
            
            # Calculate trend (simple linear trend)
            if len(cpu_values) > 1:
                first_half = cpu_values[:len(cpu_values)//2]
                second_half = cpu_values[len(cpu_values)//2:]
                trend = (sum(second_half) / len(second_half)) - (sum(first_half) / len(first_half))
            else:
                trend = 0
            
            # Determine performance tier
            if avg_cpu < 20:
                performance_tier = 'low'
            elif avg_cpu < 50:
                performance_tier = 'medium'
            else:
                performance_tier = 'high'
            
            return {
                'vps_id': vps_id,
                'period': period,
                'data_points': len(cpu_values),
                'avg_cpu_usage': round(avg_cpu, 2),
                'max_cpu_usage': round(max_cpu, 2),
                'min_cpu_usage': round(min_cpu, 2),
                'trend': round(trend, 2),
                'performance_tier': performance_tier,
                'raw_data': {
                    'dates': dates,
                    'values': values
                },
                'timestamp': dates[-1] if dates else None,  # Last timestamp
                'collection_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing CPU statistics for VPS {vps_id}: {e}")
            return {}
    
    def get_all_vps_cpu_statistics(self, vps_servers: List[Dict], period: str = 'HOUR') -> Dict:
        """Get CPU statistics for all VPS servers"""
        try:
            cpu_statistics = {}
            
            for vps in vps_servers:
                vps_id = vps.get('id')
                vps_name = vps.get('name', 'Unknown')
                
                if vps_id:
                    logger.info(f"Collecting CPU statistics for VPS: {vps_name} ({vps_id})")
                    cpu_data = self.get_vps_cpu_statistics(vps_id, period)
                    
                    if cpu_data:
                        cpu_statistics[vps_id] = {
                            'vps_name': vps_name,
                            'cpu_statistics': cpu_data
                        }
                    else:
                        logger.warning(f"No CPU data collected for VPS {vps_name}")
                else:
                    logger.warning(f"No VPS ID found for VPS: {vps_name}")
            
            return {
                'total_vps': len(vps_servers),
                'vps_with_cpu_data': len(cpu_statistics),
                'period': period,
                'cpu_statistics': cpu_statistics,
                'collection_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to collect CPU statistics for all VPS: {e}")
            return {}
    
    def get_vps_memory_statistics(self, vps_id: str, period: str = 'HOUR') -> Dict:
        """Get memory statistics for a specific VPS"""
        try:
            if not self.access_token:
                self.authenticate()
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json, text/plain, */*',
                'User-Agent': 'InfraZen/1.0'
            }
            
            url = f"{self.api_url}/v1/vps/statistic/memory/{vps_id}"
            params = {
                'id': vps_id,
                'period': period
            }
            
            logger.info(f"Fetching memory statistics for VPS {vps_id} with period {period}")
            
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Successfully retrieved memory statistics for VPS {vps_id}")
                
                # Process the memory statistics data
                if 'memory' in result:
                    return self._process_memory_statistics_data(result['memory'], vps_id, period)
                else:
                    logger.warning(f"Unexpected memory statistics response format: {result}")
                    return {}
                    
            except Exception as e:
                logger.error(f"Memory statistics endpoint failed for VPS {vps_id}: {e}")
                return {}
            
        except Exception as e:
            logger.error(f"Failed to get memory statistics for VPS {vps_id}: {e}")
            return {}
    
    def _process_memory_statistics_data(self, memory_data: Dict, vps_id: str, period: str) -> Dict:
        """Process memory statistics data from API"""
        try:
            dates = memory_data.get('date', [])
            values = memory_data.get('value', [])
            
            if not dates or not values or len(dates) != len(values):
                logger.warning(f"Invalid memory data structure for VPS {vps_id}")
                return {}
            
            # Calculate statistics
            memory_values = [float(v) for v in values if v is not None]
            
            if not memory_values:
                logger.warning(f"No valid memory values for VPS {vps_id}")
                return {}
            
            # Calculate metrics
            avg_memory = sum(memory_values) / len(memory_values)
            max_memory = max(memory_values)
            min_memory = min(memory_values)
            
            # Calculate trend (simple linear trend)
            if len(memory_values) > 1:
                first_half = memory_values[:len(memory_values)//2]
                second_half = memory_values[len(memory_values)//2:]
                trend = (sum(second_half) / len(second_half)) - (sum(first_half) / len(first_half))
            else:
                trend = 0
            
            # Determine memory usage tier (assuming 2GB = 2048MB total)
            total_memory_mb = 2048  # This should be fetched from VPS config
            memory_usage_percent = (avg_memory / total_memory_mb) * 100
            
            if memory_usage_percent < 30:
                memory_tier = 'low'
            elif memory_usage_percent < 70:
                memory_tier = 'medium'
            else:
                memory_tier = 'high'
            
            return {
                'vps_id': vps_id,
                'period': period,
                'data_points': len(memory_values),
                'avg_memory_usage_mb': round(avg_memory, 2),
                'max_memory_usage_mb': round(max_memory, 2),
                'min_memory_usage_mb': round(min_memory, 2),
                'memory_usage_percent': round(memory_usage_percent, 2),
                'trend': round(trend, 2),
                'memory_tier': memory_tier,
                'raw_data': {
                    'dates': dates,
                    'values': values
                },
                'timestamp': dates[-1] if dates else None,  # Last timestamp
                'collection_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing memory statistics for VPS {vps_id}: {e}")
            return {}
    
    def get_all_vps_memory_statistics(self, vps_servers: List[Dict], period: str = 'HOUR') -> Dict:
        """Get memory statistics for all VPS servers"""
        try:
            memory_statistics = {}
            
            for vps in vps_servers:
                vps_id = vps.get('id')
                vps_name = vps.get('name', 'Unknown')
                
                if vps_id:
                    logger.info(f"Collecting memory statistics for VPS: {vps_name} ({vps_id})")
                    memory_data = self.get_vps_memory_statistics(vps_id, period)
                    
                    if memory_data:
                        memory_statistics[vps_id] = {
                            'vps_name': vps_name,
                            'memory_statistics': memory_data
                        }
                    else:
                        logger.warning(f"No memory data collected for VPS {vps_name}")
                else:
                    logger.warning(f"No VPS ID found for VPS: {vps_name}")
            
            return {
                'total_vps': len(vps_servers),
                'vps_with_memory_data': len(memory_statistics),
                'period': period,
                'memory_statistics': memory_statistics,
                'collection_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to collect memory statistics for all VPS: {e}")
            return {}
    
    def logout(self):
        """Logout from Beget API"""
        self.access_token = None
        self.refresh_token = None
        logger.info("Logged out from Beget API")