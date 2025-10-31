#!/usr/bin/env python3
"""
Diagnostic script to check snapshot mismatch on resources page
Compares data sources for upper section vs connection cards
"""

from app import create_app
from app.core.models.provider import CloudProvider
from app.core.models.resource import Resource
from app.core.models.sync import SyncSnapshot, ResourceState
from app.core.models.complete_sync import CompleteSync, ProviderSyncReference
from datetime import datetime
import json

app = create_app()

def main():
    with app.app_context():
        # Find user with itl.team connection
        yandex_providers = CloudProvider.query.filter_by(
            provider_type='yandex',
            connection_name='itl.team',
            is_deleted=False
        ).all()
        
        if not yandex_providers:
            print("❌ No Yandex provider found with connection_name='itl.team'")
            return
        
        provider = yandex_providers[0]
        user_id = provider.user_id
        
        print(f"=== SNAPSHOT MISMATCH DIAGNOSTIC ===\n")
        print(f"Provider: {provider.connection_name} (ID: {provider.id})")
        print(f"User ID: {user_id}")
        print(f"Provider Type: {provider.provider_type}\n")
        
        # Check 1: Get data as upper section does (CompleteSync)
        print("=" * 60)
        print("UPPER SECTION DATA SOURCE (CompleteSync)")
        print("=" * 60)
        
        latest_complete_sync = (
            CompleteSync.query
            .filter_by(user_id=user_id, sync_status='success')
            .order_by(CompleteSync.sync_completed_at.desc())
            .first()
        )
        
        if latest_complete_sync:
            print(f"CompleteSync ID: {latest_complete_sync.id}")
            print(f"Completed At: {latest_complete_sync.sync_completed_at}")
            print(f"Total Resources: {latest_complete_sync.total_resources_found}")
            print(f"Total Daily Cost: {latest_complete_sync.total_daily_cost}₽")
            print(f"Total Monthly Cost: {latest_complete_sync.total_monthly_cost}₽")
            
            # Get provider syncs for this complete sync
            print(f"\nProvider Syncs in CompleteSync:")
            for ref in (latest_complete_sync.provider_syncs or []):
                if ref.provider_id == provider.id:
                    print(f"  - Provider {ref.provider_id}: Snapshot {ref.sync_snapshot_id}")
                    print(f"    Status: {ref.sync_status}")
                    
                    # Check ResourceState for this snapshot
                    resource_states = ResourceState.query.filter_by(
                        sync_snapshot_id=ref.sync_snapshot_id
                    ).all()
                    print(f"    ResourceState entries: {len(resource_states)}")
                    
                    if resource_states:
                        resource_ids = [rs.resource_id for rs in resource_states if rs.resource_id]
                        resources = Resource.query.filter(Resource.id.in_(resource_ids)).all()
                        total_cost = sum([r.daily_cost or 0 for r in resources])
                        print(f"    Resources from ResourceState: {len(resources)}")
                        print(f"    Total Cost: {total_cost:.2f}₽/day ({total_cost * 30:.2f}₽/month)")
        else:
            print("❌ No CompleteSync found!")
        
        # Check 2: Get data as connection section does (get_real_user_resources logic)
        print(f"\n{'=' * 60}")
        print("CONNECTION SECTION DATA SOURCE (get_real_user_resources)")
        print("=" * 60)
        
        # Get latest snapshot for provider
        latest_snapshot = SyncSnapshot.query.filter_by(
            provider_id=provider.id,
            sync_status='success'
        ).order_by(SyncSnapshot.created_at.desc()).first()
        
        if latest_snapshot:
            print(f"Latest Snapshot ID: {latest_snapshot.id}")
            print(f"Created At: {latest_snapshot.created_at}")
            print(f"Completed At: {latest_snapshot.sync_completed_at}")
            print(f"Total Resources: {latest_snapshot.total_resources_found}")
            # total_daily_cost doesn't exist in SyncSnapshot, calculate it
            daily_cost = (latest_snapshot.total_monthly_cost or 0) / 30
            print(f"Total Daily Cost: {daily_cost:.2f}₽ (calculated)")
            print(f"Total Monthly Cost: {latest_snapshot.total_monthly_cost}₽")
            
            # Check ResourceState
            resource_states = ResourceState.query.filter_by(
                sync_snapshot_id=latest_snapshot.id
            ).all()
            
            print(f"\nResourceState entries: {len(resource_states)}")
            
            if resource_states:
                resource_ids = [rs.resource_id for rs in resource_states if rs.resource_id]
                resources = Resource.query.filter(Resource.id.in_(resource_ids)).all()
                total_cost = sum([r.daily_cost or 0 for r in resources])
                print(f"Resources from ResourceState: {len(resources)}")
                print(f"Total Cost: {total_cost:.2f}₽/day ({total_cost * 30:.2f}₽/month)")
            else:
                print("⚠️  NO ResourceState entries! Falling back to ALL resources...")
                all_provider_resources = Resource.query.filter_by(provider_id=provider.id).all()
                active_resources = [r for r in all_provider_resources if r.is_active]
                total_cost = sum([r.daily_cost or 0 for r in all_provider_resources])
                total_cost_active = sum([r.daily_cost or 0 for r in active_resources])
                
                print(f"ALL resources for provider: {len(all_provider_resources)}")
                print(f"Active resources: {len(active_resources)}")
                print(f"Total Cost (ALL): {total_cost:.2f}₽/day ({total_cost * 30:.2f}₽/month)")
                print(f"Total Cost (Active): {total_cost_active:.2f}₽/day ({total_cost_active * 30:.2f}₽/month)")
        else:
            print("❌ No SyncSnapshot found!")
        
        # Check 3: Compare snapshots
        print(f"\n{'=' * 60}")
        print("COMPARISON & DIAGNOSIS")
        print("=" * 60)
        
        if latest_complete_sync and latest_snapshot:
            # Check if they reference the same snapshot
            complete_sync_ref = None
            for ref in (latest_complete_sync.provider_syncs or []):
                if ref.provider_id == provider.id:
                    complete_sync_ref = ref
                    break
            
            if complete_sync_ref:
                if complete_sync_ref.sync_snapshot_id == latest_snapshot.id:
                    print("✅ Both use the SAME snapshot!")
                    print(f"   Snapshot ID: {latest_snapshot.id}")
                else:
                    print("❌ MISMATCH! They use DIFFERENT snapshots!")
                    print(f"   CompleteSync uses: {complete_sync_ref.sync_snapshot_id}")
                    print(f"   Connection card uses: {latest_snapshot.id}")
                    
                    # Check dates
                    complete_snap = SyncSnapshot.query.get(complete_sync_ref.sync_snapshot_id)
                    if complete_snap:
                        print(f"\n   CompleteSync snapshot created: {complete_snap.created_at}")
                    print(f"   Latest snapshot created: {latest_snapshot.created_at}")
            
            # Check ResourceState presence
            if complete_sync_ref:
                cs_resource_states = ResourceState.query.filter_by(
                    sync_snapshot_id=complete_sync_ref.sync_snapshot_id
                ).count()
                ls_resource_states = ResourceState.query.filter_by(
                    sync_snapshot_id=latest_snapshot.id
                ).count()
                
                print(f"\nResourceState entries:")
                print(f"   CompleteSync snapshot: {cs_resource_states}")
                print(f"   Latest snapshot: {ls_resource_states}")
                
                if ls_resource_states == 0:
                    print(f"\n❌ PROBLEM: Latest snapshot has NO ResourceState entries!")
                    print(f"   This causes fallback to ALL resources (not filtered by snapshot)")
                    print(f"   Solution: Ensure sync creates ResourceState entries")

if __name__ == '__main__':
    main()

