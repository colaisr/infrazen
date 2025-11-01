"""remove_unique_constraint_board_resources

Revision ID: f7b8c9d2e1a3
Revises: e7f9b4c3a182
Create Date: 2025-10-31 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7b8c9d2e1a3'
down_revision: Union[str, Sequence[str], None] = 'e7f9b4c3a182'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove unique constraint to allow resource cloning (multiple placements of same resource).
    
    Before: Only one placement of resource_id per board_id
    After: Multiple placements allowed (clones)
    """
    # Drop the unique constraint that prevents cloning
    op.drop_constraint('unique_resource_per_board', 'board_resources', type_='unique')


def downgrade() -> None:
    """Revert to old constraint (for rollback)."""
    # Restore the unique constraint
    op.create_unique_constraint(
        'unique_resource_per_board',
        'board_resources',
        ['board_id', 'resource_id']
    )

