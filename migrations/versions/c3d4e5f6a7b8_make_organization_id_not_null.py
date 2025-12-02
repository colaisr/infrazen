"""make_organization_id_not_null

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

NOTE: This migration should be run AFTER running scripts/migrate_to_organizations.py
to populate organization_id for all existing data.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Make organization_id NOT NULL after data migration."""
    
    # Make organization_id NOT NULL for all tables
    # This assumes all data has been migrated via migrate_to_organizations.py
    
    # cloud_providers
    op.alter_column('cloud_providers', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    # resources
    op.alter_column('resources', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    # business_boards
    op.alter_column('business_boards', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    # chat_sessions
    op.alter_column('chat_sessions', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    # generated_reports
    op.alter_column('generated_reports', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    # optimization_recommendations
    op.alter_column('optimization_recommendations', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    # price_comparison_recommendations
    op.alter_column('price_comparison_recommendations', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    # complete_syncs
    op.alter_column('complete_syncs', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    # sync_snapshots
    op.alter_column('sync_snapshots', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    # unrecognized_resources
    op.alter_column('unrecognized_resources', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    # user_provider_preferences
    op.alter_column('user_provider_preferences', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)


def downgrade() -> None:
    """Downgrade schema - Make organization_id nullable again."""
    
    # user_provider_preferences
    op.alter_column('user_provider_preferences', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=True)
    
    # unrecognized_resources
    op.alter_column('unrecognized_resources', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=True)
    
    # sync_snapshots
    op.alter_column('sync_snapshots', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=True)
    
    # complete_syncs
    op.alter_column('complete_syncs', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=True)
    
    # price_comparison_recommendations
    op.alter_column('price_comparison_recommendations', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=True)
    
    # optimization_recommendations
    op.alter_column('optimization_recommendations', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=True)
    
    # generated_reports
    op.alter_column('generated_reports', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=True)
    
    # chat_sessions
    op.alter_column('chat_sessions', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=True)
    
    # business_boards
    op.alter_column('business_boards', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=True)
    
    # resources
    op.alter_column('resources', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=True)
    
    # cloud_providers
    op.alter_column('cloud_providers', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=True)

