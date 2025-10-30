"""update_unique_constraint_for_soft_delete

Revision ID: 4ada00ea0a53
Revises: b2d7e551d226
Create Date: 2025-10-30 18:20:15.994598

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ada00ea0a53'
down_revision: Union[str, Sequence[str], None] = 'b2d7e551d226'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Update unique constraint to allow same connection_name for soft-deleted providers.
    
    The new constraint includes is_deleted, so:
    - (user_id=2, connection_name='test', is_deleted=0) is unique
    - (user_id=2, connection_name='test', is_deleted=1) can coexist
    """
    # Drop old unique constraint
    op.drop_constraint('unique_user_connection', 'cloud_providers', type_='unique')
    
    # Create new unique constraint that includes is_deleted
    # This allows reusing connection names after soft delete
    op.create_unique_constraint(
        'unique_user_active_connection',
        'cloud_providers',
        ['user_id', 'connection_name', 'is_deleted']
    )


def downgrade() -> None:
    """Revert to old constraint (for rollback)."""
    # Drop new constraint
    op.drop_constraint('unique_user_active_connection', 'cloud_providers', type_='unique')
    
    # Restore old constraint
    op.create_unique_constraint(
        'unique_user_connection',
        'cloud_providers',
        ['user_id', 'connection_name']
    )
