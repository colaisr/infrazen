"""Add Cloud.ru admin credentials placeholder

Revision ID: a1b2c3d4e5f6
Revises: <latest>
Create Date: 2025-12-17 15:00:00.000000

This migration creates a placeholder for Cloud.ru admin credentials.
Actual credentials should be configured via admin UI or API.

Run this migration, then configure credentials via:
- Admin UI: /admin/providers
- Admin API: POST /api/admin/providers/cloud-ru/credentials
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = '8a9b0c1d2e3f'  # add_invitation_token_to_organization_invitations
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add Cloud.ru to provider catalog and admin credentials placeholder
    
    This migration:
    1. Adds Cloud.ru to provider_catalog (so it appears in "Available Providers")
    2. Creates an inactive placeholder for admin credentials
    """
    conn = op.get_bind()
    
    # Step 1: Add Cloud.ru to provider_catalog
    try:
        # Check if Cloud.ru already exists in catalog
        result = conn.execute(
            text("SELECT id FROM provider_catalog WHERE provider_type = 'cloud-ru'")
        ).fetchone()
        
        if result:
            print("✅ Cloud.ru already exists in provider_catalog")
        else:
            # Insert Cloud.ru into provider_catalog
            conn.execute(
                text("""
                    INSERT INTO provider_catalog
                    (provider_type, display_name, description, is_enabled, has_pricing_api, 
                     pricing_method, website_url, documentation_url, supported_regions, 
                     sync_status, created_at, updated_at)
                    VALUES
                    ('cloud-ru', 'Cloud.ru', 'Russian cloud platform offering compute, storage, databases, and managed services', 
                     true, true, 'api', 'https://cloud.ru', 'https://cloud.ru/docs', 
                     '["ru.AZ-1", "ru.AZ-2", "ru.AZ-3"]', 'never', NOW(), NOW())
                """)
            )
            print("✅ Added Cloud.ru to provider_catalog")
    except Exception as e:
        print(f"⚠️  Error adding Cloud.ru to provider_catalog: {e}")
        # Continue with credentials even if catalog update fails
    
    # Step 2: Add Cloud.ru admin credentials placeholder
    try:
        # Check if Cloud.ru credentials already exist
        result = conn.execute(
            text("SELECT id FROM provider_admin_credentials WHERE provider_type = 'cloud-ru'")
        ).fetchone()
        
        if result:
            print("✅ Cloud.ru admin credentials already exist")
        else:
            # Create inactive placeholder (admin must configure actual credentials)
            # Note: Using 'basic_auth' credential_type to match other providers' pattern
            # The actual credentials dict will contain: {'api_key': '...', 'api_secret': '...'}
            conn.execute(
                text("""
                    INSERT INTO provider_admin_credentials
                    (provider_type, credential_type, credentials, description, is_active, created_at, updated_at)
                    VALUES
                    ('cloud-ru', 'basic_auth', '{}', 'Configure via Admin UI: /admin/providers', false, NOW(), NOW())
                """)
            )
            print("✅ Created Cloud.ru admin credentials placeholder")
            print("⚠️  IMPORTANT: Configure actual credentials via Admin UI or API")
            print("   - Admin UI: /admin/providers → Cloud.ru → Credentials")
            print("   - Admin API: POST /api/admin/providers/cloud-ru/credentials")
            print("   - Required fields: api_key (Key ID), api_secret (Key Secret)")
        
    except Exception as e:
        print(f"⚠️  Error creating Cloud.ru admin credentials placeholder: {e}")
        print("   You can create it manually via Admin UI or API")


def downgrade() -> None:
    """
    Remove Cloud.ru from provider catalog and admin credentials
    """
    conn = op.get_bind()
    
    # Remove from provider_catalog
    try:
        conn.execute(
            text("DELETE FROM provider_catalog WHERE provider_type = 'cloud-ru'")
        )
        print("✅ Removed Cloud.ru from provider_catalog")
    except Exception as e:
        print(f"⚠️  Error removing Cloud.ru from provider_catalog: {e}")
    
    # Remove admin credentials
    try:
        conn.execute(
            text("DELETE FROM provider_admin_credentials WHERE provider_type = 'cloud-ru'")
        )
        print("✅ Removed Cloud.ru admin credentials")
    except Exception as e:
        print(f"⚠️  Error removing Cloud.ru admin credentials: {e}")

