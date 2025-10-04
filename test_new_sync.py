#!/usr/bin/env python3
"""
Test new sync to create proper ResourceState entries
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.core.database import db
from app.core.models.provider import CloudProvider
from app.core.models.resource import Resource
from app.core.models.sync import SyncSnapshot, ResourceState
from app.providers.selectel.service import SelectelService
import json

def test_new_sync():
    """Test new sync to create proper ResourceState entries"""
    print("🔄 Testing new sync to create ResourceState entries...")
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            # Get sel3 provider
            sel3_provider = CloudProvider.query.filter_by(connection_name='sel3').first()
            
            if not sel3_provider:
                print("❌ sel3 provider not found")
                return False
            
            print(f"✅ Found sel3 provider (ID: {sel3_provider.id})")
            
            # Check current state
            all_resources = Resource.query.filter_by(provider_id=sel3_provider.id).all()
            active_resources = Resource.query.filter_by(provider_id=sel3_provider.id, is_active=True).all()
            inactive_resources = Resource.query.filter_by(provider_id=sel3_provider.id, is_active=False).all()
            
            print(f"\n📊 Current state:")
            print(f"   Total resources: {len(all_resources)}")
            print(f"   Active resources: {len(active_resources)}")
            print(f"   Inactive resources: {len(inactive_resources)}")
            
            # Show active resources
            if active_resources:
                print(f"\n🎯 Active resources:")
                by_type = {}
                for resource in active_resources:
                    resource_type = resource.resource_type
                    if resource_type not in by_type:
                        by_type[resource_type] = []
                    by_type[resource_type].append(resource)
                
                for resource_type, resource_list in by_type.items():
                    print(f"   {resource_type}: {len(resource_list)} resources")
                    if resource_type in ['server', 'volume', 'network'] and len(resource_list) <= 5:
                        for resource in resource_list:
                            print(f"     - {resource.resource_name} (ID: {resource.resource_id})")
            
            print(f"\n🔄 Running new sync...")
            
            # Run sync
            service = SelectelService(sel3_provider)
            sync_result = service.sync_resources()
            
            if sync_result.get('success'):
                print("✅ Sync successful!")
                print(f"   Resources synced: {sync_result.get('resources_synced')}")
                print(f"   Message: {sync_result.get('message')}")
                print(f"   Sync snapshot ID: {sync_result.get('sync_snapshot_id')}")
                
                # Check the new snapshot
                snapshot_id = sync_result.get('sync_snapshot_id')
                if snapshot_id:
                    snapshot = SyncSnapshot.query.get(snapshot_id)
                    if snapshot:
                        print(f"\n📸 New snapshot details:")
                        print(f"   ID: {snapshot.id}")
                        print(f"   Status: {snapshot.sync_status}")
                        print(f"   Resources found: {snapshot.total_resources_found}")
                        print(f"   Resources created: {snapshot.resources_created}")
                        print(f"   Resources deleted: {snapshot.resources_deleted}")
                        
                        # Check ResourceState entries
                        resource_states = ResourceState.query.filter_by(sync_snapshot_id=snapshot.id).all()
                        print(f"   Resource states created: {len(resource_states)}")
                        
                        if resource_states:
                            print(f"\n📊 Resource states by action:")
                            by_action = {}
                            for rs in resource_states:
                                action = rs.state_action
                                if action not in by_action:
                                    by_action[action] = []
                                by_action[action].append(rs)
                            
                            for action, states in by_action.items():
                                print(f"   {action}: {len(states)} resources")
                                if action in ['created', 'updated'] and len(states) <= 5:
                                    for state in states:
                                        print(f"     - {state.resource_type}: {state.resource_name}")
                
                return True
                
            else:
                print(f"❌ Sync failed: {sync_result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ An unexpected error occurred: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == "__main__":
    test_new_sync()
