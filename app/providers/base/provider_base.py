"""
Abstract base class for cloud provider implementations
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime

class BaseProvider(ABC):
    """Abstract base class for cloud provider implementations"""
    
    def __init__(self, provider_id: int, credentials: Dict[str, Any]):
        self.provider_id = provider_id
        self.credentials = credentials
        self.provider_type = self.get_provider_type()
    
    @abstractmethod
    def get_provider_type(self) -> str:
        """Return the provider type identifier"""
        pass
    
    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to provider API"""
        pass
    
    @abstractmethod
    def sync_resources(self) -> Dict[str, Any]:
        """Sync all resources from provider"""
        pass
    
    @abstractmethod
    def get_resource_details(self, resource_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific resource"""
        pass
    
    @abstractmethod
    def get_usage_metrics(self, resource_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get usage metrics for a resource in a date range"""
        pass
    
    @abstractmethod
    def get_cost_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get cost data for the account in a date range"""
        pass
    
    def validate_credentials(self) -> bool:
        """Validate provider credentials format"""
        required_fields = self.get_required_credentials()
        return all(field in self.credentials for field in required_fields)
    
    @abstractmethod
    def get_required_credentials(self) -> List[str]:
        """Return list of required credential fields"""
        pass
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information and capabilities"""
        return {
            'provider_type': self.provider_type,
            'supports_resources': True,
            'supports_metrics': True,
            'supports_cost_data': True,
            'supports_logs': False,  # Override in specific providers
            'last_updated': datetime.utcnow().isoformat()
        }
