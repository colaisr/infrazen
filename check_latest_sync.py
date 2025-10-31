#!/usr/bin/env python3
from app import create_app
from app.core.models.sync import SyncSnapshot, ResourceState
from app.core.models.provider import CloudProvider
from app.core.models.resource import Resource
from datetime import datetime

app = create_app()

def main():
    with app.app_context():
        # Find Yandex provider
        provider = CloudProvider.query.filter_by(
            provider_type='yandex',
            connection_name='itl.team',
            is_deleted=False
        ).first()
        
        if not provider:
            print("❌ Provider not found!")
            return
        
        print(f"=== PROVIDER: {provider.connection_name} (ID: {provider.id}) ===\n")
        
        # Get latest snapshot
        latest_snapshot = SyncSnapshot.query.filter_by(
            provider_id=provider.id,
            sync_status='success'
        ).order_by(SyncSnapshot.created_at.desc()).first()
        
        if not latest_snapshot:
            print("❌ No successful snapshot found!")
            return
        
        print(f"Latest Snapshot ID: {latest_snapshot.id}")
        print(f"Created At: {latest_snapshot.created_at}")
        print(f"Total Resources Found: {latest_snapshot.total_resources_found}")
        print(f"Total Monthly Cost: {latest_snapshot.total_monthly_cost}₽\n")
        
        # Check ResourceState entries
        resource_states = ResourceState.query.filter_by(
            sync_snapshot_id=latest_snapshot.id
        ).all()
        
        print(f"ResourceState entries: {len(resource_states)}")
        
        if len(resource_states) == 0:
            print("\n❌ PROBLEM: No ResourceState entries found!")
            print("   Connection card will fallback to ALL resources query")
            print(f"   All resources for provider: {Resource.query.filter_by(provider_id=provider.id).count()}")
            print(f"   Active resources: {Resource.query.filter_by(provider_id=provider.id, is_active=True).count()}")
        else:
            print(f"\n✅ ResourceState entries found!")
            resource_ids = [rs.resource_id for rs in resource_states if rs.resource_id]
            resources = Resource.query.filter(Resource.id.in_(resource_ids)).all()
            active_count = len([r for r in resources if r.is_active])
            total_cost = sum([r.daily_cost or 0 for r in resources]) * 30
            
            print(f"   Resources from ResourceState: {len(resources)}")
            print(f"   Active resources: {active_count}")
            print(f"   Total Monthly Cost: {total_cost:.2f}₽")
            
            # Show breakdown
            print(f"\n   Breakdown by state_action:")
            from collections import Counter
            actions = Counter([rs.state_action for rs in resource_states])
            for action, count in actions.items():
                print(f"     - {action}: {count}")

if __name__ == '__main__':
    main()

