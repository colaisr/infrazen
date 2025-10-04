"""
Selectel API client implementation
"""
import requests
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
# from app.providers.base.provider_base import BaseProvider

logger = logging.getLogger(__name__)


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
        # Selectel regions and their API endpoints
        self.regions = {
            'ru-3': 'https://ru-3.cloud.api.selcloud.ru',
            'kz-1': 'https://kz-1.cloud.api.servercore.com'
        }
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
    
    def get_openstack_volumes(self, project_id: str = None, region: str = None) -> List[Dict[str, Any]]:
        """
        Get OpenStack volumes from a specific region
        
        Args:
            project_id: Optional project ID to scope the request
            region: Optional region to query (if None, uses default openstack_base_url)
            
        Returns:
            List of volume dictionaries
        """
        try:
            headers = self._get_openstack_headers()
            headers['Openstack-Api-Version'] = 'volume latest'
            
            # Determine which base URL to use
            base_url = self.regions.get(region, self.openstack_base_url) if region else self.openstack_base_url
            
            # Include project ID in URL if provided
            if project_id:
                volumes_url = f'{base_url}/volume/v3/{project_id}/volumes/detail'
            else:
                volumes_url = f'{base_url}/volume/v3/volumes/detail'
            
            response = requests.get(volumes_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            volumes = data.get('volumes', [])
            
            # Add region info to each volume if not already present
            for vol in volumes:
                if 'region' not in vol and region:
                    vol['region'] = region
            
            return volumes
            
        except Exception as e:
            raise Exception(f"Failed to get OpenStack volumes from {region or 'default region'}: {str(e)}")
    
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
    
    def get_openstack_ports(self) -> List[Dict[str, Any]]:
        """
        Get OpenStack network ports (network interfaces)
        
        This provides detailed network information including:
        - IP addresses per server
        - MAC addresses
        - Network attachments
        
        Returns:
            List of port dictionaries
        """
        try:
            headers = self._get_openstack_headers()
            headers['Openstack-Api-Version'] = 'network latest'
            ports_url = f'{self.openstack_base_url}/network/v2.0/ports'
            
            response = requests.get(ports_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return data.get('ports', [])
            
        except Exception as e:
            raise Exception(f"Failed to get OpenStack ports: {str(e)}")
    
    def get_server_cpu_statistics(self, server_id: str, hours: int = 1) -> Dict[str, Any]:
        """
        Get CPU usage statistics for a server
        
        Args:
            server_id: Server UUID
            hours: Number of hours of historical data (default: 1)
            
        Returns:
            Dict containing CPU statistics in Beget-compatible format:
            - avg_cpu_usage: Average CPU percentage
            - max_cpu_usage: Maximum CPU percentage
            - min_cpu_usage: Minimum CPU percentage
            - trend: CPU usage variance
            - performance_tier: low/medium/high
            - data_points: Number of data points
        """
        try:
            from datetime import datetime, timedelta
            
            iam_token = self._get_iam_token()
            
            # Set time range
            stop_time = datetime.utcnow()
            start_time = stop_time - timedelta(hours=hours)
            
            start_iso = start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            stop_iso = stop_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            # Request CPU metrics with 5-minute granularity (300 seconds)
            # Note: Selectel only supports 300-second granularity
            url = f"{self.openstack_base_url}/metric/v1/aggregates?details=false&granularity=300&start={start_iso}&stop={stop_iso}"
            
            body = {
                "operations": "(max (metric cpu_util mean) (/ (clip_min (rateofchangesec (metric cpu_average mean)) 0) 10000000)))",
                "search": f"id={server_id}",
                "resource_type": "generic"
            }
            
            headers = {
                'X-Auth-Token': iam_token,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            response = requests.post(url, json=body, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract and process data points
            if 'measures' in data and 'aggregated' in data['measures']:
                data_points = data['measures']['aggregated']
                cpu_values = [point[2] for point in data_points if point[2] is not None]
                
                if cpu_values:
                    avg_cpu = sum(cpu_values) / len(cpu_values)
                    max_cpu = max(cpu_values)
                    min_cpu = min(cpu_values)
                    trend = max_cpu - min_cpu
                    
                    # Determine performance tier
                    if avg_cpu < 20:
                        performance_tier = 'low'
                    elif avg_cpu < 60:
                        performance_tier = 'medium'
                    else:
                        performance_tier = 'high'
                    
                    return {
                        'avg_cpu_usage': round(avg_cpu, 2),
                        'max_cpu_usage': round(max_cpu, 2),
                        'min_cpu_usage': round(min_cpu, 2),
                        'trend': round(trend, 2),
                        'performance_tier': performance_tier,
                        'data_points': len(cpu_values),
                        'period': 'HOUR',
                        'collection_timestamp': datetime.utcnow().isoformat(),
                        'raw_data': data_points
                    }
            
            return {}
            
        except Exception as e:
            raise Exception(f"Failed to get CPU statistics for server {server_id}: {str(e)}")
    
    def get_server_memory_statistics(self, server_id: str, ram_mb: int, hours: int = 1) -> Dict[str, Any]:
        """
        Get memory usage statistics for a server
        
        Args:
            server_id: Server UUID
            ram_mb: Total RAM in MB (for percentage calculation)
            hours: Number of hours of historical data (default: 1)
            
        Returns:
            Dict containing memory statistics in Beget-compatible format:
            - avg_memory_usage_mb: Average memory in MB
            - max_memory_usage_mb: Maximum memory in MB
            - min_memory_usage_mb: Minimum memory in MB
            - memory_usage_percent: Average usage percentage
            - trend: Memory usage variance
            - memory_tier: low/medium/high
            - data_points: Number of data points
        """
        try:
            from datetime import datetime, timedelta
            
            iam_token = self._get_iam_token()
            
            # Set time range
            stop_time = datetime.utcnow()
            start_time = stop_time - timedelta(hours=hours)
            
            start_iso = start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            stop_iso = stop_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            # Request memory metrics with 5-minute granularity (300 seconds)
            # Note: Selectel only supports 300-second granularity
            url = f"{self.openstack_base_url}/metric/v1/aggregates?details=false&granularity=300&start={start_iso}&stop={stop_iso}"
            
            body = {
                "operations": "(metric memory.usage mean)",
                "search": f"id={server_id}",
                "resource_type": "generic"
            }
            
            headers = {
                'X-Auth-Token': iam_token,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            response = requests.post(url, json=body, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract and process data points
            if 'measures' in data and server_id in data['measures']:
                server_metrics = data['measures'][server_id]
                
                if 'memory.usage' in server_metrics and 'mean' in server_metrics['memory.usage']:
                    data_points = server_metrics['memory.usage']['mean']
                    mem_values = [point[2] for point in data_points if point[2] is not None]
                    
                    if mem_values:
                        avg_mem_mb = sum(mem_values) / len(mem_values)
                        max_mem_mb = max(mem_values)
                        min_mem_mb = min(mem_values)
                        avg_mem_percent = (avg_mem_mb / ram_mb) * 100 if ram_mb > 0 else 0
                        trend = max_mem_mb - min_mem_mb
                        
                        # Determine memory tier
                        if avg_mem_percent < 40:
                            memory_tier = 'low'
                        elif avg_mem_percent < 70:
                            memory_tier = 'medium'
                        else:
                            memory_tier = 'high'
                        
                        return {
                            'avg_memory_usage_mb': round(avg_mem_mb, 2),
                            'max_memory_usage_mb': round(max_mem_mb, 2),
                            'min_memory_usage_mb': round(min_mem_mb, 2),
                            'memory_usage_percent': round(avg_mem_percent, 2),
                            'trend': round(trend, 2),
                            'memory_tier': memory_tier,
                            'data_points': len(mem_values),
                            'period': 'HOUR',
                            'collection_timestamp': datetime.utcnow().isoformat(),
                            'raw_data': data_points
                        }
            
            return {}
            
        except Exception as e:
            raise Exception(f"Failed to get memory statistics for server {server_id}: {str(e)}")
    
    def get_resource_costs(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get cost/consumption data for all resources
        
        Uses the cloud_billing API to get actual costs per resource.
        Costs are returned in kopecks (1/100 ruble) per hour, grouped by resource.
        
        Args:
            hours: Number of hours to fetch cost data for (default: 24 for daily cost)
            
        Returns:
            Dict mapping resource_id to cost information:
            {
                'resource_id': {
                    'name': 'Resource Name',
                    'type': 'cloud_vm',
                    'hourly_cost_kopecks': 43.0,
                    'hourly_cost_rubles': 0.43,
                    'daily_cost_rubles': 10.32,
                    'monthly_cost_rubles': 309.60,
                    'metrics': {'compute_cores_preemptible': 22, 'compute_ram_preemptible': 9, ...}
                }
            }
        """
        try:
            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            # Format timestamps for API
            start_str = start_time.strftime('%Y-%m-%dT%H:00:00')
            end_str = end_time.strftime('%Y-%m-%dT%H:59:59')
            
            # Construct billing API URL
            billing_url = "https://api.selectel.ru/v1/cloud_billing/statistic/consumption"
            params = {
                'provider_keys': ['vpc', 'mks', 'dbaas', 'craas'],
                'start': start_str,
                'end': end_str,
                'locale': 'ru',
                'group_type': 'project_object_region_metric',
                'period_group_type': 'hour'
            }
            
            # Make request with X-Token authentication
            headers = {
                'X-Token': self.api_key,
                'Accept': 'application/json'
            }
            
            response = requests.get(billing_url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 'success':
                return {}
            
            # Process consumption data
            resource_costs = {}
            
            for item in data.get('data', []):
                obj = item.get('object', {})
                obj_id = obj.get('id')
                obj_name = obj.get('name', 'Unknown')
                obj_type = obj.get('type')
                parent_id = obj.get('parent_id', '')
                
                metric_id = item.get('metric', {}).get('id', '')
                cost_kopecks = item.get('value', 0)  # Cost in kopecks per hour
                
                # For VMs, aggregate their own costs
                if obj_type == 'cloud_vm':
                    if obj_id not in resource_costs:
                        resource_costs[obj_id] = {
                            'name': obj_name,
                            'type': obj_type,
                            'metrics': {},
                            'total_kopecks': 0
                        }
                    
                    resource_costs[obj_id]['metrics'][metric_id] = resource_costs[obj_id]['metrics'].get(metric_id, 0) + cost_kopecks
                    resource_costs[obj_id]['total_kopecks'] += cost_kopecks
                
                # For volumes with parent_id, add their cost to the parent VM
                elif parent_id:
                    if parent_id not in resource_costs:
                        # Initialize parent if not exists (shouldn't happen, but safe)
                        resource_costs[parent_id] = {
                            'name': obj.get('parent_name', 'Unknown'),
                            'type': 'cloud_vm',
                            'metrics': {},
                            'total_kopecks': 0
                        }
                    
                    resource_costs[parent_id]['metrics'][metric_id] = resource_costs[parent_id]['metrics'].get(metric_id, 0) + cost_kopecks
                    resource_costs[parent_id]['total_kopecks'] += cost_kopecks
            
            # Calculate averaged costs per resource
            num_hours = len(set(item.get('period') for item in data.get('data', [])))
            if num_hours == 0:
                num_hours = hours  # Fallback
            
            for resource_id, cost_data in resource_costs.items():
                # Average hourly cost
                avg_hourly_kopecks = cost_data['total_kopecks'] / num_hours if num_hours > 0 else cost_data['total_kopecks']
                avg_hourly_rubles = avg_hourly_kopecks / 100
                
                # Projected costs
                daily_rubles = avg_hourly_rubles * 24
                monthly_rubles = daily_rubles * 30
                
                cost_data['hourly_cost_kopecks'] = round(avg_hourly_kopecks, 2)
                cost_data['hourly_cost_rubles'] = round(avg_hourly_rubles, 4)
                cost_data['daily_cost_rubles'] = round(daily_rubles, 2)
                cost_data['monthly_cost_rubles'] = round(monthly_rubles, 2)
            
            return resource_costs
            
        except Exception as e:
            print(f"Error fetching resource costs: {e}")
            return {}
    
    def get_all_server_statistics(self, servers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get CPU and memory statistics for all servers
        
        Args:
            servers: List of server dictionaries from get_combined_vm_resources()
            
        Returns:
            Dict mapping server_id to statistics:
            {
                'server_id': {
                    'server_name': 'Server Name',
                    'cpu_statistics': {...},
                    'memory_statistics': {...}
                }
            }
        """
        all_statistics = {}
        
        for server in servers:
            server_id = server.get('id')
            server_name = server.get('name', 'Unknown')
            ram_mb = server.get('ram_mb', 1024)
            
            try:
                # Get CPU statistics
                cpu_stats = self.get_server_cpu_statistics(server_id, hours=1)
                
                # Get memory statistics
                memory_stats = self.get_server_memory_statistics(server_id, ram_mb, hours=1)
                
                all_statistics[server_id] = {
                    'server_name': server_name,
                    'cpu_statistics': cpu_stats,
                    'memory_statistics': memory_stats,
                    'collection_timestamp': datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                # Log error but continue with other servers
                all_statistics[server_id] = {
                    'server_name': server_name,
                    'error': str(e),
                    'cpu_statistics': {},
                    'memory_statistics': {}
                }
        
        return all_statistics
    
    def get_combined_vm_resources(self) -> List[Dict[str, Any]]:
        """
        Get VM resources with attached volumes and network interfaces combined
        
        This method combines data from multiple OpenStack APIs to create complete
        VM resources that match what you see in the Selectel admin panel.
        
        Returns:
            List of complete VM resource dictionaries including:
            - VM specifications (vCPUs, RAM, flavor)
            - Attached volumes with sizes and device paths
            - Network interfaces with IPs and MAC addresses
            - Total storage calculation
        """
        try:
            # Get all required data
            servers = self.get_openstack_servers()
            
            # Get project ID for volume API
            projects = self.get_projects()
            project_id = projects[0]['id'] if projects else None
            
            volumes = self.get_openstack_volumes(project_id)
            ports = self.get_openstack_ports()
            
            # Create volume mapping by server attachment
            volume_by_server = {}
            for volume in volumes:
                for attachment in volume.get('attachments', []):
                    server_id = attachment.get('server_id')
                    if server_id:
                        if server_id not in volume_by_server:
                            volume_by_server[server_id] = []
                        volume_by_server[server_id].append(volume)
            
            # Create port mapping by device_id (server_id)
            port_by_server = {}
            for port in ports:
                device_id = port.get('device_id')
                if device_id and port.get('device_owner', '').startswith('compute:'):
                    if device_id not in port_by_server:
                        port_by_server[device_id] = []
                    port_by_server[device_id].append(port)
            
            # Combine everything into complete VM resources
            complete_vms = []
            for server in servers:
                server_id = server['id']
                
                # Get attached volumes
                attached_volumes = volume_by_server.get(server_id, [])
                
                # Get network interfaces
                server_ports = port_by_server.get(server_id, [])
                
                # Extract IP addresses
                ip_addresses = []
                for port in server_ports:
                    for fixed_ip in port.get('fixed_ips', []):
                        ip_addresses.append(fixed_ip.get('ip_address'))
                
                # Calculate total storage
                total_storage_gb = sum(v.get('size', 0) for v in attached_volumes)
                
                # Get flavor info
                flavor = server.get('flavor', {})
                
                # Create complete VM resource
                vm_resource = {
                    'id': server_id,
                    'name': server['name'],
                    'type': 'server',
                    'status': server['status'],
                    'created_at': server.get('created'),
                    'updated_at': server.get('updated'),
                    'region': server.get('OS-EXT-AZ:availability_zone', 'ru-3'),
                    'vcpus': flavor.get('vcpus', 0),
                    'ram_mb': flavor.get('ram', 0),
                    'disk_gb': flavor.get('disk', 0),
                    'flavor_name': flavor.get('original_name', ''),
                    'image_id': server.get('image', {}).get('id'),
                    'ip_addresses': ip_addresses,
                    'total_storage_gb': total_storage_gb,
                    'attached_volumes': [
                        {
                            'id': v['id'],
                            'name': v.get('name', ''),
                            'size_gb': v['size'],
                            'type': v.get('volume_type'),
                            'status': v.get('status'),
                            'device': next((a.get('device') for a in v.get('attachments', []) if a.get('server_id') == server_id), None),
                            'bootable': v.get('bootable') == 'true'
                        }
                        for v in attached_volumes
                    ],
                    'network_interfaces': [
                        {
                            'id': p['id'],
                            'mac_address': p.get('mac_address'),
                            'status': p.get('status'),
                            'ip_addresses': [ip.get('ip_address') for ip in p.get('fixed_ips', [])]
                        }
                        for p in server_ports
                    ],
                    'metadata': server.get('metadata', {}),
                    'tags': server.get('tags', []),
                    'tenant_id': server.get('tenant_id'),
                    'user_id': server.get('user_id')
                }
                
                complete_vms.append(vm_resource)
            
            return complete_vms
            
        except Exception as e:
            raise Exception(f"Failed to get combined VM resources: {str(e)}")
    
    def calculate_volume_cost(self, volume: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate cost for a volume based on its size and type
        
        Selectel pricing (as of 2025):
        - HDD (Network Basic): 7.28 ₽/GB/month
        - SSD (Network Basic): 8.99 ₽/GB/month
        - SSD (Network Universal): 18.55 ₽/GB/month
        - SSD NVMe (Network Fast): 39.18 ₽/GB/month
        
        Args:
            volume: Volume data dictionary
            
        Returns:
            Dict with hourly, daily, and monthly costs in rubles
        """
        size_gb = volume.get('size', 0)
        volume_type = volume.get('volume_type', '').lower()
        
        # Determine price per GB per month based on volume type
        if 'fast' in volume_type or 'nvme' in volume_type:
            price_per_gb_month = 39.18
        elif 'universal' in volume_type:
            price_per_gb_month = 18.55
        elif 'basic' in volume_type or 'ssd' in volume_type:
            # Check if it's HDD or SSD basic
            if 'hdd' in volume_type:
                price_per_gb_month = 7.28
            else:
                # Default basic is HDD basic
                price_per_gb_month = 7.28
        else:
            # Default to HDD basic pricing
            price_per_gb_month = 7.28
        
        monthly_cost = size_gb * price_per_gb_month
        daily_cost = monthly_cost / 30
        hourly_cost = monthly_cost / 720  # 30 days * 24 hours
        
        return {
            'hourly_cost_rubles': round(hourly_cost, 4),
            'daily_cost_rubles': round(daily_cost, 2),
            'monthly_cost_rubles': round(monthly_cost, 2)
        }
    
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
        Get all available resources and information including combined cloud resources
        
        This method returns complete VM resources with integrated volumes and network
        info, matching what you see in the Selectel admin panel.
        
        Returns:
            Dict containing all available resource information with:
            - account: Account information
            - projects: List of projects
            - servers: Complete VM resources with attached volumes
            - volumes: Empty list (volumes are now part of servers)
            - networks: Empty list (network info is part of servers)
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
            
            # Get combined VM resources (VMs with attached volumes and network info)
            try:
                resources['servers'] = self.get_combined_vm_resources()
                
                # Get standalone volumes from ALL regions (those not attached to any server)
                all_volumes = []
                for project in resources.get('projects', []):
                    project_id = project.get('id')
                    if project_id:
                        # Query each region for volumes
                        for region_name in self.regions.keys():
                            try:
                                logger.info(f"Fetching volumes for project {project_id} in region {region_name}")
                                project_volumes = self.get_openstack_volumes(project_id, region=region_name)
                                all_volumes.extend(project_volumes)
                                logger.info(f"Found {len(project_volumes)} volumes in {region_name}")
                            except Exception as vol_err:
                                logger.warning(f"Failed to get volumes for project {project_id} in region {region_name}: {vol_err}")
                
                # Filter to only standalone volumes (not attached to any server)
                standalone_volumes = [
                    vol for vol in all_volumes 
                    if not vol.get('attachments') or len(vol.get('attachments', [])) == 0
                ]
                logger.info(f"Found {len(standalone_volumes)} standalone volumes out of {len(all_volumes)} total")
                resources['volumes'] = standalone_volumes
                
                # Networks are integrated into servers
                resources['networks'] = []
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
