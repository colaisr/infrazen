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
    Add Cloud.ru to provider admin credentials (optional placeholder)
    
    Note: This creates an inactive placeholder. Admin must configure
    actual credentials via admin UI or API.
    """
    conn = op.get_bind()
    
    try:
        # Check if Cloud.ru credentials already exist
        result = conn.execute(
            text("SELECT id FROM provider_admin_credentials WHERE provider_type = 'cloud-ru'")
        ).fetchone()
        
        if result:
            print("✅ Cloud.ru admin credentials already exist")
            return
        
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
    Remove Cloud.ru admin credentials
    """
    conn = op.get_bind()
    
    try:
        conn.execute(
            text("DELETE FROM provider_admin_credentials WHERE provider_type = 'cloud-ru'")
        )
        print("✅ Removed Cloud.ru admin credentials")
    except Exception as e:
        print(f"⚠️  Error removing Cloud.ru admin credentials: {e}")

