#!/usr/bin/env python3
"""
Quick script to populate organization_id for existing data
Run this BEFORE making organization_id NOT NULL
"""
from app import create_app
from app.core.models import db
from app.core.models.user import User
from app.core.models.organization import Organization
from app.core.models.organization_member import OrganizationMember
from app.core.models.provider import CloudProvider
from app.core.models.resource import Resource
from datetime import datetime

app = create_app()
with app.app_context():
    users = User.query.all()
    print(f'Found {len(users)} users')
    
    for user in users:
        # Create personal org name
        org_name = f"{user.first_name or 'User'} {user.last_name or ''}".strip() or f"Personal ({user.email})"
        
        # Check if user already has a personal org
        personal_org = None
        memberships = OrganizationMember.query.filter_by(user_id=user.id, role='owner', is_active=True).all()
        if memberships:
            personal_org = Organization.query.get(memberships[0].organization_id)
        
        if not personal_org:
            personal_org = Organization(name=org_name)
            db.session.add(personal_org)
            db.session.flush()
            print(f'Created org for user {user.email}: {personal_org.id} ({personal_org.name})')
            
            # Add user as owner
            member = OrganizationMember(
                organization_id=personal_org.id,
                user_id=user.id,
                role='owner',
                is_active=True,
                joined_at=datetime.utcnow()
            )
            db.session.add(member)
        
        # Update all user's data
        updated_providers = CloudProvider.query.filter_by(user_id=user.id).update({'organization_id': personal_org.id})
        updated_resources = Resource.query.filter_by(user_id=user.id).update({'organization_id': personal_org.id})
        
        if updated_providers > 0 or updated_resources > 0:
            print(f'Updated {updated_providers} providers and {updated_resources} resources for user {user.email}')
    
    db.session.commit()
    print('✅ Migration complete!')

