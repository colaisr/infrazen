"""add resource_states table

Revision ID: e7f9b4c3a182
Revises: 4ada00ea0a53
Create Date: 2025-10-31 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'e7f9b4c3a182'
down_revision = '4ada00ea0a53'
branch_labels = None
depends_on = None


def upgrade():
    # Create resource_states table
    op.create_table('resource_states',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        
        # Relationships
        sa.Column('sync_snapshot_id', sa.Integer(), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=True),  # Nullable for deleted resources
        
        # Resource identification (for deleted resources)
        sa.Column('provider_resource_id', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_name', sa.String(length=255), nullable=False),
        
        # State tracking
        sa.Column('state_action', sa.String(length=20), nullable=False),  # created, updated, unchanged, deleted
        sa.Column('previous_state', sa.Text(), nullable=True),  # JSON of previous resource state
        sa.Column('current_state', sa.Text(), nullable=True),  # JSON of current resource state
        sa.Column('changes_detected', sa.Text(), nullable=True),  # JSON of detected changes
        
        # Resource metadata
        sa.Column('service_name', sa.String(length=100), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('effective_cost', sa.Float(), nullable=True, server_default='0.0'),
        
        # Change tracking
        sa.Column('has_cost_change', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('has_status_change', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('has_config_change', sa.Boolean(), nullable=True, server_default='0'),
        
        # Primary key and foreign keys
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['sync_snapshot_id'], ['sync_snapshots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resource_id'], ['resources.id'], ondelete='SET NULL')
    )
    
    # Create indexes for better query performance
    op.create_index('ix_resource_states_sync_snapshot_id', 'resource_states', ['sync_snapshot_id'])
    op.create_index('ix_resource_states_resource_id', 'resource_states', ['resource_id'])
    op.create_index('ix_resource_states_state_action', 'resource_states', ['state_action'])
    op.create_index('ix_resource_states_provider_resource_id', 'resource_states', ['provider_resource_id'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_resource_states_provider_resource_id', table_name='resource_states')
    op.drop_index('ix_resource_states_state_action', table_name='resource_states')
    op.drop_index('ix_resource_states_resource_id', table_name='resource_states')
    op.drop_index('ix_resource_states_sync_snapshot_id', table_name='resource_states')
    
    # Drop table
    op.drop_table('resource_states')

