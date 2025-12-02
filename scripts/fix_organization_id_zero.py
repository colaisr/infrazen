#!/usr/bin/env python3
"""
Fix providers with organization_id = 0
"""
from app import create_app
from app.core.models import db
from app.core.models.user import User
from app.core.models.organization import Organization
from app.core.models.organization_member import OrganizationMember
from app.core.models.provider import CloudProvider
from datetime import datetime

app = create_app()
with app.app_context():
    # Fix providers with organization_id = 0
    providers_with_zero = CloudProvider.query.filter(CloudProvider.organization_id == 0).all()
    print(f'Found {len(providers_with_zero)} providers with organization_id = 0')
    
    for provider in providers_with_zero:
        user = User.query.get(provider.user_id)
        if not user:
            print(f'Skipping provider {provider.id} - user {provider.user_id} not found')
            continue
        
        # Find or create personal org
        member = OrganizationMember.query.filter_by(user_id=user.id, role='owner', is_active=True).first()
        if member:
            org_id = member.organization_id
        else:
            # Create org
            first_name = user.first_name or 'User'
            last_name = user.last_name or ''
            org_name = f'{first_name} {last_name}'.strip() or f'Personal ({user.email})'
            org = Organization(name=org_name)
            db.session.add(org)
            db.session.flush()
            org_id = org.id
            # Add member
            member = OrganizationMember(
                organization_id=org_id,
                user_id=user.id,
                role='owner',
                is_active=True,
                joined_at=datetime.utcnow()
            )
            db.session.add(member)
            print(f'Created org {org_id} for user {user.email}')
        
        provider.organization_id = org_id
        print(f'Fixed provider {provider.id} for user {user.email}: org_id = {org_id}')
    
    db.session.commit()
    print('✅ Fixed all organization_id = 0 values')

