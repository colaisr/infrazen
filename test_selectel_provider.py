#!/usr/bin/env python3
"""
Comprehensive test script for Selectel provider integration
Tests both API key and service account authentication methods
"""

from app import create_app
from app.core.models.provider import CloudProvider
from app.providers.selectel.client import SelectelClient
import json
import sys

def test_selectel_provider():
    """Test Selectel provider with both authentication methods"""
    
    app = create_app()
    with app.app_context():
        # Get the Selectel provider
        provider = CloudProvider.query.filter_by(provider_type='selectel').first()
        
        if not provider:
            print('❌ No Selectel provider found')
            return False
        
        print(f'🧪 Testing Selectel Provider: {provider.connection_name}')
        print('=' * 60)
        
        credentials = json.loads(provider.credentials)
        test_results = {
            'api_key_auth': False,
            'service_account_auth': False,
            'iam_token_generation': False,
            'openstack_apis': False,
            'full_resource_discovery': False
        }
        
        # Test 1: API Key Authentication (Basic Selectel APIs)
        print('\n📋 Test 1: API Key Authentication (Basic Selectel APIs)')
        print('-' * 50)
        
        try:
            # Test basic API connection with just API key
            api_key = credentials.get('api_key')
            basic_client = SelectelClient(api_key=api_key)
            
            # Test account info
            account_info = basic_client.get_account_info()
            account_name = account_info.get('account', {}).get('name', 'Unknown')
            print(f'✅ Account info: {account_name}')
            
            # Test projects
            projects = basic_client.get_projects()
            print(f'✅ Projects: {len(projects)} found')
            if projects:
                print(f'   First project: {projects[0].get("name", "Unknown")}')
            
            # Test users
            users = basic_client.get_users()
            print(f'✅ Users: {len(users)} found')
            if users:
                print(f'   First user: {users[0].get("name", "Unknown")}')
            
            test_results['api_key_auth'] = True
                
        except Exception as e:
            print(f'❌ API Key test failed: {str(e)}')
        
        # Test 2: Service Account Authentication (OpenStack APIs)
        print('\n🔐 Test 2: Service Account Authentication (OpenStack APIs)')
        print('-' * 50)
        
        try:
            # Test with service account credentials
            service_client = SelectelClient(
                api_key=credentials.get('api_key'),
                account_id=credentials.get('account_id'),
                service_username=credentials.get('service_username'),
                service_password=credentials.get('service_password')
            )
            
            # Test IAM token generation
            print('Testing IAM token generation...')
            iam_token = service_client._get_iam_token()
            print(f'✅ IAM token generated: {iam_token[:20]}...')
            test_results['iam_token_generation'] = True
            
            # Test OpenStack servers API
            print('Testing OpenStack servers API...')
            servers = service_client.get_openstack_servers()
            print(f'✅ Servers: {len(servers)} found')
            if servers:
                for i, server in enumerate(servers[:2]):
                    print(f'   {i+1}. {server.get("name", "Unknown")} (Status: {server.get("status", "Unknown")})')
            
            # Test OpenStack volumes API
            print('Testing OpenStack volumes API...')
            volumes = service_client.get_openstack_volumes()
            print(f'✅ Volumes: {len(volumes)} found')
            if volumes:
                for i, volume in enumerate(volumes[:2]):
                    print(f'   {i+1}. {volume.get("name", "Unknown")} (Size: {volume.get("size", "Unknown")} GB)')
            
            # Test OpenStack networks API
            print('Testing OpenStack networks API...')
            networks = service_client.get_openstack_networks()
            print(f'✅ Networks: {len(networks)} found')
            if networks:
                for i, network in enumerate(networks[:2]):
                    print(f'   {i+1}. {network.get("name", "Unknown")} (Status: {network.get("admin_state_up", "Unknown")})')
            
            test_results['service_account_auth'] = True
            test_results['openstack_apis'] = True
                    
        except Exception as e:
            print(f'❌ Service Account test failed: {str(e)}')
            import traceback
            traceback.print_exc()
        
        # Test 3: Full Resource Discovery
        print('\n🔄 Test 3: Full Resource Discovery')
        print('-' * 50)
        
        try:
            # Test get_all_resources method
            all_resources = service_client.get_all_resources()
            
            print(f'✅ All resources discovered:')
            total_resources = 0
            for resource_type, resource_list in all_resources.items():
                if isinstance(resource_list, list):
                    count = len(resource_list)
                    total_resources += count
                    print(f'   {resource_type}: {count} items')
                elif isinstance(resource_list, dict):
                    print(f'   {resource_type}: {type(resource_list)}')
                else:
                    print(f'   {resource_type}: {resource_list}')
            
            # Check for errors
            if 'error' in all_resources and all_resources['error']:
                print(f'❌ Error in resource discovery: {all_resources["error"]}')
            else:
                print(f'✅ No errors in resource discovery (Total: {total_resources} resources)')
                test_results['full_resource_discovery'] = True
                
        except Exception as e:
            print(f'❌ Full resource discovery failed: {str(e)}')
        
        # Test 4: Authentication Credentials Summary
        print('\n🔑 Test 4: Authentication Credentials Summary')
        print('-' * 50)
        
        print(f'API Key: {credentials.get("api_key", "Not found")[:20]}...')
        print(f'Account ID: {credentials.get("account_id", "Not found")}')
        print(f'Service Username: {credentials.get("service_username", "Not found")}')
        print(f'Service UID: {credentials.get("service_uid", "Not found")}')
        print(f'Service Password: {"***" if credentials.get("service_password") else "Not found"}')
        
        # Test 5: Provider Status
        print('\n📊 Test 5: Provider Status')
        print('-' * 50)
        
        print(f'Provider ID: {provider.id}')
        print(f'Connection Name: {provider.connection_name}')
        print(f'Is Active: {provider.is_active}')
        print(f'Last Sync: {provider.last_sync}')
        print(f'Sync Status: {provider.sync_status}')
        print(f'Sync Error: {provider.sync_error or "None"}')
        
        # Final Results
        print('\n' + '=' * 60)
        print('🎯 Selectel Provider Test Results:')
        print('-' * 30)
        
        passed_tests = 0
        total_tests = len(test_results)
        
        for test_name, result in test_results.items():
            status = '✅ PASS' if result else '❌ FAIL'
            test_display = test_name.replace('_', ' ').title()
            print(f'   {test_display}: {status}')
            if result:
                passed_tests += 1
        
        print(f'\n📈 Overall Result: {passed_tests}/{total_tests} tests passed')
        
        if passed_tests == total_tests:
            print('🎉 All tests passed! Selectel provider is working correctly.')
            return True
        else:
            print('⚠️  Some tests failed. Check the output above for details.')
            return False

if __name__ == '__main__':
    success = test_selectel_provider()
    sys.exit(0 if success else 1)
