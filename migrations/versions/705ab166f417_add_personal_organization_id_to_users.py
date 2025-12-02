"""add_personal_organization_id_to_users

Revision ID: 705ab166f417
Revises: c3d4e5f6a7b8
Create Date: 2025-12-02 08:10:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '705ab166f417'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add personal_organization_id to users table and populate it."""
    
    # Add personal_organization_id column (nullable initially)
    op.add_column('users', sa.Column('personal_organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_users_personal_org',
        'users', 'organizations',
        ['personal_organization_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('idx_users_personal_org', 'users', ['personal_organization_id'])
    
    # Populate personal_organization_id for existing users
    # Set it to their owner organization (the one they own)
    op.execute("""
        UPDATE users u
        INNER JOIN organization_members om ON u.id = om.user_id
        INNER JOIN organizations o ON om.organization_id = o.id
        SET u.personal_organization_id = o.id
        WHERE om.role = 'owner' AND om.is_active = 1
        AND u.personal_organization_id IS NULL
    """)


def downgrade() -> None:
    """Remove personal_organization_id from users table."""
    op.drop_index('idx_users_personal_org', 'users')
    op.drop_constraint('fk_users_personal_org', 'users', type_='foreignkey')
    op.drop_column('users', 'personal_organization_id')
