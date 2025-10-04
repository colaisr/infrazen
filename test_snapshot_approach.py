#!/usr/bin/env python3
"""
Test snapshot-based resource display for sel3 provider
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

def test_snapshot_approach():
    """Test that resources are displayed from latest snapshot"""
    print("📸 Testing snapshot-based resource display...")
    
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
            
            # Check current snapshots
            snapshots = SyncSnapshot.query.filter_by(provider_id=sel3_provider.id).order_by(SyncSnapshot.created_at.desc()).limit(3).all()
            print(f"\n📸 Recent snapshots:")
            for i, snapshot in enumerate(snapshots):
                print(f"   {i+1}. Snapshot ID: {snapshot.id}")
                print(f"      Status: {snapshot.sync_status}")
                print(f"      Created: {snapshot.created_at}")
                print(f"      Resources: {snapshot.total_resources_found}")
                print(f"      Created: {snapshot.resources_created}")
                print(f"      Deleted: {snapshot.resources_deleted}")
            
            # Get latest successful snapshot
            latest_snapshot = SyncSnapshot.query.filter_by(
                provider_id=sel3_provider.id, 
                sync_status='success'
            ).order_by(SyncSnapshot.created_at.desc()).first()
            
            if latest_snapshot:
                print(f"\n🎯 Latest successful snapshot: {latest_snapshot.id}")
                
                # Get resources from latest snapshot
                resource_states = ResourceState.query.filter_by(
                    sync_snapshot_id=latest_snapshot.id
                ).all()
                
                print(f"   Resource states in snapshot: {len(resource_states)}")
                
                # Get actual Resource objects
                resource_ids = [rs.resource_id for rs in resource_states if rs.resource_id]
                if resource_ids:
                    resources = Resource.query.filter(Resource.id.in_(resource_ids)).all()
                    print(f"   Actual resources: {len(resources)}")
                    
                    # Show resources by type
                    by_type = {}
                    for resource in resources:
                        resource_type = resource.resource_type
                        if resource_type not in by_type:
                            by_type[resource_type] = []
                        by_type[resource_type].append(resource)
                    
                    print(f"\n📊 Resources from latest snapshot:")
                    for resource_type, resource_list in by_type.items():
                        print(f"   {resource_type}: {len(resource_list)} resources")
                        if resource_type in ['server', 'volume', 'network'] and len(resource_list) <= 5:
                            for resource in resource_list:
                                print(f"     - {resource.resource_name} (ID: {resource.resource_id})")
                else:
                    print("   No resource IDs found in snapshot")
            else:
                print("❌ No successful snapshots found")
            
            # Test the get_real_user_resources function
            print(f"\n🔄 Testing get_real_user_resources function...")
            from app.web.main import get_real_user_resources
            
            user_resources = get_real_user_resources('106509284268867883869')
            sel3_resources = [r for r in user_resources if r.provider_id == sel3_provider.id]
            
            print(f"   Resources returned by get_real_user_resources: {len(sel3_resources)}")
            
            # Show resources by type
            by_type = {}
            for resource in sel3_resources:
                resource_type = resource.resource_type
                if resource_type not in by_type:
                    by_type[resource_type] = []
                by_type[resource_type].append(resource)
            
            print(f"\n📊 Resources from get_real_user_resources:")
            for resource_type, resource_list in by_type.items():
                print(f"   {resource_type}: {len(resource_list)} resources")
                if resource_type in ['server', 'volume', 'network'] and len(resource_list) <= 5:
                    for resource in resource_list:
                        print(f"     - {resource.resource_name} (ID: {resource.resource_id})")
            
            return True
            
        except Exception as e:
            print(f"❌ An unexpected error occurred: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == "__main__":
    test_snapshot_approach()
