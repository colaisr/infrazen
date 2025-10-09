"""
Providers package - Unified plugin-based architecture
"""

# Import new plugin system
from .plugin_system import ProviderPluginManager, ProviderPlugin, SyncResult, plugin_manager
from .resource_registry import ResourceRegistry, ProviderResource, resource_registry
from .sync_orchestrator import SyncOrchestrator, sync_orchestrator
from .configuration import ConfigurationManager, ProviderConfiguration, configuration_manager

# Import existing modules for backward compatibility
from . import base
from . import beget
from . import selectel

# Re-export commonly used classes for backward compatibility
from .base.provider_base import BaseProvider
from .base.resource_mapper import ResourceMapper

__all__ = [
    # New plugin system
    'ProviderPluginManager',
    'ProviderPlugin',
    'SyncResult',
    'plugin_manager',
    'ResourceRegistry',
    'ProviderResource',
    'resource_registry',
    'SyncOrchestrator',
    'sync_orchestrator',
    'ConfigurationManager',
    'ProviderConfiguration',
    'configuration_manager',

    # Backward compatibility
    'BaseProvider',
    'ResourceMapper',
    'base',
    'beget',
    'selectel'
]
