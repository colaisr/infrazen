"""add_external_ip_to_resources

Revision ID: 1bc4850fcaa8
Revises: ce3f3c4645c9
Create Date: 2025-10-25 08:57:50.484175

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1bc4850fcaa8'
down_revision: Union[str, Sequence[str], None] = 'ce3f3c4645c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add external_ip column to resources table
    op.add_column('resources', sa.Column('external_ip', sa.String(length=45), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove external_ip column from resources table
    op.drop_column('resources', 'external_ip')
