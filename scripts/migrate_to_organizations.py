"""
Data migration script to create personal organizations for all existing users
and migrate all user data to their personal organizations.

This script should be run AFTER running the Alembic migrations that add the
organization tables and organization_id columns.

Usage:
    python scripts/migrate_to_organizations.py
"""
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.core.models import db
from app.core.models.user import User
from app.core.models.organization import Organization
from app.core.models.organization_member import OrganizationMember
from app.core.models.provider import CloudProvider
from app.core.models.resource import Resource
from app.core.models.business_board import BusinessBoard
from app.core.models.chat import ChatSession
from app.core.models.report import GeneratedReport
from app.core.models.recommendations import OptimizationRecommendation
from app.core.models.pricing import PriceComparisonRecommendation
from app.core.models.complete_sync import CompleteSync
from app.core.models.sync import SyncSnapshot
from app.core.models.unrecognized_resource import UnrecognizedResource
from app.core.models.user_provider_preference import UserProviderPreference


def migrate_user_to_organization(user):
    """Create personal organization for a user and migrate all their data"""
    print(f"Processing user {user.id} ({user.email})...")
    
    # Create personal organization
    org_name = f"{user.first_name or 'User'} {user.last_name or ''}".strip() or f"Personal ({user.email})"
    personal_org = Organization(
        name=org_name
    )
    db.session.add(personal_org)
    db.session.flush()  # Get the org ID
    
    print(f"  Created organization: {personal_org.name} (ID: {personal_org.id})")
    
    # Create organization member (user as owner)
    member = OrganizationMember(
        organization_id=personal_org.id,
        user_id=user.id,
        role='owner',
        joined_at=datetime.utcnow(),
        is_active=True
    )
    db.session.add(member)
    
    # Set user's default organization
    user.default_organization_id = personal_org.id
    user.last_active_organization_id = personal_org.id
    
    # Migrate all user data to organization
    migrated_counts = {}
    
    # Migrate providers
    providers = CloudProvider.query.filter_by(user_id=user.id).all()
    for provider in providers:
        provider.organization_id = personal_org.id
    migrated_counts['providers'] = len(providers)
    
    # Migrate resources (via providers)
    provider_ids = [p.id for p in providers]
    if provider_ids:
        resources = Resource.query.filter(Resource.provider_id.in_(provider_ids)).all()
        for resource in resources:
            resource.organization_id = personal_org.id
        migrated_counts['resources'] = len(resources)
    else:
        migrated_counts['resources'] = 0
    
    # Migrate boards
    boards = BusinessBoard.query.filter_by(user_id=user.id).all()
    for board in boards:
        board.organization_id = personal_org.id
    migrated_counts['boards'] = len(boards)
    
    # Migrate chat sessions
    chat_sessions = ChatSession.query.filter_by(user_id=user.id).all()
    for session in chat_sessions:
        session.organization_id = personal_org.id
    migrated_counts['chat_sessions'] = len(chat_sessions)
    
    # Migrate reports
    reports = GeneratedReport.query.filter_by(user_id=user.id).all()
    for report in reports:
        report.organization_id = personal_org.id
    migrated_counts['reports'] = len(reports)
    
    # Migrate recommendations (via resources/providers)
    if provider_ids:
        recommendations = OptimizationRecommendation.query.filter(
            OptimizationRecommendation.provider_id.in_(provider_ids)
        ).all()
        for rec in recommendations:
            rec.organization_id = personal_org.id
        migrated_counts['recommendations'] = len(recommendations)
    else:
        migrated_counts['recommendations'] = 0
    
    # Migrate price comparison recommendations
    price_recs = PriceComparisonRecommendation.query.filter_by(user_id=user.id).all()
    for rec in price_recs:
        rec.organization_id = personal_org.id
    migrated_counts['price_comparison_recommendations'] = len(price_recs)
    
    # Migrate complete syncs
    complete_syncs = CompleteSync.query.filter_by(user_id=user.id).all()
    for sync in complete_syncs:
        sync.organization_id = personal_org.id
    migrated_counts['complete_syncs'] = len(complete_syncs)
    
    # Migrate sync snapshots (via providers)
    if provider_ids:
        snapshots = SyncSnapshot.query.filter(SyncSnapshot.provider_id.in_(provider_ids)).all()
        for snapshot in snapshots:
            snapshot.organization_id = personal_org.id
        migrated_counts['sync_snapshots'] = len(snapshots)
    else:
        migrated_counts['sync_snapshots'] = 0
    
    # Migrate unrecognized resources (via providers)
    if provider_ids:
        unrecognized = UnrecognizedResource.query.filter(
            UnrecognizedResource.provider_id.in_(provider_ids)
        ).all()
        for ur in unrecognized:
            ur.organization_id = personal_org.id
        migrated_counts['unrecognized_resources'] = len(unrecognized)
    else:
        migrated_counts['unrecognized_resources'] = 0
    
    # Migrate user provider preferences
    preferences = UserProviderPreference.query.filter_by(user_id=user.id).all()
    for pref in preferences:
        pref.organization_id = personal_org.id
    migrated_counts['user_provider_preferences'] = len(preferences)
    
    # Commit for this user
    db.session.commit()
    
    print(f"  Migrated data: {migrated_counts}")
    print(f"  ✓ User {user.id} migration complete\n")
    
    return personal_org, migrated_counts


