"""
Selectel API client implementation
"""
import requests
import json
from typing import Dict, List, Optional, Any
# from app.providers.base.provider_base import BaseProvider


class SelectelClient:
    """Selectel API client for managing cloud resources"""
    
    def __init__(self, api_key: str, account_id: str = None, service_username: str = None, service_password: str = None):
        """
        Initialize Selectel client
        
        Args:
            api_key: Selectel API key (X-Token)
            account_id: Account ID (optional, can be retrieved from API)
            service_username: Service user username for IAM token generation
            service_password: Service user password for IAM token generation
        """
        self.api_key = api_key
        self.account_id = account_id
        self.service_username = service_username
        self.service_password = service_password
        self.base_url = "https://api.selectel.ru/vpc/resell/v2"
        self.openstack_base_url = "https://ru-3.cloud.api.selcloud.ru"
        self.session = requests.Session()
        self.session.headers.update({
            'X-Token': self.api_key,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        self._jwt_token = None
    
    def _get_iam_token(self) -> str:
        """
        Get IAM token for OpenStack API authentication using service user credentials
        
        According to Selectel documentation, OpenStack APIs require IAM tokens which
        can only be obtained using service user credentials (username/password).
        The static API key (X-Token) doesn't work with OpenStack APIs.
        
        Returns:
            IAM token string
        """
        if self._jwt_token:
            return self._jwt_token
            
        try:
            # Use service user credentials if available, otherwise fall back to account info
            if self.service_username and self.service_password:
                username = self.service_username
                account_id = self.account_id or '478587'  # Use provided account_id or default
            else:
                # Fallback: Get account info to extract username and account_id
                account_info = self.get_account_info()
                if not account_info or 'account' not in account_info:
                    raise Exception("Could not get account information and no service user credentials provided")
                
                account_data = account_info['account']
                username = account_data.get('name', '478587')  # Use account name as username
                account_id = account_data.get('name', '478587')  # Use account name as domain
            
            # Get project ID first to scope the IAM token properly
            projects = self.get_projects()
            if not projects:
                raise Exception("No projects found for this account")
            
            # Use the first project (or we could make this configurable)
            project_id = projects[0].get('id')
            project_name = projects[0].get('name')
            
            # Get IAM token using OpenStack Keystone API with service user credentials
            # Scope the token to the specific project, not the entire domain
            auth_url = 'https://cloud.api.selcloud.ru/identity/v3/auth/tokens'
            auth_data = {
                "auth": {
                    "identity": {
                        "methods": ["password"],
                        "password": {
                            "user": {
                                "name": username,
                                "domain": {
                                    "name": account_id
                                },
                                "password": self.service_password if self.service_password else self.api_key
                            }
                        }
                    },
                    "scope": {
                        "project": {
                            "id": project_id,
                            "domain": {
                                "name": account_id
                            }
                        }
                    }
                }
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            response = requests.post(auth_url, json=auth_data, headers=headers, timeout=30)
            
            if response.status_code == 201:
                # Get the token from X-Subject-Token header
                subject_token = response.headers.get('X-Subject-Token')
                if subject_token:
                    self._jwt_token = subject_token
                    return self._jwt_token
                else:
                    raise Exception("No X-Subject-Token header in response")
            else:
                # IAM token generation failed
                raise Exception(f"IAM token generation failed ({response.status_code}): {response.text[:200]}")
            
        except Exception as e:
            # IAM token generation failed
            raise Exception(f"IAM token generation failed: {str(e)}")
    
    def _get_openstack_headers(self) -> Dict[str, str]:
        """
        Get headers for OpenStack API requests
        
        Returns:
            Dict containing OpenStack API headers
        """
        iam_token = self._get_iam_token()
        return {
            'X-Auth-Token': iam_token,
            'Accept': 'application/json, text/plain, */*',
            'Openstack-Api-Version': 'compute latest',
            'Origin': 'https://my.selectel.ru',
            'Referer': 'https://my.selectel.ru/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
        }
    
    def get_openstack_servers(self) -> List[Dict[str, Any]]:
        """
        Get OpenStack servers (VMs)
        
        Returns:
            List of server dictionaries
        """
        try:
            headers = self._get_openstack_headers()
            servers_url = f'{self.openstack_base_url}/compute/v2.1/servers/detail'
            
            response = requests.get(servers_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return data.get('servers', [])
            
        except Exception as e:
            raise Exception(f"Failed to get OpenStack servers: {str(e)}")
    
    def get_openstack_volumes(self, project_id: str = None) -> List[Dict[str, Any]]:
        """
        Get OpenStack volumes
        
        Args:
            project_id: Optional project ID to scope the request
            
        Returns:
            List of volume dictionaries
        """
        try:
            headers = self._get_openstack_headers()
            headers['Openstack-Api-Version'] = 'volume latest'
            
            # Include project ID in URL if provided
            if project_id:
                volumes_url = f'{self.openstack_base_url}/volume/v3/{project_id}/volumes/detail'
            else:
                volumes_url = f'{self.openstack_base_url}/volume/v3/volumes/detail'
            
            response = requests.get(volumes_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return data.get('volumes', [])
            
        except Exception as e:
            raise Exception(f"Failed to get OpenStack volumes: {str(e)}")
    
    def get_openstack_networks(self) -> List[Dict[str, Any]]:
        """
        Get OpenStack networks
        
        Returns:
            List of network dictionaries
        """
        try:
            headers = self._get_openstack_headers()
            headers['Openstack-Api-Version'] = 'network latest'
            networks_url = f'{self.openstack_base_url}/network/v2.0/networks'
            
            response = requests.get(networks_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return data.get('networks', [])
            
        except Exception as e:
            raise Exception(f"Failed to get OpenStack networks: {str(e)}")
    
    def get_all_cloud_resources(self, project_id: str = None) -> Dict[str, Any]:
        """
        Get all actual cloud resources (servers, volumes, networks)
        
        Args:
            project_id: Optional project ID to scope the requests
            
        Returns:
            Dict containing all cloud resources
        """
        try:
            resources = {
                'servers': self.get_openstack_servers(),
                'volumes': self.get_openstack_volumes(project_id),
                'networks': self.get_openstack_networks()
            }
            return resources
            
        except Exception as e:
            return {
                'error': str(e),
                'servers': [],
                'volumes': [],
                'networks': []
            }
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the API connection and return account information
        
        Returns:
            Dict containing connection test results
        """
        try:
            # Test with /accounts endpoint
            response = self.session.get(f"{self.base_url}/accounts", timeout=30)
            
            if response.status_code == 200:
                account_data = response.json()
                account_info = account_data.get('account', {})
                
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'account_info': {
                        'name': account_info.get('name'),
                        'enabled': account_info.get('enabled'),
                        'locked': account_info.get('locked'),
                        'onboarding': account_info.get('onboarding')
                    },
                    'message': 'Connection successful'
                }
            else:
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'error': response.text,
                    'message': f'API request failed with status {response.status_code}'
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Connection failed'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Unexpected error during connection test'
            }
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information
        
        Returns:
            Dict containing account information
        """
        try:
            response = self.session.get(f"{self.base_url}/accounts", timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get account info: {str(e)}")
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """
        Get list of projects
        
        Returns:
            List of project dictionaries
        """
        try:
            response = self.session.get(f"{self.base_url}/projects", timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('projects', [])
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get projects: {str(e)}")
    
    def get_users(self) -> List[Dict[str, Any]]:
        """
        Get list of users
        
        Returns:
            List of user dictionaries
        """
        try:
            response = self.session.get(f"{self.base_url}/users", timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('users', [])
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get users: {str(e)}")
    
    def get_roles(self) -> List[Dict[str, Any]]:
        """
        Get list of roles
        
        Returns:
            List of role dictionaries
        """
        try:
            response = self.session.get(f"{self.base_url}/roles", timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('roles', [])
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get roles: {str(e)}")
    
    def get_quotas(self, project_id: str = None) -> Dict[str, Any]:
        """
        Get quotas for account or specific project
        
        Args:
            project_id: Optional project ID to get quotas for specific project
            
        Returns:
            Dict containing quota information
        """
        try:
            url = f"{self.base_url}/quotas"
            if project_id:
                url += f"/{project_id}"
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get quotas: {str(e)}")
    
    def get_resources(self, project_id: str = None) -> Dict[str, Any]:
        """
        Get resources for account or specific project
        
        Args:
            project_id: Optional project ID to get resources for specific project
            
        Returns:
            Dict containing resource information
        """
        try:
            # This endpoint might not exist yet, but we can try
            url = f"{self.base_url}/resources"
            if project_id:
                url += f"/{project_id}"
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # If endpoint doesn't exist, return empty resources
            return {'resources': []}
    
    def get_billing_info(self) -> Dict[str, Any]:
        """
        Get billing information
        
        Returns:
            Dict containing billing information
        """
        try:
            # Try different billing endpoints
            billing_endpoints = [
                f"{self.base_url}/billing",
                f"{self.base_url}/invoices",
                f"{self.base_url}/payments",
                f"{self.base_url}/transactions"
            ]
            
            for endpoint in billing_endpoints:
                try:
                    response = self.session.get(endpoint, timeout=30)
                    if response.status_code == 200:
                        return response.json()
                except:
                    continue
            
            # If no billing endpoint works, return empty
            return {'billing': {}}
            
        except Exception as e:
            return {'billing': {}, 'error': str(e)}
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics
        
        Returns:
            Dict containing usage statistics
        """
        try:
            # Try different usage endpoints
            usage_endpoints = [
                f"{self.base_url}/usage",
                f"{self.base_url}/metrics",
                f"{self.base_url}/stats"
            ]
            
            for endpoint in usage_endpoints:
                try:
                    response = self.session.get(endpoint, timeout=30)
                    if response.status_code == 200:
                        return response.json()
                except:
                    continue
            
            # If no usage endpoint works, return empty
            return {'usage': {}}
            
        except Exception as e:
            return {'usage': {}, 'error': str(e)}
    
    def get_all_resources(self) -> Dict[str, Any]:
        """
        Get all available resources and information including actual cloud resources
        
        Returns:
            Dict containing all available resource information
        """
        try:
            # Get basic account/project information
            resources = {
                'account': self.get_account_info(),
                'projects': self.get_projects(),
                'users': self.get_users(),
                'roles': self.get_roles(),
                'billing': self.get_billing_info(),
                'usage': self.get_usage_stats()
            }
            
            # Try to get quotas (might fail)
            try:
                resources['quotas'] = self.get_quotas()
            except:
                resources['quotas'] = {}
            
            # Get actual cloud resources (servers, volumes, networks)
            try:
                cloud_resources = self.get_all_cloud_resources()
                resources.update(cloud_resources)
            except Exception as e:
                resources['cloud_error'] = str(e)
                resources['servers'] = []
                resources['volumes'] = []
                resources['networks'] = []
            
            return resources
            
        except Exception as e:
            return {
                'error': str(e),
                'account': {},
                'projects': [],
                'users': [],
                'roles': [],
                'billing': {},
                'usage': {},
                'quotas': {},
                'servers': [],
                'volumes': [],
                'networks': []
            }
