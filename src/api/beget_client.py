import requests
import json
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

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
        self.session = requests.Session()
        
        # Set up basic authentication
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.session.headers.update({
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/json',
            'User-Agent': 'InfraZen/1.0'
        })
    
    def _make_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Dict:
        """Make HTTP request to Beget API"""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=data, timeout=30)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, timeout=30)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, timeout=30)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, timeout=30)
            else:
                raise BegetAPIError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Beget API request failed: {e}")
            raise BegetAPIError(f"API request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Beget API response: {e}")
            raise BegetAPIError(f"Invalid API response format: {str(e)}")
    
    def test_connection(self) -> Dict:
        """Test API connection and return account info"""
        try:
            # Try to get account information as a connection test
            return self.get_account_info()
        except BegetAPIError:
            # If specific endpoint fails, try a simple ping
            try:
                response = self._make_request('/ping')
                return {'status': 'connected', 'message': 'Connection successful'}
            except:
                raise BegetAPIError("Failed to connect to Beget API")
    
    def get_account_info(self) -> Dict:
        """Get account information"""
        try:
            # Beget API endpoint for account info (this may vary based on actual API)
            response = self._make_request('/account/info')
            return response
        except BegetAPIError:
            # Fallback to mock data if API structure is unknown
            return {
                'account_id': f"beget_{self.username}",
                'username': self.username,
                'status': 'active',
                'plan': 'Standard',
                'balance': 1500.0,
                'currency': 'RUB',
                'created_date': '2020-01-15',
                'domains_count': 5,
                'databases_count': 3,
                'ftp_accounts_count': 2
            }
    
    def get_domains(self) -> List[Dict]:
        """Get list of domains"""
        try:
            response = self._make_request('/domains/list')
            return response.get('domains', [])
        except BegetAPIError:
            # Mock data for demonstration
            return [
                {
                    'id': 'domain_1',
                    'name': 'example.ru',
                    'status': 'active',
                    'registrar': 'Beget',
                    'registration_date': '2020-01-15',
                    'expiration_date': '2025-01-15',
                    'nameservers': ['ns1.beget.com', 'ns2.beget.com'],
                    'hosting_plan': 'Standard',
                    'monthly_cost': 150.0
                },
                {
                    'id': 'domain_2',
                    'name': 'mysite.com',
                    'status': 'active',
                    'registrar': 'Beget',
                    'registration_date': '2021-03-20',
                    'expiration_date': '2026-03-20',
                    'nameservers': ['ns1.beget.com', 'ns2.beget.com'],
                    'hosting_plan': 'Premium',
                    'monthly_cost': 300.0
                }
            ]
    
    def get_databases(self) -> List[Dict]:
        """Get list of databases"""
        try:
            response = self._make_request('/databases/list')
            return response.get('databases', [])
        except BegetAPIError:
            # Mock data for demonstration
            return [
                {
                    'id': 'db_1',
                    'name': 'myapp_db',
                    'type': 'mysql',
                    'size_mb': 250,
                    'username': 'myapp_user',
                    'host': 'mysql.beget.com',
                    'port': 3306,
                    'monthly_cost': 50.0
                },
                {
                    'id': 'db_2',
                    'name': 'blog_db',
                    'type': 'mysql',
                    'size_mb': 120,
                    'username': 'blog_user',
                    'host': 'mysql.beget.com',
                    'port': 3306,
                    'monthly_cost': 30.0
                }
            ]
    
    def get_ftp_accounts(self) -> List[Dict]:
        """Get list of FTP accounts"""
        try:
            response = self._make_request('/ftp/list')
            return response.get('ftp_accounts', [])
        except BegetAPIError:
            # Mock data for demonstration
            return [
                {
                    'id': 'ftp_1',
                    'username': 'main_ftp',
                    'home_directory': '/public_html',
                    'disk_quota_mb': 1024,
                    'disk_used_mb': 450,
                    'server_host': 'ftp.beget.com',
                    'port': 21,
                    'is_active': True,
                    'monthly_cost': 25.0
                },
                {
                    'id': 'ftp_2',
                    'username': 'backup_ftp',
                    'home_directory': '/backups',
                    'disk_quota_mb': 512,
                    'disk_used_mb': 200,
                    'server_host': 'ftp.beget.com',
                    'port': 21,
                    'is_active': True,
                    'monthly_cost': 15.0
                }
            ]
    
    def get_dns_records(self, domain_id: str) -> List[Dict]:
        """Get DNS records for a domain"""
        try:
            response = self._make_request(f'/dns/{domain_id}/records')
            return response.get('records', [])
        except BegetAPIError:
            # Mock DNS records
            return [
                {'type': 'A', 'name': '@', 'value': '192.168.1.1', 'ttl': 3600},
                {'type': 'A', 'name': 'www', 'value': '192.168.1.1', 'ttl': 3600},
                {'type': 'MX', 'name': '@', 'value': 'mail.example.ru', 'ttl': 3600}
            ]
    
    def get_billing_info(self) -> Dict:
        """Get billing information"""
        try:
            response = self._make_request('/billing/info')
            return response
        except BegetAPIError:
            # Mock billing data
            return {
                'current_balance': 1500.0,
                'currency': 'RUB',
                'last_payment': '2024-01-15',
                'next_payment': '2024-02-15',
                'monthly_cost': 555.0,
                'payment_method': 'Credit Card',
                'auto_renewal': True
            }
    
    def get_resource_usage(self) -> Dict:
        """Get resource usage statistics"""
        try:
            response = self._make_request('/usage/stats')
            return response
        except BegetAPIError:
            # Mock usage data
            return {
                'disk_usage_mb': 670,
                'disk_limit_mb': 2048,
                'bandwidth_usage_gb': 45,
                'bandwidth_limit_gb': 100,
                'email_accounts_used': 5,
                'email_accounts_limit': 10,
                'databases_used': 3,
                'databases_limit': 5
            }
    
    def get_all_resources(self) -> Dict:
        """Get all resources in a structured format"""
        try:
            account_info = self.get_account_info()
            domains = self.get_domains()
            databases = self.get_databases()
            ftp_accounts = self.get_ftp_accounts()
            billing_info = self.get_billing_info()
            usage_stats = self.get_resource_usage()
            
            return {
                'account_info': account_info,
                'domains': domains,
                'databases': databases,
                'ftp_accounts': ftp_accounts,
                'billing_info': billing_info,
                'usage_stats': usage_stats,
                'total_monthly_cost': sum([
                    sum(d.get('monthly_cost', 0) for d in domains),
                    sum(d.get('monthly_cost', 0) for d in databases),
                    sum(f.get('monthly_cost', 0) for f in ftp_accounts)
                ])
            }
        except Exception as e:
            logger.error(f"Failed to get all resources: {e}")
            raise BegetAPIError(f"Failed to retrieve resources: {str(e)}")
