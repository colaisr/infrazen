"""add tenant to resources

Revision ID: e4c1a7b2d9f0
Revises: d3e4f5a6b7c8
Create Date: 2026-02-18

Adds `tenant` column to resources for provider metadata (e.g., Cloud.ru meta.tenant_name).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4c1a7b2d9f0"
down_revision: Union[str, Sequence[str], None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("resources", sa.Column("tenant", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("resources", "tenant")

