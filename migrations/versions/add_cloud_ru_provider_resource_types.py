"""add cloud-ru provider_resource_types

Revision ID: d3e4f5a6b7c8
Revises: c1d2e3f4a5b6
Create Date: 2026-02-16

Adds provider_resource_types for Cloud.ru so resources display correctly.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Cloud.ru provider resource types."""
    conn = op.get_bind()
    from datetime import datetime
    now = datetime.utcnow()
    types = [
        ('cloud-ru', 'server', 'Виртуальная машина', 'server', True, '["vm","server","compute"]'),
        ('cloud-ru', 'volume', 'Диск', 'disk', True, '["volume","disk","block_storage"]'),
        ('cloud-ru', 'network', 'Сеть', 'network', True, '["network","ip","floating_ip"]'),
        ('cloud-ru', 's3', 'Object Storage', 's3', True, '["s3","object_storage","bucket"]'),
        ('cloud-ru', 'database', 'База данных', 'database', True, '["database","postgresql","mysql","redis"]'),
        ('cloud-ru', 'other', 'Другое', 'box', True, '["other","unknown"]'),
    ]
    for provider_type, unified_type, display_name, icon, enabled, raw_aliases in types:
        try:
            conn.execute(
                sa.text("""
                    INSERT INTO provider_resource_types
                    (provider_type, unified_type, display_name, icon, enabled, raw_aliases, created_at, updated_at)
                    VALUES (:pt, :ut, :dn, :icon, :en, :ra, :now, :now)
                    ON DUPLICATE KEY UPDATE display_name=VALUES(display_name), icon=VALUES(icon), enabled=VALUES(enabled), raw_aliases=VALUES(raw_aliases), updated_at=VALUES(updated_at)
                """),
                {'pt': provider_type, 'ut': unified_type, 'dn': display_name, 'icon': icon, 'en': enabled, 'ra': raw_aliases, 'now': now}
            )
        except Exception:
            pass


def downgrade() -> None:
    """Remove Cloud.ru provider resource types."""
    op.execute("DELETE FROM provider_resource_types WHERE provider_type = 'cloud-ru'")
