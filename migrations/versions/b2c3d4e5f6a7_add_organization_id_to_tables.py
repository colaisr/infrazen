"""add_organization_id_to_tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add organization_id to existing tables."""
    
    # Add organization_id to cloud_providers (nullable initially, will be populated by data migration)
    op.add_column('cloud_providers', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_providers_org',
        'cloud_providers', 'organizations',
        ['organization_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('idx_providers_org', 'cloud_providers', ['organization_id'])
    
    # Add organization_id to resources (nullable initially)
    op.add_column('resources', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_resources_org',
        'resources', 'organizations',
        ['organization_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('idx_resources_org', 'resources', ['organization_id'])
    
    # Add organization_id to business_boards (nullable initially)
    op.add_column('business_boards', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_business_boards_org',
        'business_boards', 'organizations',
        ['organization_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('idx_business_boards_org', 'business_boards', ['organization_id'])
    
    # Add organization_id to chat_sessions (nullable initially)
    op.add_column('chat_sessions', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_chat_sessions_org',
        'chat_sessions', 'organizations',
        ['organization_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('idx_chat_sessions_org', 'chat_sessions', ['organization_id'])
    
    # Add organization_id to generated_reports (nullable initially)
    op.add_column('generated_reports', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_generated_reports_org',
        'generated_reports', 'organizations',
        ['organization_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('idx_generated_reports_org', 'generated_reports', ['organization_id'])
    
    # Add organization_id to optimization_recommendations (nullable initially)
    op.add_column('optimization_recommendations', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_optimization_recommendations_org',
        'optimization_recommendations', 'organizations',
        ['organization_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('idx_optimization_recommendations_org', 'optimization_recommendations', ['organization_id'])
    
    # Add organization_id to price_comparison_recommendations (nullable initially)
    op.add_column('price_comparison_recommendations', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_price_comparison_recommendations_org',
        'price_comparison_recommendations', 'organizations',
        ['organization_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('idx_price_comparison_recommendations_org', 'price_comparison_recommendations', ['organization_id'])
    
    # Add organization_id to complete_syncs (nullable initially)
    op.add_column('complete_syncs', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_complete_syncs_org',
        'complete_syncs', 'organizations',
        ['organization_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('idx_complete_syncs_org', 'complete_syncs', ['organization_id'])
    
    # Add organization_id to sync_snapshots (nullable initially, via provider)
    op.add_column('sync_snapshots', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_sync_snapshots_org',
        'sync_snapshots', 'organizations',
        ['organization_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('idx_sync_snapshots_org', 'sync_snapshots', ['organization_id'])
    
    # Add organization_id to unrecognized_resources (nullable initially)
    op.add_column('unrecognized_resources', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_unrecognized_resources_org',
        'unrecognized_resources', 'organizations',
        ['organization_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('idx_unrecognized_resources_org', 'unrecognized_resources', ['organization_id'])
    
    # Add organization_id to user_provider_preferences (nullable initially)
    # Note: This might need to be org-scoped in the future
    op.add_column('user_provider_preferences', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_user_provider_preferences_org',
        'user_provider_preferences', 'organizations',
        ['organization_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('idx_user_provider_preferences_org', 'user_provider_preferences', ['organization_id'])


def downgrade() -> None:
    """Downgrade schema - Remove organization_id from tables."""
    
    # Remove organization_id from user_provider_preferences
    op.drop_index('idx_user_provider_preferences_org', 'user_provider_preferences')
    op.drop_constraint('fk_user_provider_preferences_org', 'user_provider_preferences', type_='foreignkey')
    op.drop_column('user_provider_preferences', 'organization_id')
    
    # Remove organization_id from unrecognized_resources
    op.drop_index('idx_unrecognized_resources_org', 'unrecognized_resources')
    op.drop_constraint('fk_unrecognized_resources_org', 'unrecognized_resources', type_='foreignkey')
    op.drop_column('unrecognized_resources', 'organization_id')
    
    # Remove organization_id from sync_snapshots
    op.drop_index('idx_sync_snapshots_org', 'sync_snapshots')
    op.drop_constraint('fk_sync_snapshots_org', 'sync_snapshots', type_='foreignkey')
    op.drop_column('sync_snapshots', 'organization_id')
    
    # Remove organization_id from complete_syncs
    op.drop_index('idx_complete_syncs_org', 'complete_syncs')
    op.drop_constraint('fk_complete_syncs_org', 'complete_syncs', type_='foreignkey')
    op.drop_column('complete_syncs', 'organization_id')
    
    # Remove organization_id from price_comparison_recommendations
    op.drop_index('idx_price_comparison_recommendations_org', 'price_comparison_recommendations')
    op.drop_constraint('fk_price_comparison_recommendations_org', 'price_comparison_recommendations', type_='foreignkey')
    op.drop_column('price_comparison_recommendations', 'organization_id')
    
    # Remove organization_id from optimization_recommendations
    op.drop_index('idx_optimization_recommendations_org', 'optimization_recommendations')
    op.drop_constraint('fk_optimization_recommendations_org', 'optimization_recommendations', type_='foreignkey')
    op.drop_column('optimization_recommendations', 'organization_id')
    
    # Remove organization_id from generated_reports
    op.drop_index('idx_generated_reports_org', 'generated_reports')
    op.drop_constraint('fk_generated_reports_org', 'generated_reports', type_='foreignkey')
    op.drop_column('generated_reports', 'organization_id')
    
    # Remove organization_id from chat_sessions
    op.drop_index('idx_chat_sessions_org', 'chat_sessions')
    op.drop_constraint('fk_chat_sessions_org', 'chat_sessions', type_='foreignkey')
    op.drop_column('chat_sessions', 'organization_id')
    
    # Remove organization_id from business_boards
    op.drop_index('idx_business_boards_org', 'business_boards')
    op.drop_constraint('fk_business_boards_org', 'business_boards', type_='foreignkey')
    op.drop_column('business_boards', 'organization_id')
    
    # Remove organization_id from resources
    op.drop_index('idx_resources_org', 'resources')
    op.drop_constraint('fk_resources_org', 'resources', type_='foreignkey')
    op.drop_column('resources', 'organization_id')
    
    # Remove organization_id from cloud_providers
    op.drop_index('idx_providers_org', 'cloud_providers')
    op.drop_constraint('fk_providers_org', 'cloud_providers', type_='foreignkey')
    op.drop_column('cloud_providers', 'organization_id')

