"""
Dynamic resource registry for provider-agnostic resource mapping
"""
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ProviderResource:
    """Standardized resource representation across all providers"""
    resource_id: str
    resource_name: str
    resource_type: str
    service_name: str
    region: str
    status: str
    effective_cost: float
    currency: str
    billing_period: str
    provider_config: Dict[str, Any]
    provider_type: str
    tags: Dict[str, str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'resource_id': self.resource_id,
            'resource_name': self.resource_name,
            'resource_type': self.resource_type,
            'service_name': self.service_name,
            'region': self.region,
            'status': self.status,
            'effective_cost': self.effective_cost,
            'currency': self.currency,
            'billing_period': self.billing_period,
            'provider_config': self.provider_config,
            'provider_type': self.provider_type,
            'tags': self.tags
        }


class ResourceMapping:
    """Resource type mapping configuration"""

    def __init__(self, provider_type: str, raw_type: str, unified_type: str,
                 service_name: str, custom_mappings: Dict[str, Any] = None):
        self.provider_type = provider_type
        self.raw_type = raw_type
        self.unified_type = unified_type
        self.service_name = service_name
        self.custom_mappings = custom_mappings or {}
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'provider_type': self.provider_type,
            'raw_type': self.raw_type,
            'unified_type': self.unified_type,
            'service_name': self.service_name,
            'custom_mappings': self.custom_mappings,
            'created_at': self.created_at.isoformat()
        }


class StatusMapping:
    """Status value mapping configuration"""

    def __init__(self, provider_type: str, raw_status: str, unified_status: str):
        self.provider_type = provider_type
        self.raw_status = raw_status
        self.unified_status = unified_status

    def to_dict(self) -> Dict[str, Any]:
        return {
            'provider_type': self.provider_type,
            'raw_status': self.raw_status,
            'unified_status': self.unified_status
        }


