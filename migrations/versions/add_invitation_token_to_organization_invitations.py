"""add_invitation_token_to_organization_invitations

Revision ID: 8a9b0c1d2e3f
Revises: 2f7d8d0bf9e9
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a9b0c1d2e3f'
down_revision: Union[str, Sequence[str], None] = '2f7d8d0bf9e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add invitation_token field to organization_invitations table for unregistered user invitations."""
    
    # Add invitation_token column
    op.add_column('organization_invitations', sa.Column('invitation_token', sa.String(255), nullable=True))
    
    # Create unique index on invitation_token
    op.create_index('ix_organization_invitations_invitation_token', 'organization_invitations', ['invitation_token'], unique=True)


def downgrade() -> None:
    """Remove invitation_token field from organization_invitations table."""
    op.drop_index('ix_organization_invitations_invitation_token', table_name='organization_invitations')
    op.drop_column('organization_invitations', 'invitation_token')

