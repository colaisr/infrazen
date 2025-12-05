#!/usr/bin/env python3
"""
Cleanup script to remove test users and all their related data
"""
from app import create_app
from app.core.database import db
from app.core.models.user import User
from app.core.models.organization_invitation import OrganizationInvitation
from app.core.models.organization_member import OrganizationMember
from app.core.models.organization import Organization
from app.core.models.resource import Resource
from app.core.models.provider import CloudProvider
from app.core.models.sync import SyncSnapshot, ResourceState
from app.core.models.complete_sync import CompleteSync, ProviderSyncReference
from app.core.models.recommendations import OptimizationRecommendation
from app.core.models.pricing import PriceComparisonRecommendation
from app.core.models.user_provider_preference import UserProviderPreference
from app.core.models.resource_tag import ResourceTag
from app.core.models.resource_metric import ResourceMetric
from app.core.models.business_context import BusinessBoard, BoardResource
import sys

def cleanup_user(email):
    """Delete a user and all their related data"""
    print(f"\n{'='*60}")
    print(f"Cleaning up user: {email}")
    print(f"{'='*60}")
    
    # Find user
    user = User.find_by_email(email)
    if not user:
        print(f"  ⚠️  User not found: {email}")
        return False
    
    user_id = user.id
    print(f"  ✓ Found user ID: {user_id}")
    
    # Delete invitations for this email
    invitations = OrganizationInvitation.query.filter_by(email=email.lower()).all()
    if invitations:
        print(f"  ✓ Found {len(invitations)} invitation(s)")
        for inv in invitations:
            db.session.delete(inv)
        db.session.commit()
        print(f"  ✓ Deleted {len(invitations)} invitation(s)")
    
    # Get user's organization memberships
    memberships = OrganizationMember.query.filter_by(user_id=user_id).all()
    org_ids = [m.organization_id for m in memberships]
    print(f"  ✓ Found {len(memberships)} organization membership(s)")
    
    # Delete organization memberships
    for membership in memberships:
        db.session.delete(membership)
    db.session.commit()
    print(f"  ✓ Deleted organization memberships")
    
    # Get user's providers
    providers = CloudProvider.query.filter_by(user_id=user_id).all()
    provider_ids = [p.id for p in providers]
    if provider_ids:
        print(f"  ✓ Found {len(providers)} provider(s)")
        
        # Delete complete syncs and references
        complete_syncs = CompleteSync.query.filter_by(user_id=user_id).all()
        if complete_syncs:
            sync_ids = [cs.id for cs in complete_syncs]
            ProviderSyncReference.query.filter(ProviderSyncReference.complete_sync_id.in_(sync_ids)).delete(synchronize_session=False)
            db.session.commit()
            CompleteSync.query.filter(CompleteSync.id.in_(sync_ids)).delete(synchronize_session=False)
            db.session.commit()
            print(f"  ✓ Deleted {len(complete_syncs)} complete sync(s)")
        
        # Delete snapshots and resource states
        snapshots = SyncSnapshot.query.filter(SyncSnapshot.provider_id.in_(provider_ids)).all()
        if snapshots:
            snapshot_ids = [s.id for s in snapshots]
            ResourceState.query.filter(ResourceState.sync_snapshot_id.in_(snapshot_ids)).delete(synchronize_session=False)
            db.session.commit()
            SyncSnapshot.query.filter(SyncSnapshot.id.in_(snapshot_ids)).delete(synchronize_session=False)
            db.session.commit()
            print(f"  ✓ Deleted {len(snapshots)} snapshot(s)")
        
        # Get resources for these providers
        resources = Resource.query.filter(Resource.provider_id.in_(provider_ids)).all()
        if resources:
            resource_ids = [r.id for r in resources]
            print(f"  ✓ Found {len(resources)} resource(s)")
            
            # Delete resource-related data
            ResourceTag.query.filter(ResourceTag.resource_id.in_(resource_ids)).delete(synchronize_session=False)
            ResourceMetric.query.filter(ResourceMetric.resource_id.in_(resource_ids)).delete(synchronize_session=False)
            db.session.commit()
            
            # Delete recommendations
            OptimizationRecommendation.query.filter(OptimizationRecommendation.resource_id.in_(resource_ids)).delete(synchronize_session=False)
            PriceComparisonRecommendation.query.filter(PriceComparisonRecommendation.resource_id.in_(resource_ids)).delete(synchronize_session=False)
            db.session.commit()
            
            # Delete resources
            Resource.query.filter(Resource.id.in_(resource_ids)).delete(synchronize_session=False)
            db.session.commit()
            print(f"  ✓ Deleted {len(resources)} resource(s)")
        
        # Delete provider recommendations
        OptimizationRecommendation.query.filter(OptimizationRecommendation.provider_id.in_(provider_ids)).delete(synchronize_session=False)
        db.session.commit()
        
        # Delete providers
        CloudProvider.query.filter(CloudProvider.id.in_(provider_ids)).delete(synchronize_session=False)
        db.session.commit()
        print(f"  ✓ Deleted {len(providers)} provider(s)")
    
    # Delete business context data
    boards = BusinessBoard.query.filter_by(user_id=user_id).all()
    if boards:
        board_ids = [b.id for b in boards]
        BoardResource.query.filter(BoardResource.board_id.in_(board_ids)).delete(synchronize_session=False)
        db.session.commit()
        BusinessBoard.query.filter(BusinessBoard.id.in_(board_ids)).delete(synchronize_session=False)
        db.session.commit()
        print(f"  ✓ Deleted {len(boards)} business board(s)")
    
    # Delete user provider preferences
    prefs = UserProviderPreference.query.filter_by(user_id=user_id).all()
    if prefs:
        for pref in prefs:
            db.session.delete(pref)
        db.session.commit()
        print(f"  ✓ Deleted {len(prefs)} provider preference(s)")
    
    # Delete user
    db.session.delete(user)
    db.session.commit()
    print(f"  ✓ Deleted user")
    
    print(f"  ✅ Successfully cleaned up user: {email}")
    return True

def main():
    """Main cleanup function"""
    emails_to_cleanup = [
        'pcdoavsaesqimytfkz@nespj.com',
        'ypwwcbtwqgrpwwoewz@xfavaj.com',
        'cola@yootech.io'
    ]
    
    app = create_app()
    with app.app_context():
        print("🧹 Starting cleanup of test users...")
        print(f"Users to cleanup: {', '.join(emails_to_cleanup)}")
        
        # Confirm deletion
        if '--yes' not in sys.argv:
            response = input("\n⚠️  Are you sure you want to delete these users and all their data? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Cleanup cancelled")
                return
        
        success_count = 0
        for email in emails_to_cleanup:
            try:
                if cleanup_user(email):
                    success_count += 1
            except Exception as e:
                print(f"  ❌ Error cleaning up {email}: {str(e)}")
                db.session.rollback()
        
        print(f"\n{'='*60}")
        print(f"✅ Cleanup complete: {success_count}/{len(emails_to_cleanup)} users cleaned up")
        print(f"{'='*60}")

if __name__ == '__main__':
    main()

