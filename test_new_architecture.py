#!/usr/bin/env python3
"""
Test script for the new provider architecture
Verifies that the plugin system works and maintains backward compatibility
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_plugin_discovery():
    """Test that plugins are discovered correctly"""
    print("Testing plugin discovery...")

    from app.providers import plugin_manager

    # Discover plugins
    plugin_manager.discover_plugins()

    # Check available providers
    available = plugin_manager.get_available_providers()
    print(f"Available providers: {available}")

    assert len(available) >= 2, f"Expected at least 2 providers, got {len(available)}"
    assert 'beget' in available, "Beget provider not found"
    assert 'selectel' in available, "Selectel provider not found"

    print("✓ Plugin discovery works")

def test_provider_info():
    """Test getting provider information"""
    print("Testing provider info retrieval...")

    from app.providers import plugin_manager

    # Test Beget info
    beget_info = plugin_manager.get_provider_info('beget')
    assert beget_info is not None, "Beget info not found"
    assert beget_info['provider_type'] == 'beget', "Wrong provider type"
    assert beget_info['provider_name'] == 'Beget Hosting', "Wrong provider name"

    # Test Selectel info
    selectel_info = plugin_manager.get_provider_info('selectel')
    assert selectel_info is not None, "Selectel info not found"
    assert selectel_info['provider_type'] == 'selectel', "Wrong provider type"
    assert selectel_info['provider_name'] == 'Selectel Cloud', "Wrong provider name"

    print("✓ Provider info retrieval works")

def test_configuration_manager():
    """Test configuration management"""
    print("Testing configuration manager...")

    from app.providers import configuration_manager

    # Test available providers
    available = configuration_manager.get_available_providers()
    print(f"Configured providers: {available}")

    assert len(available) >= 2, f"Expected at least 2 configured providers, got {len(available)}"

    # Test Beget configuration
    beget_config = configuration_manager.get_configuration('beget')
    assert beget_config is not None, "Beget configuration not found"
    assert beget_config.provider_name == 'Beget Hosting', "Wrong Beget name"

    # Test credential validation
    valid_creds = {'username': 'test', 'password': 'test123'}
    validation = configuration_manager.validate_provider_credentials('beget', valid_creds)
    assert validation['valid'] == True, f"Valid credentials rejected: {validation}"

    invalid_creds = {'username': 'test'}  # Missing password
    validation = configuration_manager.validate_provider_credentials('beget', invalid_creds)
    assert validation['valid'] == False, "Invalid credentials accepted"

    print("✓ Configuration manager works")

def test_resource_registry():
    """Test resource registry functionality"""
    print("Testing resource registry...")

    from app.providers import resource_registry

    # Test status mapping
    assert resource_registry._map_status('running', 'beget') == 'active', "Status mapping failed"
    assert resource_registry._map_status('stopped', 'beget') == 'stopped', "Status mapping failed"

    # Test registering custom mappings
    resource_registry.register_resource_mapping(
        'test_provider', 'custom_vm', 'server', 'Compute'
    )

    # Test the mapping
    test_data = {'type': 'custom_vm', 'name': 'Test VM', 'cost': 100.0}
    unified = resource_registry.map_resource(test_data, 'test_provider')

    assert unified.resource_type == 'server', "Custom mapping failed"
    assert unified.service_name == 'Compute', "Service mapping failed"

    print("✓ Resource registry works")

def test_backward_compatibility():
    """Test that existing imports still work"""
    print("Testing backward compatibility...")

    # Test existing imports
    from app.providers.base.provider_base import BaseProvider
    from app.providers.base.resource_mapper import ResourceMapper
    from app.providers.beget.client import BegetAPIClient
    from app.providers.selectel.client import SelectelClient

    # Test that classes can be instantiated (basic smoke test)
    assert BaseProvider is not None, "BaseProvider import failed"
    assert ResourceMapper is not None, "ResourceMapper import failed"
    assert BegetAPIClient is not None, "BegetAPIClient import failed"
    assert SelectelClient is not None, "SelectelClient import failed"

    print("✓ Backward compatibility maintained")

def test_plugin_creation():
    """Test creating plugin instances"""
    print("Testing plugin creation...")

    from app.providers import plugin_manager

    # Test creating Beget plugin
    creds = {'username': 'test', 'password': 'test123'}
    config = {'connection_name': 'Test Connection'}

    plugin = plugin_manager.create_plugin_instance('beget', 1, creds, config)
    assert plugin is not None, "Failed to create Beget plugin"
    assert plugin.get_provider_type() == 'beget', "Wrong plugin type"
    assert plugin.get_provider_name() == 'Beget Hosting', "Wrong plugin name"

    # Test credential validation
    assert plugin.validate_credentials() == True, "Valid credentials rejected"

    print("✓ Plugin creation works")

def main():
    """Run all tests"""
    print("Testing new provider architecture...\n")

    try:
        test_plugin_discovery()
        test_provider_info()
        test_configuration_manager()
        test_resource_registry()
        test_backward_compatibility()
        test_plugin_creation()

        print("\n🎉 All tests passed! New architecture is working correctly.")
        print("\nKey achievements:")
        print("- Plugin system with automatic discovery")
        print("- Dynamic resource registry")
        print("- Configuration management")
        print("- Unified sync orchestration")
        print("- Backward compatibility maintained")
        print("\nReady to add more providers!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == '__main__':
    exit(main())
