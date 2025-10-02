"""
Resource mapping utilities for converting provider-specific data to unified format
"""
from typing import Dict, Any, List
from datetime import datetime

class ResourceMapper:
    """Utility class for mapping provider-specific resources to unified format"""
    
    @staticmethod
    def map_resource(provider_data: Dict[str, Any], provider_type: str) -> Dict[str, Any]:
        """Map provider-specific resource data to unified format"""
        return {
            'resource_id': provider_data.get('id', ''),
            'resource_name': provider_data.get('name', ''),
            'region': provider_data.get('region', 'default'),
            'service_name': ResourceMapper._map_service_name(provider_data, provider_type),
            'resource_type': ResourceMapper._map_resource_type(provider_data, provider_type),
            'status': ResourceMapper._map_status(provider_data),
            'pricing_model': provider_data.get('pricing_model', 'on-demand'),
            'list_price': float(provider_data.get('price', 0.0)),
            'effective_cost': float(provider_data.get('cost', 0.0)),
            'currency': provider_data.get('currency', 'RUB'),
            'billing_period': provider_data.get('billing_period', 'monthly'),
            'provider_config': provider_data
        }
    
    @staticmethod
    def _map_service_name(provider_data: Dict[str, Any], provider_type: str) -> str:
        """Map provider-specific service to unified service name"""
        service_mapping = {
            'beget': {
                'vps': 'Compute',
                'domain': 'Domain',
                'database': 'Database',
                'ftp': 'Storage'
            },
            'yandex': {
                'compute': 'Compute',
                'storage': 'Storage',
                'database': 'Database',
                'network': 'Network'
            }
        }
        
        resource_type = provider_data.get('type', '').lower()
        return service_mapping.get(provider_type, {}).get(resource_type, 'Unknown')
    
    @staticmethod
    def _map_resource_type(provider_data: Dict[str, Any], provider_type: str) -> str:
        """Map provider-specific resource type to unified type"""
        type_mapping = {
            'beget': {
                'vps': 'VM',
                'domain': 'Domain',
                'database': 'MySQL',
                'ftp': 'FTP'
            },
            'yandex': {
                'compute': 'VM',
                'storage': 'Bucket',
                'database': 'PostgreSQL',
                'network': 'LoadBalancer'
            }
        }
        
        resource_type = provider_data.get('type', '').lower()
        return type_mapping.get(provider_type, {}).get(resource_type, resource_type.title())
    
    @staticmethod
    def _map_status(provider_data: Dict[str, Any]) -> str:
        """Map provider-specific status to unified status"""
        status = provider_data.get('status', '').lower()
        status_mapping = {
            'running': 'active',
            'active': 'active',
            'stopped': 'stopped',
            'stopping': 'stopped',
            'starting': 'active',
            'deleted': 'deleted',
            'error': 'error'
        }
        return status_mapping.get(status, 'unknown')
    
    @staticmethod
    def map_metrics(provider_data: Dict[str, Any], resource_id: str) -> List[Dict[str, Any]]:
        """Map provider-specific metrics to unified format"""
        metrics = []
        timestamp = datetime.utcnow()
        
        # CPU metrics
        if 'cpu_usage' in provider_data:
            metrics.append({
                'resource_id': resource_id,
                'metric_name': 'cpu_usage',
                'metric_value': float(provider_data['cpu_usage']),
                'metric_unit': 'percent',
                'timestamp': timestamp
            })
        
        # Memory metrics
        if 'memory_usage' in provider_data:
            metrics.append({
                'resource_id': resource_id,
                'metric_name': 'memory_usage',
                'metric_value': float(provider_data['memory_usage']),
                'metric_unit': 'percent',
                'timestamp': timestamp
            })
        
        # Disk metrics
        if 'disk_usage' in provider_data:
            metrics.append({
                'resource_id': resource_id,
                'metric_name': 'disk_usage',
                'metric_value': float(provider_data['disk_usage']),
                'metric_unit': 'percent',
                'timestamp': timestamp
            })
        
        return metrics
