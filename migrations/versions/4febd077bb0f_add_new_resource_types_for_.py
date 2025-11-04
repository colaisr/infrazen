"""add_new_resource_types_for_recommendations

Revision ID: 4febd077bb0f
Revises: 3f6721afaf53
Create Date: 2025-11-04 03:36:32.723983

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4febd077bb0f'
down_revision: Union[str, Sequence[str], None] = '3f6721afaf53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new resource types for recommendation rules."""
    from datetime import datetime
    
    # Resource types to add for each provider
    resource_types = [
        # Snapshots (Yandex has them)
        ('yandex', 'snapshot', 'Snapshot', 'fa-camera'),
        
        # Reserved IPs (Yandex has them)
        ('yandex', 'reserved_ip', 'Reserved IP', 'fa-network-wired'),
        
        # Managed databases - Yandex
        ('yandex', 'postgresql-cluster', 'PostgreSQL Cluster', 'fa-database'),
        ('yandex', 'mysql-cluster', 'MySQL Cluster', 'fa-database'),
        ('yandex', 'kafka-cluster', 'Kafka Cluster', 'fa-stream'),
        ('yandex', 'redis-cluster', 'Redis Cluster', 'fa-database'),
        
        # Managed databases - Selectel
        ('selectel', 'postgresql-cluster', 'PostgreSQL Cluster', 'fa-database'),
        ('selectel', 'mysql-cluster', 'MySQL Cluster', 'fa-database'),
        ('selectel', 'kafka-cluster', 'Kafka Cluster', 'fa-stream'),
        ('selectel', 'redis-cluster', 'Redis Cluster', 'fa-database'),
        
        # Managed databases - Beget
        ('beget', 'postgresql-cluster', 'PostgreSQL Cluster', 'fa-database'),
        ('beget', 'mysql-cluster', 'MySQL Cluster', 'fa-database'),
    ]
    
    # Insert new resource types
    provider_resource_types = sa.table(
        'provider_resource_types',
        sa.column('provider_type', sa.String),
        sa.column('unified_type', sa.String),
        sa.column('display_name', sa.String),
        sa.column('icon', sa.String),
        sa.column('enabled', sa.Boolean),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )
    
    now = datetime.utcnow()
    
    # Use raw SQL with INSERT IGNORE to skip duplicates
    for provider, unified_type, display_name, icon in resource_types:
        op.execute(
            f"""
            INSERT IGNORE INTO provider_resource_types 
            (provider_type, unified_type, display_name, icon, enabled, created_at, updated_at)
            VALUES ('{provider}', '{unified_type}', '{display_name}', '{icon}', 1, '{now}', '{now}')
            """
        )


def downgrade() -> None:
    """Remove new resource types."""
    # Define the types to remove
    types_to_remove = [
        ('yandex', 'snapshot'),
        ('yandex', 'reserved_ip'),
        ('yandex', 'postgresql-cluster'),
        ('yandex', 'mysql-cluster'),
        ('yandex', 'kafka-cluster'),
        ('yandex', 'redis-cluster'),
        ('selectel', 'postgresql-cluster'),
        ('selectel', 'mysql-cluster'),
        ('selectel', 'kafka-cluster'),
        ('selectel', 'redis-cluster'),
        ('beget', 'postgresql-cluster'),
        ('beget', 'mysql-cluster'),
    ]
    
    # Delete resource types
    for provider, unified_type in types_to_remove:
        op.execute(
            f"DELETE FROM provider_resource_types WHERE provider_type='{provider}' AND unified_type='{unified_type}'"
        )