class ResourceRegistry:
    """Dynamic resource registry for managing provider mappings"""

    def __init__(self):
        self._resource_mappings: Dict[str, Dict[str, ResourceMapping]] = {}
        self._status_mappings: Dict[str, Dict[str, StatusMapping]] = {}
        self._field_mappings: Dict[str, Dict[str, str]] = {}
        self._custom_processors: Dict[str, Callable] = {}
        self._validators: Dict[str, Callable] = {}

        # Initialize with default mappings
        self._initialize_default_mappings()

    def _initialize_default_mappings(self):
        """Initialize default mappings for existing providers"""
        # Common status mappings
        common_statuses = [
            ('running', 'active'),
            ('active', 'active'),
            ('stopped', 'stopped'),
            ('stopping', 'stopped'),
            ('starting', 'active'),
            ('deleted', 'deleted'),
            ('error', 'error'),
            ('failed', 'error'),
            ('terminated', 'deleted'),
            ('shutoff', 'stopped'),
            ('suspended', 'stopped'),
        ]

        for raw, unified in common_statuses:
            self.register_status_mapping('*', raw, unified)

    def register_resource_mapping(self, provider_type: str, raw_type: str,
                                unified_type: str, service_name: str,
                                custom_mappings: Dict[str, Any] = None) -> None:
        """Register a resource type mapping"""
        if provider_type not in self._resource_mappings:
            self._resource_mappings[provider_type] = {}

        mapping = ResourceMapping(provider_type, raw_type, unified_type,
                                service_name, custom_mappings)
        self._resource_mappings[provider_type][raw_type] = mapping

        logger.debug(f"Registered resource mapping: {provider_type}.{raw_type} -> {unified_type}")

    def register_status_mapping(self, provider_type: str, raw_status: str,
                               unified_status: str) -> None:
        """Register a status value mapping"""
        if provider_type not in self._status_mappings:
            self._status_mappings[provider_type] = {}

        mapping = StatusMapping(provider_type, raw_status, unified_status)
        self._status_mappings[provider_type][raw_status] = mapping

    def register_field_mapping(self, provider_type: str, raw_field: str,
                              unified_field: str) -> None:
        """Register a field name mapping"""
        if provider_type not in self._field_mappings:
            self._field_mappings[provider_type] = {}

        self._field_mappings[provider_type][raw_field] = unified_field

    def register_custom_processor(self, provider_type: str, processor: Callable) -> None:
        """Register a custom resource processor for a provider"""
        self._custom_processors[provider_type] = processor
        logger.debug(f"Registered custom processor for {provider_type}")

    def register_validator(self, provider_type: str, validator: Callable) -> None:
        """Register a resource validator for a provider"""
        self._validators[provider_type] = validator
        logger.debug(f"Registered validator for {provider_type}")

    def map_resource(self, provider_data: Dict[str, Any], provider_type: str) -> ProviderResource:
        """Map provider-specific resource data to unified format"""
        # Check for custom processor first
        if provider_type in self._custom_processors:
            try:
                result = self._custom_processors[provider_type](provider_data, provider_type)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Custom processor failed for {provider_type}: {e}")

        # Fall back to standard mapping
        return self._map_resource_standard(provider_data, provider_type)

    def _map_resource_standard(self, provider_data: Dict[str, Any], provider_type: str) -> ProviderResource:
        """Standard resource mapping logic"""
        # Get resource type from provider data
        raw_type = self._extract_raw_type(provider_data, provider_type)

        # Map resource type
        resource_mapping = self._get_resource_mapping(provider_type, raw_type)

        # Map status
        raw_status = self._extract_raw_status(provider_data, provider_type)
        unified_status = self._map_status(raw_status, provider_type)

        # Map fields
        mapped_data = self._map_fields(provider_data, provider_type)

        # Create unified resource
        unified_resource = ProviderResource(
            resource_id=str(mapped_data.get('id', provider_data.get('id', ''))),
            resource_name=mapped_data.get('name', provider_data.get('name', '')),
            resource_type=resource_mapping.unified_type if resource_mapping else raw_type,
            service_name=resource_mapping.service_name if resource_mapping else 'Unknown',
            region=mapped_data.get('region', 'default'),
            status=unified_status,
            effective_cost=float(mapped_data.get('cost', provider_data.get('cost', 0.0))),
            currency=mapped_data.get('currency', 'RUB'),
            billing_period=mapped_data.get('billing_period', 'monthly'),
            provider_config=provider_data,
            provider_type=provider_type
        )

        # Add custom tags from mapping
        if resource_mapping and resource_mapping.custom_mappings:
            for key, value in resource_mapping.custom_mappings.items():
                if callable(value):
                    try:
                        tag_value = value(provider_data)
                        if tag_value:
                            unified_resource.tags[key] = str(tag_value)
                    except Exception as e:
                        logger.warning(f"Failed to compute custom tag {key}: {e}")
                else:
                    unified_resource.tags[key] = str(value)

        return unified_resource

    def _extract_raw_type(self, provider_data: Dict[str, Any], provider_type: str) -> str:
        """Extract raw resource type from provider data"""
        # Common type fields
        type_fields = ['type', 'resource_type', 'service_type', 'kind']

        for field in type_fields:
            if field in provider_data:
                return str(provider_data[field]).lower()

        # Provider-specific type extraction
        if provider_type == 'beget':
            if 'vps' in provider_data:
                return 'vps'
            elif 'domain' in provider_data:
                return 'domain'
        elif provider_type == 'selectel':
            if 'cloud_vm' in provider_data.get('type', ''):
                return 'server'
            elif 'volume' in provider_data.get('type', ''):
                return 'volume'

        return 'unknown'

    def _extract_raw_status(self, provider_data: Dict[str, Any], provider_type: str) -> str:
        """Extract raw status from provider data"""
        status_fields = ['status', 'state', 'status_code']

        for field in status_fields:
            if field in provider_data:
                return str(provider_data[field]).lower()

        return 'unknown'

    def _get_resource_mapping(self, provider_type: str, raw_type: str) -> Optional[ResourceMapping]:
        """Get resource mapping for provider and raw type"""
        # Check provider-specific mapping
        if provider_type in self._resource_mappings:
            mapping = self._resource_mappings[provider_type].get(raw_type)
            if mapping:
                return mapping

        # Check wildcard mapping
        if '*' in self._resource_mappings:
            return self._resource_mappings['*'].get(raw_type)

        return None

    def _map_status(self, raw_status: str, provider_type: str) -> str:
        """Map raw status to unified status"""
        # Check provider-specific mapping
        if provider_type in self._status_mappings:
            mapping = self._status_mappings[provider_type].get(raw_status)
            if mapping:
                return mapping.unified_status

        # Check wildcard mapping
        if '*' in self._status_mappings:
            mapping = self._status_mappings['*'].get(raw_status)
            if mapping:
                return mapping.unified_status

        # Default to raw status
        return raw_status

    def _map_fields(self, provider_data: Dict[str, Any], provider_type: str) -> Dict[str, Any]:
        """Map field names according to provider mappings"""
        mapped = dict(provider_data)  # Copy original data

        if provider_type in self._field_mappings:
            for raw_field, unified_field in self._field_mappings[provider_type].items():
                if raw_field in provider_data and unified_field not in mapped:
                    mapped[unified_field] = provider_data[raw_field]

        return mapped

    def validate_resource(self, unified_resource: ProviderResource) -> bool:
        """Validate a unified resource"""
        provider_type = unified_resource.provider_type

        if provider_type in self._validators:
            try:
                return self._validators[provider_type](unified_resource)
            except Exception as e:
                logger.warning(f"Validator failed for {provider_type}: {e}")

        # Basic validation
        return bool(
            unified_resource.resource_id and
            unified_resource.resource_name and
            unified_resource.resource_type
        )

    def get_registered_mappings(self, provider_type: str = None) -> Dict[str, Any]:
        """Get all registered mappings"""
        if provider_type:
            return {
                'resource_mappings': {
                    k: v.to_dict() for k, v in self._resource_mappings.get(provider_type, {}).items()
                },
                'status_mappings': {
                    k: v.to_dict() for k, v in self._status_mappings.get(provider_type, {}).items()
                },
                'field_mappings': self._field_mappings.get(provider_type, {}),
                'has_custom_processor': provider_type in self._custom_processors,
                'has_validator': provider_type in self._validators
            }

        # Return all mappings
        return {
            'providers': list(set(list(self._resource_mappings.keys()) +
                                list(self._status_mappings.keys()) +
                                list(self._field_mappings.keys()))),
            'resource_mappings': {k: {k2: v2.to_dict() for k2, v2 in v.items()}
                                for k, v in self._resource_mappings.items()},
            'status_mappings': {k: {k2: v2.to_dict() for k2, v2 in v.items()}
                              for k, v in self._status_mappings.items()},
            'field_mappings': self._field_mappings,
            'custom_processors': list(self._custom_processors.keys()),
            'validators': list(self._validators.keys())
        }


# Global resource registry instance
resource_registry = ResourceRegistry()