def main():
    """Main migration function"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("Organization Migration Script")
        print("=" * 60)
        print()
        
        # Get all users
        users = User.query.all()
        print(f"Found {len(users)} users to migrate\n")
        
        if len(users) == 0:
            print("No users found. Nothing to migrate.")
            return
        
        # Auto-proceed if running non-interactively (check for --yes flag or stdin not available)
        import sys
        auto_proceed = '--yes' in sys.argv or not sys.stdin.isatty()
        
        if not auto_proceed:
            # Confirm before proceeding
            response = input(f"Proceed with migration for {len(users)} users? (yes/no): ")
            if response.lower() != 'yes':
                print("Migration cancelled.")
                return
        else:
            print(f"Auto-proceeding with migration for {len(users)} users...")
        
        print()
        print("Starting migration...")
        print("-" * 60)
        
        total_counts = {}
        successful_users = 0
        failed_users = 0
        
        for user in users:
            try:
                org, counts = migrate_user_to_organization(user)
                successful_users += 1
                
                # Aggregate counts
                for key, value in counts.items():
                    total_counts[key] = total_counts.get(key, 0) + value
                    
            except Exception as e:
                print(f"  ✗ ERROR migrating user {user.id}: {str(e)}")
                db.session.rollback()
                failed_users += 1
                import traceback
                traceback.print_exc()
                print()
        
        print("-" * 60)
        print("Migration Summary:")
        print(f"  Successful: {successful_users} users")
        print(f"  Failed: {failed_users} users")
        print()
        print("Total migrated data:")
        for key, value in total_counts.items():
            print(f"  {key}: {value}")
        print()
        
        # Verify migration
        print("Verifying migration...")
        orgs_without_data = 0
        orgs_with_data = 0
        
        organizations = Organization.query.all()
        for org in organizations:
            # Check if org has any data
            has_providers = CloudProvider.query.filter_by(organization_id=org.id).count() > 0
            has_resources = Resource.query.filter_by(organization_id=org.id).count() > 0
            has_boards = BusinessBoard.query.filter_by(organization_id=org.id).count() > 0
            
            if has_providers or has_resources or has_boards:
                orgs_with_data += 1
            else:
                orgs_without_data += 1
        
        print(f"  Organizations with data: {orgs_with_data}")
        print(f"  Organizations without data: {orgs_without_data}")
        print()
        
        # Check for unmigrated data
        print("Checking for unmigrated data...")
        unmigrated_providers = CloudProvider.query.filter_by(organization_id=None).count()
        unmigrated_resources = Resource.query.filter_by(organization_id=None).count()
        unmigrated_boards = BusinessBoard.query.filter_by(organization_id=None).count()
        
        if unmigrated_providers > 0 or unmigrated_resources > 0 or unmigrated_boards > 0:
            print(f"  ⚠ WARNING: Found unmigrated data:")
            print(f"    Providers: {unmigrated_providers}")
            print(f"    Resources: {unmigrated_resources}")
            print(f"    Boards: {unmigrated_boards}")
        else:
            print("  ✓ All data migrated successfully!")
        
        print()
        print("=" * 60)
        print("Migration complete!")
        print("=" * 60)


if __name__ == '__main__':
    main()

