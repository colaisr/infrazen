#!/usr/bin/env python3
"""Test if ResourceState can be created in production"""
from app import create_app
from app.core.models.sync import SyncSnapshot, ResourceState
from app.core.models.provider import CloudProvider
from app.core.models.resource import Resource
from app.core.database import db

app = create_app()

def main():
    with app.app_context():
        # Get latest snapshot
        provider = CloudProvider.query.filter_by(
            provider_type='yandex',
            connection_name='itl.team',
            is_deleted=False
        ).first()
        
        if not provider:
            print("❌ Provider not found!")
            return
        
        latest_snapshot = SyncSnapshot.query.filter_by(
            provider_id=provider.id,
            sync_status='success'
        ).order_by(SyncSnapshot.created_at.desc()).first()
        
        if not latest_snapshot:
            print("❌ No snapshot found!")
            return
        
        print(f"Testing ResourceState creation with snapshot {latest_snapshot.id}")
        
        # Get first resource
        resource = Resource.query.filter_by(provider_id=provider.id).first()
        
        if not resource:
            print("❌ No resources found!")
            return
        
        print(f"Using resource: {resource.resource_name} (ID: {resource.id})")
        
        # Try to create ResourceState
        try:
            resource_state = ResourceState(
                sync_snapshot_id=latest_snapshot.id,
                resource_id=resource.id,
                provider_resource_id=resource.resource_id or 'test',
                resource_type=resource.resource_type,
                resource_name=resource.resource_name,
                state_action='created',
                service_name=resource.service_name or 'Test',
                region=resource.region or 'unknown',
                status=resource.status or 'unknown',
                effective_cost=resource.effective_cost or 0.0
            )
            
            resource_state.set_current_state({'test': 'data'})
            
            db.session.add(resource_state)
            db.session.commit()
            
            print("✅ ResourceState created successfully!")
            print(f"   ResourceState ID: {resource_state.id}")
            
            # Clean up
            db.session.delete(resource_state)
            db.session.commit()
            print("✅ Test ResourceState deleted")
            
        except Exception as e:
            print(f"❌ ERROR creating ResourceState: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

if __name__ == '__main__':
    main()

