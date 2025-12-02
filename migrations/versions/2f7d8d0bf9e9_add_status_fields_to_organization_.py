"""add_status_fields_to_organization_invitations

Revision ID: 2f7d8d0bf9e9
Revises: 705ab166f417
Create Date: 2025-12-02 08:14:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f7d8d0bf9e9'
down_revision: Union[str, Sequence[str], None] = '705ab166f417'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add status tracking fields to organization_invitations table."""
    
    # Add status fields
    op.add_column('organization_invitations', sa.Column('status', sa.String(20), nullable=False, server_default='sent'))
    op.add_column('organization_invitations', sa.Column('accepted_at', sa.DateTime(), nullable=True))
    op.add_column('organization_invitations', sa.Column('revoked_at', sa.DateTime(), nullable=True))
    
    # Update existing invitations to 'accepted' if they have a corresponding active member
    op.execute("""
        UPDATE organization_invitations oi
        INNER JOIN organization_members om ON oi.organization_id = om.organization_id
        INNER JOIN users u ON om.user_id = u.id AND u.email = oi.email
        SET oi.status = 'accepted', oi.accepted_at = om.joined_at
        WHERE om.is_active = 1
    """)


def downgrade() -> None:
    """Remove status tracking fields from organization_invitations table."""
    op.drop_column('organization_invitations', 'revoked_at')
    op.drop_column('organization_invitations', 'accepted_at')
    op.drop_column('organization_invitations', 'status')
