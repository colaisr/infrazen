"""add_organizations_tables

Revision ID: a1b2c3d4e5f6
Revises: 4ada00ea0a53
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '8139f6939d1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add organizations tables."""
    
    # Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for organizations name
    op.create_index('idx_organizations_name', 'organizations', ['name'])
    
    # Create organization_members table
    op.create_table(
        'organization_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='viewer'),
        sa.Column('invited_by_user_id', sa.Integer(), nullable=True),
        sa.Column('invited_at', sa.DateTime(), nullable=True),
        sa.Column('joined_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'user_id', name='unique_org_user')
    )
    
    # Create indexes for organization_members
    op.create_index('idx_org_members_user', 'organization_members', ['user_id'])
    op.create_index('idx_org_members_org', 'organization_members', ['organization_id'])
    op.create_index('idx_org_members_role', 'organization_members', ['role'])
    
    # Create organization_invitations table (for audit trail)
    op.create_table(
        'organization_invitations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='viewer'),
        sa.Column('invited_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for organization_invitations
    op.create_index('idx_invitations_email', 'organization_invitations', ['email'])
    op.create_index('idx_invitations_org', 'organization_invitations', ['organization_id'])
    
    # Add organization preference fields to users table
    op.add_column('users', sa.Column('default_organization_id', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('last_active_organization_id', sa.Integer(), nullable=True))
    
    # Add foreign keys for user organization preferences
    op.create_foreign_key(
        'fk_users_default_org',
        'users', 'organizations',
        ['default_organization_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_users_last_active_org',
        'users', 'organizations',
        ['last_active_organization_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema - Remove organizations tables."""
    
    # Remove foreign keys from users table
    op.drop_constraint('fk_users_last_active_org', 'users', type_='foreignkey')
    op.drop_constraint('fk_users_default_org', 'users', type_='foreignkey')
    
    # Remove columns from users table
    op.drop_column('users', 'last_active_organization_id')
    op.drop_column('users', 'default_organization_id')
    
    # Drop indexes for organization_invitations
    op.drop_index('idx_invitations_org', 'organization_invitations')
    op.drop_index('idx_invitations_email', 'organization_invitations')
    
    # Drop organization_invitations table
    op.drop_table('organization_invitations')
    
    # Drop indexes for organization_members
    op.drop_index('idx_org_members_role', 'organization_members')
    op.drop_index('idx_org_members_org', 'organization_members')
    op.drop_index('idx_org_members_user', 'organization_members')
    
    # Drop organization_members table
    op.drop_table('organization_members')
    
    # Drop index for organizations
    op.drop_index('idx_organizations_name', 'organizations')
    
    # Drop organizations table
    op.drop_table('organizations')

