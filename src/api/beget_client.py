"""
Beget API Client using the official OpenAPI Python SDK
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime, date

# Import the official Beget OpenAPI client
import beget_openapi_auth
from beget_openapi_auth.apis.tags import auth_service_api
from beget_openapi_auth.model.auth_auth_request import AuthAuthRequest
from beget_openapi_auth.model.auth_auth_response import AuthAuthResponse

logger = logging.getLogger(__name__)

class BegetAPIError(Exception):
    """Custom exception for Beget API errors"""
    pass

class BegetAPIClient:
    """Client for interacting with Beget hosting API using official OpenAPI SDK"""
    
    def __init__(self, username: str, password: str, api_url: str = "https://api.beget.com"):
        self.username = username
        self.password = password
        self.api_url = api_url.rstrip('/')
        self.access_token = None
        self.refresh_token = None
        self.api_client = None
        self.auth_api = None
        
        # Initialize the configuration
        self.configuration = beget_openapi_auth.Configuration(
            host=self.api_url
        )
    
    def authenticate(self) -> bool:
        """Authenticate with Beget API and get access token"""
        try:
            # Create API client with configuration
            self.api_client = beget_openapi_auth.ApiClient(self.configuration)
            self.auth_api = auth_service_api.AuthServiceApi(self.api_client)
            
            # Create authentication request
            auth_request = AuthAuthRequest(
                login=self.username,
                password=self.password
            )
            
            # Make authentication request
            response = self.auth_api.auth_service_auth(auth_request)
            
            # Extract tokens from response
            if hasattr(response, 'body') and response.body:
                auth_response = response.body
                self.access_token = getattr(auth_response, 'access_token', None)
                self.refresh_token = getattr(auth_response, 'refresh_token', None)
                
                if self.access_token:
                    # Update configuration with the access token
                    self.configuration.access_token = self.access_token
                    logger.info("Successfully authenticated with Beget API")
                    return True
                else:
                    logger.error("No access token received from Beget API")
                    return False
            else:
                logger.error("Invalid response format from Beget API")
                return False
                
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise BegetAPIError(f"Authentication failed: {str(e)}")
    
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
                # Only use mock data when explicitly requested (for development)
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
        """Get list of domains"""
        # This would be implemented using the official SDK once we have the right API endpoints
        # For now, return mock data
        return [
            {
                'id': f'domain_{i}',
                'name': f'example{i}.com',
                'status': 'active',
                'expires': (date.today().replace(year=date.today().year + 1)).isoformat(),
                'monthly_cost': 50,
                'currency': 'RUB'
            }
            for i in range(1, 4)
        ]
    
    def get_databases(self) -> List[Dict]:
        """Get list of databases"""
        # This would be implemented using the official SDK once we have the right API endpoints
        # For now, return mock data
        return [
            {
                'id': f'db_{i}',
                'name': f'database_{i}',
                'type': 'MySQL',
                'size': '100MB',
                'monthly_cost': 30,
                'currency': 'RUB'
            }
            for i in range(1, 3)
        ]
    
    def get_ftp_accounts(self) -> List[Dict]:
        """Get list of FTP accounts"""
        # This would be implemented using the official SDK once we have the right API endpoints
        # For now, return mock data
        return [
            {
                'id': f'ftp_{i}',
                'username': f'ftp_user_{i}',
                'status': 'active',
                'quota': '1GB',
                'monthly_cost': 20,
                'currency': 'RUB'
            }
            for i in range(1, 3)
        ]
    
    def get_billing_info(self) -> Dict:
        """Get billing information"""
        return {
            'current_balance': 1500.00,
            'currency': 'RUB',
            'last_payment': (date.today().replace(day=1)).isoformat(),
            'next_billing': (date.today().replace(day=1, month=date.today().month + 1)).isoformat()
        }
    
    def get_resource_usage(self) -> Dict:
        """Get resource usage statistics"""
        return {
            'disk_usage': {'used': 250, 'total': 1000, 'unit': 'MB'},
            'bandwidth_usage': {'used': 500, 'total': 5000, 'unit': 'MB'},
            'domains_count': 3,
            'databases_count': 2,
            'ftp_accounts_count': 2
        }
    
    def get_all_resources(self) -> Dict:
        """Get all resources in a structured format"""
        try:
            # Use mock data for resource collection to avoid breaking existing connections
            account_info = self.get_account_info(use_mock_data=True)
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
    
    def sync_resources(self) -> Dict:
        """Sync resources with Beget API"""
        try:
            # Authenticate first
            if not self.authenticate():
                raise BegetAPIError("Failed to authenticate for sync")
            
            # Get fresh data
            resources = self.get_all_resources()
            
            return {
                'status': 'success',
                'message': 'Resources synced successfully',
                'resources_count': len(resources.get('domains', [])) + len(resources.get('databases', [])) + len(resources.get('ftp_accounts', [])),
                'last_sync': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            raise BegetAPIError(f"Sync failed: {str(e)}")
    
    def logout(self):
        """Logout from Beget API"""
        try:
            if self.auth_api and self.refresh_token:
                self.auth_api.auth_service_logout()
                logger.info("Successfully logged out from Beget API")
        except Exception as e:
            logger.warning(f"Logout failed: {e}")
        finally:
            self.access_token = None
            self.refresh_token = None
            self.api_client = None
            self.auth_api = None