"""
Provider configuration management system
Handles provider-specific configuration schemas and validation
"""
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CredentialType(Enum):
    """Types of credentials supported"""
    USERNAME_PASSWORD = "username_password"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    TOKEN = "token"
    CERTIFICATE = "certificate"


@dataclass
class CredentialSchema:
    """Schema for provider credentials"""
    field_name: str
    field_type: str
    required: bool
    description: str
    validation_pattern: Optional[str] = None
    example: Optional[str] = None


@dataclass
class ProviderConfiguration:
    """Complete configuration schema for a provider"""
    provider_type: str
    provider_name: str
    credential_type: CredentialType
    credentials_schema: List[CredentialSchema]
    default_config: Dict[str, Any]
    capabilities: Dict[str, Any]
    regions: List[str]
    api_endpoints: List[str]

    def get_credential_fields(self) -> List[str]:
        """Get list of required credential field names"""
        return [cred.field_name for cred in self.credentials_schema if cred.required]

    def validate_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Validate credentials against schema"""
        errors = []
        warnings = []

        # Check required fields
        required_fields = self.get_credential_fields()
        for field in required_fields:
            if field not in credentials or not credentials[field]:
                errors.append(f"Missing required credential: {field}")

        # Validate field formats
        for cred_schema in self.credentials_schema:
            field_name = cred_schema.field_name
            if field_name in credentials:
                value = credentials[field_name]
                if cred_schema.validation_pattern:
                    import re
                    if not re.match(cred_schema.validation_pattern, str(value)):
                        errors.append(f"Invalid format for {field_name}")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }


class ConfigurationManager:
    """Manages provider configurations"""

    def __init__(self):
        self._configurations: Dict[str, ProviderConfiguration] = {}
        self._initialize_configurations()

    def _initialize_configurations(self):
        """Initialize built-in provider configurations"""

        # Beget configuration
        beget_config = ProviderConfiguration(
            provider_type="beget",
            provider_name="Beget Hosting",
            credential_type=CredentialType.USERNAME_PASSWORD,
            credentials_schema=[
                CredentialSchema(
                    field_name="username",
                    field_type="string",
                    required=True,
                    description="Beget account username/login",
                    example="your_username"
                ),
                CredentialSchema(
                    field_name="password",
                    field_type="password",
                    required=True,
                    description="Beget account password",
                    example="your_password"
                ),
                CredentialSchema(
                    field_name="api_url",
                    field_type="url",
                    required=False,
                    description="Beget API URL (optional)",
                    example="https://api.beget.com",
                    validation_pattern=r"^https?://.*"
                )
            ],
            default_config={
                "api_url": "https://api.beget.com",
                "timeout": 30,
                "retries": 3
            },
            capabilities={
                "supports_resources": True,
                "supports_metrics": True,
                "supports_cost_data": True,
                "supports_vps": True,
                "supports_domains": True,
                "supports_databases": True,
                "supports_ftp": True,
                "supports_email": True
            },
            regions=["global"],
            api_endpoints=[
                "https://api.beget.com/v1/auth",
                "https://api.beget.com/v1/vps",
                "https://api.beget.com/api/domain",
                "https://api.beget.com/api/database"
            ]
        )
        self._configurations["beget"] = beget_config

        # Selectel configuration
        selectel_config = ProviderConfiguration(
            provider_type="selectel",
            provider_name="Selectel Cloud",
            credential_type=CredentialType.USERNAME_PASSWORD,
            credentials_schema=[
                CredentialSchema(
                    field_name="username",
                    field_type="string",
                    required=True,
                    description="Selectel account username",
                    example="your_username"
                ),
                CredentialSchema(
                    field_name="password",
                    field_type="password",
                    required=True,
                    description="Selectel account password",
                    example="your_password"
                ),
                CredentialSchema(
                    field_name="account_id",
                    field_type="string",
                    required=True,
                    description="Selectel account ID",
                    example="12345",
                    validation_pattern=r"^\d+$"
                )
            ],
            default_config={
                "billing_api_url": "https://my.selectel.ru/api/v2",
                "openstack_api_url": "https://api.selectel.ru",
                "timeout": 30,
                "retries": 3
            },
            capabilities={
                "supports_resources": True,
                "supports_metrics": True,
                "supports_cost_data": True,
                "supports_vms": True,
                "supports_volumes": True,
                "supports_kubernetes": True,
                "supports_databases": True,
                "supports_s3": True,
                "supports_load_balancers": True,
                "sync_method": "billing_first"
            },
            regions=["ru-1", "ru-2", "ru-3", "ru-7", "ru-8", "ru-9", "kz-1"],
            api_endpoints=[
                "https://my.selectel.ru/api/v2/billing",
                "https://api.selectel.ru/compute",
                "https://api.selectel.ru/storage",
                "https://api.selectel.ru/network"
            ]
        )
        self._configurations["selectel"] = selectel_config

    def register_configuration(self, config: ProviderConfiguration) -> None:
        """Register a new provider configuration"""
        self._configurations[config.provider_type] = config
        logger.info(f"Registered configuration for provider: {config.provider_type}")

    def get_configuration(self, provider_type: str) -> Optional[ProviderConfiguration]:
        """Get configuration for a provider type"""
        return self._configurations.get(provider_type)

    def get_available_providers(self) -> List[str]:
        """Get list of configured provider types"""
        return list(self._configurations.keys())

    def validate_provider_credentials(self, provider_type: str, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Validate credentials for a provider"""
        config = self.get_configuration(provider_type)
        if not config:
            return {
                'valid': False,
                'errors': [f"No configuration found for provider: {provider_type}"],
                'warnings': []
            }

        return config.validate_credentials(credentials)

    def get_provider_setup_guide(self, provider_type: str) -> Dict[str, Any]:
        """Get setup guide for a provider"""
        config = self.get_configuration(provider_type)
        if not config:
            return {}

        return {
            'provider_type': config.provider_type,
            'provider_name': config.provider_name,
            'credential_type': config.credential_type.value,
            'required_credentials': [
                {
                    'field': cred.field_name,
                    'type': cred.field_type,
                    'description': cred.description,
                    'example': cred.example,
                    'required': cred.required
                }
                for cred in config.credentials_schema
            ],
            'setup_steps': self._get_setup_steps(provider_type),
            'documentation_links': self._get_documentation_links(provider_type)
        }

    def _get_setup_steps(self, provider_type: str) -> List[str]:
        """Get setup steps for a provider"""
        steps = {
            'beget': [
                "1. Create a Beget hosting account at https://beget.com",
                "2. Enable API access in your Beget control panel",
                "3. Generate or retrieve your API credentials (username/password)",
                "4. Test the connection in InfraZen before adding the provider"
            ],
            'selectel': [
                "1. Create a Selectel cloud account at https://selectel.ru",
                "2. Enable API access and get your account ID",
                "3. Generate service user credentials with appropriate permissions",
                "4. Configure billing API access if needed",
                "5. Test the connection in InfraZen before adding the provider"
            ]
        }
        return steps.get(provider_type, [])

    def _get_documentation_links(self, provider_type: str) -> List[str]:
        """Get documentation links for a provider"""
        links = {
            'beget': [
                "https://beget.com/ru/docs/api",
                "https://beget.com/ru/kb"
            ],
            'selectel': [
                "https://developers.selectel.ru/",
                "https://docs.selectel.ru/"
            ]
        }
        return links.get(provider_type, [])


# Global configuration manager instance
configuration_manager = ConfigurationManager()
