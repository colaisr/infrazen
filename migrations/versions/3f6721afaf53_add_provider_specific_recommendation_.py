"""add_provider_specific_recommendation_tracking

Revision ID: 3f6721afaf53
Revises: fa7962b5fce6
Create Date: 2025-11-03 16:02:18.438568

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f6721afaf53'
down_revision: Union[str, Sequence[str], None] = 'fa7962b5fce6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add provider-specific tracking columns for recommendations."""
    # Add columns for tracking which provider is being recommended
    op.add_column('optimization_recommendations',
        sa.Column('target_provider', sa.String(50), nullable=True)
    )
    op.add_column('optimization_recommendations',
        sa.Column('target_sku', sa.String(200), nullable=True)
    )
    op.add_column('optimization_recommendations',
        sa.Column('target_region', sa.String(100), nullable=True)
    )
    
    # Add columns for verification tracking (auto-cleanup of obsolete recommendations)
    op.add_column('optimization_recommendations',
        sa.Column('last_verified_at', sa.DateTime, nullable=True)
    )
    op.add_column('optimization_recommendations',
        sa.Column('verification_fail_count', sa.Integer, nullable=True, server_default='0')
    )
    
    # Create index for provider-specific deduplication
    op.create_index(
        'idx_dedup_provider_specific',
        'optimization_recommendations',
        ['source', 'resource_id', 'recommendation_type', 'target_provider', 'target_sku'],
        unique=False
    )
    
    # Create index for verification tracking queries
    op.create_index(
        'idx_verification_tracking',
        'optimization_recommendations',
        ['last_verified_at', 'status'],
        unique=False
    )


def downgrade() -> None:
    """Remove provider-specific tracking columns."""
    op.drop_index('idx_verification_tracking', table_name='optimization_recommendations')
    op.drop_index('idx_dedup_provider_specific', table_name='optimization_recommendations')
    op.drop_column('optimization_recommendations', 'verification_fail_count')
    op.drop_column('optimization_recommendations', 'last_verified_at')
    op.drop_column('optimization_recommendations', 'target_region')
    op.drop_column('optimization_recommendations', 'target_sku')
    op.drop_column('optimization_recommendations', 'target_provider')
