"""
Yandex Cloud API client implementation
"""
import requests
import json
import logging
import jwt
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class YandexClient:
    """Yandex Cloud API client for managing cloud resources"""
    
    def __init__(self, credentials: dict, cloud_id: str = None, folder_id: str = None):
        """
        Initialize Yandex Cloud client
        
        Args:
            credentials: Dict with credentials (service_account_key or oauth_token)
            cloud_id: Cloud ID (optional, can be discovered)
            folder_id: Folder ID (optional, can be discovered)
        """
        # Handle both dictionary credentials and legacy string formats
        if isinstance(credentials, dict):
            self.service_account_key = credentials.get('service_account_key')
            self.oauth_token = credentials.get('oauth_token')
            self.cloud_id = credentials.get('cloud_id') or cloud_id
            self.folder_id = credentials.get('folder_id') or folder_id
        elif isinstance(credentials, str):
            # Try to parse as JSON first
            try:
                creds_dict = json.loads(credentials)
                self.service_account_key = creds_dict.get('service_account_key')
                self.oauth_token = creds_dict.get('oauth_token')
                self.cloud_id = creds_dict.get('cloud_id') or cloud_id
                self.folder_id = creds_dict.get('folder_id') or folder_id
            except:
                # Treat as service account key JSON
                self.service_account_key = credentials
                self.oauth_token = None
                self.cloud_id = cloud_id
                self.folder_id = folder_id
        else:
            self.service_account_key = credentials
            self.oauth_token = None
            self.cloud_id = cloud_id
            self.folder_id = folder_id
        
        # Parse service account key if it's a JSON string
        if isinstance(self.service_account_key, str):
            try:
                self.service_account_key = json.loads(self.service_account_key)
            except:
                pass  # Already parsed or invalid
        
        self.base_url = "https://api.cloud.yandex.net"
        self.compute_url = "https://compute.api.cloud.yandex.net/compute/v1"
        self.vpc_url = "https://vpc.api.cloud.yandex.net/vpc/v1"
        self.billing_url = "https://billing.api.cloud.yandex.net/billing/v1"
        self.resource_manager_url = "https://resource-manager.api.cloud.yandex.net/resource-manager/v1"
        self.monitoring_url = "https://monitoring.api.cloud.yandex.net/monitoring/v2"
        
        self._iam_token = None
        self._iam_token_expires_at = None
        self._discovered_folders = []
        self._discovered_clouds = []
        
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def _truncate_to_microseconds(self, timestamp_str: str) -> str:
        """
        Truncate nanosecond precision to microsecond precision for Python datetime compatibility
        
        Yandex Cloud returns: 2025-10-26T04:41:00.714635763+00:00 (9 digits)
        Python expects:       2025-10-26T04:41:00.714635+00:00 (6 digits max)
        
        Args:
            timestamp_str: ISO format timestamp string
        
        Returns:
            Timestamp string with truncated fractional seconds
        """
        import re
        # Match timestamp with nanosecond precision
        # Pattern: YYYY-MM-DDTHH:MM:SS.nnnnnnnnn+HH:MM
        pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(\d+)([\+\-]\d{2}:\d{2}|Z)'
        match = re.match(pattern, timestamp_str)
        
        if match:
            date_time = match.group(1)
            fractional = match.group(2)
            timezone = match.group(3)
            
            # Truncate to 6 digits (microseconds)
            fractional_truncated = fractional[:6]
            
            return f"{date_time}.{fractional_truncated}{timezone}"
        
        # If no fractional seconds, return as-is
        return timestamp_str
    
    def _get_iam_token(self) -> str:
        """
        Get IAM token for API authentication
        
        Yandex Cloud requires IAM tokens which can be obtained via:
        1. Service Account Key (recommended for automation)
        2. OAuth token (for user accounts)
        
        Returns:
            IAM token string
        """
        # Check if we have a valid cached token
        if self._iam_token and self._iam_token_expires_at:
            # Use timezone-aware datetime for comparison
            from datetime import timezone
            now = datetime.now(timezone.utc)
            # Remove timezone info from expires_at for comparison (make both naive)
            expires_at_naive = self._iam_token_expires_at.replace(tzinfo=None)
            now_naive = datetime.now()
            if now_naive < expires_at_naive - timedelta(minutes=5):
                return self._iam_token
        
        try:
            if self.service_account_key:
                # Use service account key (JWT method)
                return self._get_iam_token_from_service_account()
            elif self.oauth_token:
                # Use OAuth token
                return self._get_iam_token_from_oauth()
            else:
                raise Exception("No credentials provided (service_account_key or oauth_token required)")
        
        except Exception as e:
            raise Exception(f"IAM token generation failed: {str(e)}")
    
    def _get_iam_token_from_service_account(self) -> str:
        """
        Generate IAM token using service account key (JWT method)
        
        This is the recommended method for automation and integrations.
        """
        try:
            if isinstance(self.service_account_key, str):
                sa_key = json.loads(self.service_account_key)
            else:
                sa_key = self.service_account_key
            
            # Extract key components
            service_account_id = sa_key.get('service_account_id')
            key_id = sa_key.get('id')
            private_key = sa_key.get('private_key')
            
            if not all([service_account_id, key_id, private_key]):
                raise Exception("Invalid service account key format")
            
            # Generate JWT
            now = int(time.time())
            payload = {
                'aud': 'https://iam.api.cloud.yandex.net/iam/v1/tokens',
                'iss': service_account_id,
                'iat': now,
                'exp': now + 3600  # Token valid for 1 hour
            }
            
            # Sign JWT with private key
            encoded_token = jwt.encode(
                payload,
                private_key,
                algorithm='PS256',
                headers={'kid': key_id}
            )
            
            # Exchange JWT for IAM token
            iam_url = 'https://iam.api.cloud.yandex.net/iam/v1/tokens'
            response = requests.post(
                iam_url,
                json={'jwt': encoded_token},
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self._iam_token = data.get('iamToken')
                
                # Calculate expiration time (tokens are valid for 12 hours)
                expires_at_str = data.get('expiresAt')
                if expires_at_str:
                    # Yandex returns timestamps with nanosecond precision (9 digits)
                    # Python's fromisoformat only supports microseconds (6 digits)
                    # Truncate to microseconds before parsing
                    expires_at_str = self._truncate_to_microseconds(expires_at_str)
                    # Parse and store as timezone-aware datetime
                    self._iam_token_expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                else:
                    # Default to 12 hours if no expiration provided
                    # Store as timezone-naive for consistency with comparison logic
                    self._iam_token_expires_at = datetime.now() + timedelta(hours=12)
                
                logger.info("✅ IAM token generated successfully using service account")
                return self._iam_token
            else:
                raise Exception(f"IAM token request failed ({response.status_code}): {response.text}")
        
        except Exception as e:
            raise Exception(f"Failed to generate IAM token from service account: {str(e)}")
    
    def _get_iam_token_from_oauth(self) -> str:
        """
        Generate IAM token using OAuth token
        
        This method is used for user accounts.
        """
        try:
            iam_url = 'https://iam.api.cloud.yandex.net/iam/v1/tokens'
            response = requests.post(
                iam_url,
                json={'yandexPassportOauthToken': self.oauth_token},
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self._iam_token = data.get('iamToken')
                
                # Calculate expiration time
                expires_at_str = data.get('expiresAt')
                if expires_at_str:
                    # Truncate nanoseconds to microseconds for Python compatibility
                    expires_at_str = self._truncate_to_microseconds(expires_at_str)
                    # Parse and store as timezone-aware datetime
                    self._iam_token_expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                else:
                    # Store as timezone-naive for consistency
                    self._iam_token_expires_at = datetime.now() + timedelta(hours=12)
                
                logger.info("✅ IAM token generated successfully using OAuth")
                return self._iam_token
            else:
                raise Exception(f"IAM token request failed ({response.status_code}): {response.text}")
        
        except Exception as e:
            raise Exception(f"Failed to generate IAM token from OAuth: {str(e)}")
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers for API requests
        
        Returns:
            Dict containing API headers
        """
        iam_token = self._get_iam_token()
        return {
            'Authorization': f'Bearer {iam_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the API connection
        
        Returns:
            Dict containing connection test results
        """
        try:
            # Test 1: IAM token generation
            iam_token = self._get_iam_token()
            if not iam_token:
                return {
                    'success': False,
                    'error': 'Failed to generate IAM token',
                    'message': 'IAM token generation failed'
                }
            
            # Test 2: List clouds to verify access
            try:
                clouds = self.list_clouds()
                
                return {
                    'success': True,
                    'status_code': 200,
                    'message': 'Connection successful',
                    'clouds_found': len(clouds),
                    'clouds': clouds[:5]  # Show first 5 clouds
                }
            except Exception as api_error:
                return {
                    'success': False,
                    'error': str(api_error),
                    'message': f'IAM token valid but API access failed: {str(api_error)}'
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Connection test failed'
            }
    
    def list_clouds(self) -> List[Dict[str, Any]]:
        """
        List all clouds accessible to the account
        
        Returns:
            List of cloud dictionaries
        """
        try:
            headers = self._get_headers()
            url = f'{self.resource_manager_url}/clouds'
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            clouds = data.get('clouds', [])
            
            self._discovered_clouds = clouds
            logger.info(f"Found {len(clouds)} clouds")
            
            return clouds
        
        except Exception as e:
            raise Exception(f"Failed to list clouds: {str(e)}")
    
    def list_folders(self, cloud_id: str = None) -> List[Dict[str, Any]]:
        """
        List all folders in a cloud
        
        Args:
            cloud_id: Cloud ID (uses self.cloud_id if not provided)
        
        Returns:
            List of folder dictionaries
        """
        try:
            cloud_id = cloud_id or self.cloud_id
            if not cloud_id:
                # If no cloud_id, discover from available clouds
                clouds = self.list_clouds()
                if clouds:
                    cloud_id = clouds[0]['id']
                else:
                    raise Exception("No clouds found and no cloud_id provided")
            
            headers = self._get_headers()
            url = f'{self.resource_manager_url}/folders'
            params = {'cloudId': cloud_id}
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            folders = data.get('folders', [])
            
            self._discovered_folders = folders
            logger.info(f"Found {len(folders)} folders in cloud {cloud_id}")
            
            return folders
        
        except Exception as e:
            raise Exception(f"Failed to list folders: {str(e)}")
    
    def list_instances(self, folder_id: str = None) -> List[Dict[str, Any]]:
        """
        List all compute instances in a folder
        
        Args:
            folder_id: Folder ID (uses self.folder_id if not provided)
        
        Returns:
            List of instance dictionaries with full details
        """
        try:
            folder_id = folder_id or self.folder_id
            if not folder_id:
                # Discover folder from available folders
                folders = self.list_folders()
                if folders:
                    folder_id = folders[0]['id']
                else:
                    raise Exception("No folders found and no folder_id provided")
            
            headers = self._get_headers()
            url = f'{self.compute_url}/instances'
            params = {'folderId': folder_id}
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            instances = data.get('instances', [])
            
            logger.info(f"Found {len(instances)} instances in folder {folder_id}")
            
            # Enrich each instance with additional details
            enriched_instances = []
            for instance in instances:
                # Add folder context
                instance['folder_id'] = folder_id
                enriched_instances.append(instance)
            
            return enriched_instances
        
        except Exception as e:
            raise Exception(f"Failed to list instances: {str(e)}")
    
    def get_instance(self, instance_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific instance
        
        Args:
            instance_id: Instance ID
        
        Returns:
            Instance details dictionary
        """
        try:
            headers = self._get_headers()
            url = f'{self.compute_url}/instances/{instance_id}'
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return response.json()
        
        except Exception as e:
            raise Exception(f"Failed to get instance {instance_id}: {str(e)}")
    
    def list_disks(self, folder_id: str = None) -> List[Dict[str, Any]]:
        """
        List all disks in a folder
        
        Args:
            folder_id: Folder ID (uses self.folder_id if not provided)
        
        Returns:
            List of disk dictionaries
        """
        try:
            folder_id = folder_id or self.folder_id
            if not folder_id:
                folders = self.list_folders()
                if folders:
                    folder_id = folders[0]['id']
                else:
                    raise Exception("No folders found and no folder_id provided")
            
            headers = self._get_headers()
            url = f'{self.compute_url}/disks'
            params = {'folderId': folder_id}
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            disks = data.get('disks', [])
            
            logger.info(f"Found {len(disks)} disks in folder {folder_id}")
            
            return disks
        
        except Exception as e:
            raise Exception(f"Failed to list disks: {str(e)}")
    
    def list_networks(self, folder_id: str = None) -> List[Dict[str, Any]]:
        """
        List all networks in a folder
        
        Args:
            folder_id: Folder ID (uses self.folder_id if not provided)
        
        Returns:
            List of network dictionaries
        """
        try:
            folder_id = folder_id or self.folder_id
            if not folder_id:
                folders = self.list_folders()
                if folders:
                    folder_id = folders[0]['id']
                else:
                    raise Exception("No folders found and no folder_id provided")
            
            headers = self._get_headers()
            url = f'{self.vpc_url}/networks'
            params = {'folderId': folder_id}
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            networks = data.get('networks', [])
            
            logger.info(f"Found {len(networks)} networks in folder {folder_id}")
            
            return networks
        
        except Exception as e:
            raise Exception(f"Failed to list networks: {str(e)}")
    
    def list_subnets(self, folder_id: str = None) -> List[Dict[str, Any]]:
        """
        List all subnets in a folder
        
        Args:
            folder_id: Folder ID (uses self.folder_id if not provided)
        
        Returns:
            List of subnet dictionaries
        """
        try:
            folder_id = folder_id or self.folder_id
            if not folder_id:
                folders = self.list_folders()
                if folders:
                    folder_id = folders[0]['id']
                else:
                    raise Exception("No folders found and no folder_id provided")
            
            headers = self._get_headers()
            url = f'{self.vpc_url}/subnets'
            params = {'folderId': folder_id}
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            subnets = data.get('subnets', [])
            
            logger.info(f"Found {len(subnets)} subnets in folder {folder_id}")
            
            return subnets
        
        except Exception as e:
            raise Exception(f"Failed to list subnets: {str(e)}")
    
    def _get_service_account_folder(self) -> Optional[str]:
        """
        Get the folder ID that the service account belongs to
        
        This is useful when the service account doesn't have cloud-level permissions
        but can access resources in its own folder.
        
        Returns:
            Folder ID or None
        """
        try:
            if not self.service_account_key:
                return None
            
            # Get service account ID
            if isinstance(self.service_account_key, dict):
                sa_id = self.service_account_key.get('service_account_id')
            else:
                return None
            
            if not sa_id:
                return None
            
            headers = self._get_headers()
            url = f'https://iam.api.cloud.yandex.net/iam/v1/serviceAccounts/{sa_id}'
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                sa_info = response.json()
                folder_id = sa_info.get('folderId')
                
                if folder_id:
                    logger.info(f"Service account belongs to folder: {folder_id}")
                    return folder_id
            
            return None
        except Exception as e:
            logger.error(f"Failed to get service account folder: {e}")
            return None
    
    def _get_folder_details(self, folder_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details for a specific folder
        
        Args:
            folder_id: Folder ID
        
        Returns:
            Folder details dict or None
        """
        try:
            headers = self._get_headers()
            url = f'{self.resource_manager_url}/folders/{folder_id}'
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get folder details for {folder_id}: {e}")
            return None
    
    def get_all_resources_from_folder(self, folder_id: str = None) -> Dict[str, Any]:
        """
        Get all resources from a folder
        
        Args:
            folder_id: Folder ID (uses self.folder_id if not provided)
        
        Returns:
            Dict containing all resource types
        """
        try:
            folder_id = folder_id or self.folder_id
            
            resources = {
                'instances': self.list_instances(folder_id),
                'disks': self.list_disks(folder_id),
                'networks': self.list_networks(folder_id),
                'subnets': self.list_subnets(folder_id)
            }
            
            return resources
        
        except Exception as e:
            logger.error(f"Error getting resources from folder {folder_id}: {e}")
            return {
                'instances': [],
                'disks': [],
                'networks': [],
                'subnets': [],
                'error': str(e)
            }
    
    def get_all_resources(self) -> Dict[str, Any]:
        """
        Get all resources across all accessible folders
        
        Returns:
            Dict containing all resources organized by folder
        """
        try:
            # Discover all clouds
            clouds = self.list_clouds()
            all_resources = {
                'clouds': clouds,
                'folders': [],
                'total_instances': 0,
                'total_disks': 0,
                'total_networks': 0
            }
            
            # If no clouds found, try to discover folder from service account
            if len(clouds) == 0:
                logger.warning("No clouds accessible - attempting to discover folder from service account")
                try:
                    folder_id = self._get_service_account_folder()
                    if folder_id:
                        logger.info(f"Using service account folder: {folder_id}")
                        folder_details = self._get_folder_details(folder_id)
                        
                        if folder_details:
                            folder_resources = self.get_all_resources_from_folder(folder_id)
                            
                            folder_info = {
                                'folder': folder_details,
                                'cloud_id': folder_details.get('cloudId', 'unknown'),
                                'resources': folder_resources
                            }
                            
                            all_resources['folders'].append(folder_info)
                            all_resources['total_instances'] += len(folder_resources.get('instances', []))
                            all_resources['total_disks'] += len(folder_resources.get('disks', []))
                            all_resources['total_networks'] += len(folder_resources.get('networks', []))
                            
                            logger.info(f"Found {all_resources['total_instances']} instances from folder {folder_id}")
                            return all_resources
                except Exception as folder_error:
                    logger.error(f"Failed to use service account folder: {folder_error}")
            
            for cloud in clouds:
                cloud_id = cloud['id']
                folders = self.list_folders(cloud_id)
                
                for folder in folders:
                    folder_id = folder['id']
                    folder_resources = self.get_all_resources_from_folder(folder_id)
                    
                    folder_info = {
                        'folder': folder,
                        'cloud_id': cloud_id,
                        'resources': folder_resources
                    }
                    
                    all_resources['folders'].append(folder_info)
                    all_resources['total_instances'] += len(folder_resources.get('instances', []))
                    all_resources['total_disks'] += len(folder_resources.get('disks', []))
                    all_resources['total_networks'] += len(folder_resources.get('networks', []))
            
            logger.info(f"Discovered {all_resources['total_instances']} instances, "
                       f"{all_resources['total_disks']} disks, "
                       f"{all_resources['total_networks']} networks across "
                       f"{len(all_resources['folders'])} folders")
            
            return all_resources
        
        except Exception as e:
            logger.error(f"Error getting all resources: {e}")
            return {
                'clouds': [],
                'folders': [],
                'total_instances': 0,
                'total_disks': 0,
                'total_networks': 0,
                'error': str(e)
            }
    
    def get_billing_account(self) -> Dict[str, Any]:
        """
        Get billing account information
        
        Returns:
            Billing account details
        """
        try:
            headers = self._get_headers()
            url = f'{self.billing_url}/billingAccounts'
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            accounts = data.get('billingAccounts', [])
            
            if accounts:
                return accounts[0]  # Return first billing account
            else:
                return {}
        
        except Exception as e:
            logger.error(f"Failed to get billing account: {e}")
            return {}
    
    def get_resource_costs(self, billing_account_id: str = None, 
                           start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        Get resource costs from billing API
        
        Note: Yandex Cloud billing API access requires special permissions.
        This is a placeholder for future implementation.
        
        Args:
            billing_account_id: Billing account ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            Dict with cost information
        """
        try:
            # Note: Billing API access may require additional setup
            # For now, we'll return estimated costs based on resource types
            logger.warning("Billing API not fully implemented - using resource-based cost estimation")
            return {}
        
        except Exception as e:
            logger.error(f"Failed to get resource costs: {e}")
            return {}
    
    def get_instance_cpu_statistics(self, instance_id: str, folder_id: str = None, days: int = 30) -> Dict[str, Any]:
        """
        Get CPU usage statistics for a compute instance
        
        Args:
            instance_id: Instance ID
            folder_id: Folder ID (uses self.folder_id if not provided)
            days: Number of days of historical data (default: 30)
        
        Returns:
            Dict containing CPU statistics:
            - avg_cpu_usage: Average CPU percentage
            - max_cpu_usage: Maximum CPU percentage
            - min_cpu_usage: Minimum CPU percentage
            - trend: CPU usage variance
            - performance_tier: low/medium/high
            - data_points: Number of raw data points
            - daily_aggregated: List of daily averages for charting
        """
        try:
            from collections import defaultdict
            
            folder_id = folder_id or self.folder_id
            if not folder_id:
                # Try to get folder from service account
                folder_id = self._get_service_account_folder()
            
            if not folder_id:
                raise Exception("No folder_id available for metrics query")
            
            # Set time range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            # Query Yandex Monitoring API
            url = f'{self.monitoring_url}/data/read'
            params = {'folderId': folder_id}
            
            # Use cpu_usage metric (aggregate across all CPU cores)
            body = {
                'query': f'cpu_usage{{resource_id="{instance_id}"}}',
                'fromTime': start_time.isoformat() + 'Z',
                'toTime': end_time.isoformat() + 'Z',
                'downsampling': {
                    'gridAggregation': 'AVG',
                    'maxPoints': days * 24  # Hourly granularity
                }
            }
            
            headers = self._get_headers()
            response = requests.post(url, json=body, params=params, headers=headers, timeout=90)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract metrics data
            metrics = data.get('metrics', [])
            if not metrics or len(metrics) == 0:
                # No metrics available (VM might be too new or monitoring not enabled)
                logger.warning(f"No CPU metrics available for instance {instance_id}")
                return {
                    'avg_cpu_usage': 0,
                    'max_cpu_usage': 0,
                    'min_cpu_usage': 0,
                    'trend': 0,
                    'performance_tier': 'unknown',
                    'data_points': 0,
                    'daily_data_points': 0,
                    'period': 'DAY',
                    'collection_timestamp': datetime.utcnow().isoformat(),
                    'daily_aggregated': [],
                    'no_data': True
                }
            
            # Get timeseries data
            timeseries = metrics[0].get('timeseries', {})
            timestamps = timeseries.get('timestamps', [])
            values = timeseries.get('doubleValues', [])
            
            if not values or len(values) == 0:
                logger.warning(f"No CPU data points for instance {instance_id}")
                return {
                    'avg_cpu_usage': 0,
                    'max_cpu_usage': 0,
                    'min_cpu_usage': 0,
                    'trend': 0,
                    'performance_tier': 'unknown',
                    'data_points': 0,
                    'no_data': True
                }
            
            # Aggregate hourly/sub-hourly data into daily points for UI display
            daily_data = defaultdict(list)
            
            for i, timestamp in enumerate(timestamps):
                if i < len(values) and values[i] is not None:
                    # Convert timestamp (milliseconds since epoch) to date
                    dt = datetime.fromtimestamp(timestamp / 1000.0)
                    date_key = dt.strftime('%Y-%m-%d')
                    daily_data[date_key].append(values[i])
            
            # Calculate statistics
            all_values = [v for v in values if v is not None]
            
            if not all_values:
                return {'avg_cpu_usage': 0, 'max_cpu_usage': 0, 'min_cpu_usage': 0, 'no_data': True}
            
            avg_cpu = sum(all_values) / len(all_values)
            max_cpu = max(all_values)
            min_cpu = min(all_values)
            trend = max_cpu - min_cpu
            
            # Determine performance tier (same thresholds as Selectel)
            if avg_cpu < 20:
                performance_tier = 'low'
            elif avg_cpu < 60:
                performance_tier = 'medium'
            else:
                performance_tier = 'high'
            
            # Create daily aggregated data for chart display
            daily_points = []
            for date in sorted(daily_data.keys()):
                day_values = daily_data[date]
                day_avg = sum(day_values) / len(day_values)
                daily_points.append({
                    'date': date,
                    'value': round(day_avg, 2),
                    'samples': len(day_values)
                })
            
            logger.info(f"✅ CPU statistics for {instance_id}: avg={avg_cpu:.2f}%, max={max_cpu:.2f}%, {len(all_values)} points")
            
            return {
                'avg_cpu_usage': round(avg_cpu, 2),
                'max_cpu_usage': round(max_cpu, 2),
                'min_cpu_usage': round(min_cpu, 2),
                'trend': round(trend, 2),
                'performance_tier': performance_tier,
                'data_points': len(all_values),
                'daily_data_points': len(daily_points),
                'period': 'DAY',
                'collection_timestamp': datetime.utcnow().isoformat(),
                'daily_aggregated': daily_points,  # For chart display
                'metric_source': 'yandex_monitoring'
            }
        
        except Exception as e:
            logger.error(f"Failed to get CPU statistics for instance {instance_id}: {e}")
            return {
                'avg_cpu_usage': 0,
                'max_cpu_usage': 0,
                'min_cpu_usage': 0,
                'error': str(e),
                'no_data': True
            }

