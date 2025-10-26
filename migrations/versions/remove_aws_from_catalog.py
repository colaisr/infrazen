"""remove aws from provider catalog

Revision ID: remove_aws_001
Revises: yandex_integration_001
Create Date: 2025-10-26 17:33:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'remove_aws_001'
down_revision: Union[str, Sequence[str], None] = 'yandex_integration_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove AWS from provider catalog as it's not implemented and not planned
    """
    conn = op.get_bind()
    
    try:
        # Remove AWS from provider_catalog
        conn.execute(
            sa.text("DELETE FROM provider_catalog WHERE provider_type = 'aws'")
        )
        print("✅ Removed AWS from provider_catalog")
    except Exception as e:
        print(f"⚠️  Error removing AWS from provider_catalog: {e}")
        # Continue migration even if this fails


def downgrade() -> None:
    """
    Restore AWS to provider catalog (in case rollback is needed)
    """
    conn = op.get_bind()
    
    try:
        # Check if AWS already exists
        result = conn.execute(
            sa.text("SELECT id FROM provider_catalog WHERE provider_type = 'aws'")
        ).fetchone()
        
        if not result:
            # Insert AWS back into catalog
            conn.execute(
                sa.text("""
                    INSERT INTO provider_catalog
                    (provider_type, display_name, description, is_enabled, has_pricing_api, 
                     pricing_method, website_url, documentation_url, sync_status, 
                     created_at, updated_at)
                    VALUES
                    (:provider_type, :display_name, :description, :is_enabled, :has_pricing_api,
                     :pricing_method, :website_url, :documentation_url, :sync_status,
                     NOW(), NOW())
                """),
                {
                    'provider_type': 'aws',
                    'display_name': 'Amazon Web Services',
                    'description': 'Global cloud platform with comprehensive services and Russian region support',
                    'is_enabled': False,
                    'has_pricing_api': True,
                    'pricing_method': 'api',
                    'website_url': 'https://aws.amazon.com',
                    'documentation_url': 'https://docs.aws.amazon.com',
                    'sync_status': 'never'
                }
            )
            print("✅ Restored AWS to provider_catalog")
    except Exception as e:
        print(f"⚠️  Error restoring AWS to provider_catalog: {e}")

