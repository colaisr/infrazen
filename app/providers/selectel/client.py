"""
Selectel API client implementation
"""
import requests
import json
from typing import Dict, List, Optional, Any
# from app.providers.base.provider_base import BaseProvider


class SelectelClient:
    """Selectel API client for managing cloud resources"""
    
    def __init__(self, api_key: str, account_id: str = None):
        """
        Initialize Selectel client
        
        Args:
            api_key: Selectel API key (X-Token)
            account_id: Account ID (optional, can be retrieved from API)
        """
        self.api_key = api_key
        self.account_id = account_id
        self.base_url = "https://api.selectel.ru/vpc/resell/v2"
        self.session = requests.Session()
        self.session.headers.update({
            'X-Token': self.api_key,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
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
        Get all available resources and information
        
        Returns:
            Dict containing all available resource information
        """
        try:
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
            
            # Try to get resources (might fail)
            try:
                resources['resources'] = self.get_resources()
            except:
                resources['resources'] = {}
            
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
                'resources': {}
            }
