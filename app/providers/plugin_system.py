"""
Plugin-based provider system for InfraZen
Enables scalable, maintainable provider implementations
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type
from datetime import datetime
import importlib
import pkgutil
import inspect

logger = logging.getLogger(__name__)


class SyncResult:
    """Standardized sync result across all providers"""

    def __init__(self, success: bool = False, message: str = "", data: Dict = None, errors: List[str] = None, provider_type: str = ""):
        self.success = success
        self.message = message
        self.data = data or {}
        self.errors = errors or []
        self.timestamp = datetime.now()
        self.provider_type = provider_type
        self.resources_synced = 0
        self.total_cost = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'success': self.success,
            'message': self.message,
            'data': self.data,
            'errors': self.errors,
            'timestamp': self.timestamp.isoformat(),
            'provider_type': self.provider_type,
            'resources_synced': self.resources_synced,
            'total_cost': self.total_cost
        }


class ProviderPlugin(ABC):
    """Abstract base class for all provider plugins"""

    def __init__(self, provider_id: int, credentials: Dict[str, Any], config: Dict[str, Any] = None):
        self.provider_id = provider_id
        self.credentials = credentials
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def get_provider_type(self) -> str:
        """Return the provider type identifier"""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return human-readable provider name"""
        pass

    @abstractmethod
    def get_required_credentials(self) -> List[str]:
        """Return list of required credential field names"""
        pass

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to provider API"""
        pass

    @abstractmethod
    def sync_resources(self) -> SyncResult:
        """Sync all resources from provider"""
        pass

    @abstractmethod
    def get_resource_mappings(self) -> Dict[str, Any]:
        """Return resource type mappings for this provider"""
        pass

    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Return provider capabilities and features"""
        pass

    def validate_credentials(self) -> bool:
        """Validate that all required credentials are provided"""
        required = self.get_required_credentials()
        return all(field in self.credentials and self.credentials[field] for field in required)

    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information and metadata"""
        return {
            'provider_type': self.get_provider_type(),
            'provider_name': self.get_provider_name(),
            'capabilities': self.get_capabilities(),
            'resource_mappings': self.get_resource_mappings(),
            'required_credentials': self.get_required_credentials(),
            'version': getattr(self, '__version__', '1.0.0'),
            'last_updated': datetime.now().isoformat()
        }


class ProviderPluginManager:
    """Manages discovery and instantiation of provider plugins"""

    def __init__(self):
        self._plugins = {}  # provider_type -> plugin_class
        self._discovered = False
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def discover_plugins(self) -> None:
        """Discover all available provider plugins"""
        if self._discovered:
            return

        self.logger.info("Discovering provider plugins...")

        # Import the providers package to ensure all plugins are loaded
        import app.providers

        # Get the providers directory path
        providers_path = app.providers.__path__

        # Discover all submodules in the providers package
        for importer, modname, ispkg in pkgutil.iter_modules(providers_path, "app.providers."):
            if ispkg and modname not in ['base', 'plugins']:  # Skip base and plugins directories
                try:
                    # Import the provider module
                    provider_module = importlib.import_module(modname)

                    # Look for plugin classes in the module
                    for name, obj in inspect.getmembers(provider_module):
                        if (inspect.isclass(obj) and
                            issubclass(obj, ProviderPlugin) and
                            obj != ProviderPlugin):

                            # Get provider type from class
                            plugin_instance = obj(0, {}, {})  # Dummy instance to get type
                            provider_type = plugin_instance.get_provider_type()

                            self._plugins[provider_type] = obj
                            self.logger.info(f"Discovered plugin: {provider_type} -> {obj.__name__}")

                except Exception as e:
                    self.logger.warning(f"Failed to load provider plugin {modname}: {e}")

        # Also check for plugins in the plugins subdirectory
        try:
            import app.providers.plugins as plugins_pkg
            plugins_path = plugins_pkg.__path__

            for importer, modname, ispkg in pkgutil.iter_modules(plugins_path, "app.providers.plugins."):
                try:
                    plugin_module = importlib.import_module(modname)

                    # Look for plugin classes
                    for name, obj in inspect.getmembers(plugin_module):
                        if (inspect.isclass(obj) and
                            issubclass(obj, ProviderPlugin) and
                            obj != ProviderPlugin):

                            plugin_instance = obj(0, {}, {})
                            provider_type = plugin_instance.get_provider_type()

                            self._plugins[provider_type] = obj
                            self.logger.info(f"Discovered plugin: {provider_type} -> {obj.__name__}")

                except Exception as e:
                    self.logger.warning(f"Failed to load plugin {modname}: {e}")

        except ImportError:
            self.logger.debug("No plugins subdirectory found")

        self._discovered = True
        self.logger.info(f"Plugin discovery complete. Found {len(self._plugins)} plugins: {list(self._plugins.keys())}")

    def get_available_providers(self) -> List[str]:
        """Get list of available provider types"""
        if not self._discovered:
            self.discover_plugins()
        return list(self._plugins.keys())

    def get_plugin_class(self, provider_type: str) -> Optional[Type[ProviderPlugin]]:
        """Get plugin class for a provider type"""
        if not self._discovered:
            self.discover_plugins()
        return self._plugins.get(provider_type)

    def create_plugin_instance(self, provider_type: str, provider_id: int,
                             credentials: Dict[str, Any], config: Dict[str, Any] = None) -> Optional[ProviderPlugin]:
        """Create a plugin instance for a provider"""
        plugin_class = self.get_plugin_class(provider_type)
        if not plugin_class:
            self.logger.error(f"No plugin found for provider type: {provider_type}")
            return None

        try:
            instance = plugin_class(provider_id, credentials, config)
            self.logger.debug(f"Created plugin instance: {provider_type} for provider {provider_id}")
            return instance
        except Exception as e:
            self.logger.error(f"Failed to create plugin instance for {provider_type}: {e}")
            return None

    def get_provider_info(self, provider_type: str) -> Optional[Dict[str, Any]]:
        """Get information about a provider type"""
        plugin_class = self.get_plugin_class(provider_type)
        if not plugin_class:
            return None

        try:
            # Create dummy instance to get info
            dummy_instance = plugin_class(0, {}, {})
            return dummy_instance.get_provider_info()
        except Exception as e:
            self.logger.error(f"Failed to get provider info for {provider_type}: {e}")
            return None

    def validate_provider_credentials(self, provider_type: str, credentials: Dict[str, Any]) -> bool:
        """Validate credentials for a provider type"""
        plugin_class = self.get_plugin_class(provider_type)
        if not plugin_class:
            return False

        try:
            dummy_instance = plugin_class(0, credentials, {})
            return dummy_instance.validate_credentials()
        except Exception as e:
            self.logger.error(f"Failed to validate credentials for {provider_type}: {e}")
            return False


# Global plugin manager instance
plugin_manager = ProviderPluginManager()
