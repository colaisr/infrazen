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
    # Need to drop foreign keys before altering columns, then recreate them
    
    # Drop foreign keys first
    foreign_keys_to_drop = [
        ('cloud_providers', 'fk_providers_org'),
        ('resources', 'fk_resources_org'),
        ('business_boards', 'fk_business_boards_org'),
        ('chat_sessions', 'fk_chat_sessions_org'),
        ('generated_reports', 'fk_generated_reports_org'),
        ('optimization_recommendations', 'fk_optimization_recommendations_org'),
        ('price_comparison_recommendations', 'fk_price_comparison_recommendations_org'),
        ('complete_syncs', 'fk_complete_syncs_org'),
        ('sync_snapshots', 'fk_sync_snapshots_org'),
        ('unrecognized_resources', 'fk_unrecognized_resources_org'),
        ('user_provider_preferences', 'fk_user_provider_preferences_org'),
    ]
    
    for table_name, fk_name in foreign_keys_to_drop:
        try:
            op.drop_constraint(fk_name, table_name, type_='foreignkey')
        except Exception:
            # Constraint might not exist, continue
            pass
    
    # Alter columns to NOT NULL
    op.alter_column('cloud_providers', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    op.alter_column('resources', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    op.alter_column('business_boards', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    op.alter_column('chat_sessions', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    op.alter_column('generated_reports', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    op.alter_column('optimization_recommendations', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    op.alter_column('price_comparison_recommendations', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    op.alter_column('complete_syncs', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    op.alter_column('sync_snapshots', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    op.alter_column('unrecognized_resources', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    op.alter_column('user_provider_preferences', 'organization_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    # Recreate foreign keys
    op.create_foreign_key('fk_providers_org', 'cloud_providers', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_resources_org', 'resources', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_business_boards_org', 'business_boards', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_chat_sessions_org', 'chat_sessions', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_generated_reports_org', 'generated_reports', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_optimization_recommendations_org', 'optimization_recommendations', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_price_comparison_recommendations_org', 'price_comparison_recommendations', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_complete_syncs_org', 'complete_syncs', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_sync_snapshots_org', 'sync_snapshots', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_unrecognized_resources_org', 'unrecognized_resources', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_user_provider_preferences_org', 'user_provider_preferences', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')


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

