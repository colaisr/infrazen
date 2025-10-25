"""add yandex cloud integration

Revision ID: yandex_integration_001
Revises: d26614473f34
Create Date: 2025-10-25 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = 'yandex_integration_001'
down_revision: Union[str, Sequence[str], None] = '1bc4850fcaa8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Update Yandex Cloud provider in catalog with proper integration settings
    and add resource type mappings
    """
    conn = op.get_bind()
    
    # Update or insert Yandex Cloud provider in catalog
    try:
        # Check if yandex provider exists
        result = conn.execute(
            sa.text("SELECT id FROM provider_catalog WHERE provider_type = 'yandex'")
        ).fetchone()
        
        if result:
            # Update existing entry
            conn.execute(
                sa.text("""
                    UPDATE provider_catalog
                    SET 
                        display_name = :display_name,
                        description = :description,
                        is_enabled = :is_enabled,
                        has_pricing_api = :has_pricing_api,
                        pricing_method = :pricing_method,
                        website_url = :website_url,
                        documentation_url = :documentation_url,
                        supported_regions = :supported_regions,
                        updated_at = NOW()
                    WHERE provider_type = 'yandex'
                """),
                {
                    'display_name': 'Yandex Cloud',
                    'description': 'Russian cloud platform offering compute, storage, databases, and AI services',
                    'is_enabled': True,
                    'has_pricing_api': True,
                    'pricing_method': 'api',
                    'website_url': 'https://cloud.yandex.com',
                    'documentation_url': 'https://cloud.yandex.com/docs',
                    'supported_regions': '["ru-central1-a", "ru-central1-b", "ru-central1-c"]'
                }
            )
            print("✅ Updated existing Yandex Cloud provider in catalog")
        else:
            # Insert new entry
            conn.execute(
                sa.text("""
                    INSERT INTO provider_catalog
                    (provider_type, display_name, description, is_enabled, has_pricing_api, 
                     pricing_method, website_url, documentation_url, supported_regions, 
                     sync_status, created_at, updated_at)
                    VALUES
                    (:provider_type, :display_name, :description, :is_enabled, :has_pricing_api,
                     :pricing_method, :website_url, :documentation_url, :supported_regions,
                     :sync_status, NOW(), NOW())
                """),
                {
                    'provider_type': 'yandex',
                    'display_name': 'Yandex Cloud',
                    'description': 'Russian cloud platform offering compute, storage, databases, and AI services',
                    'is_enabled': True,
                    'has_pricing_api': True,
                    'pricing_method': 'api',
                    'website_url': 'https://cloud.yandex.com',
                    'documentation_url': 'https://cloud.yandex.com/docs',
                    'supported_regions': '["ru-central1-a", "ru-central1-b", "ru-central1-c"]',
                    'sync_status': 'never'
                }
            )
            print("✅ Inserted new Yandex Cloud provider in catalog")
    except Exception as e:
        print(f"⚠️  Provider catalog update: {e}")
        # Continue with migration even if this fails
    
    # Add Yandex Cloud resource type mappings
    try:
        yandex_resource_types = [
            ('yandex', 'server', 'Виртуальная машина', 'server', True, '["instance","vm","compute"]'),
            ('yandex', 'volume', 'Диск', 'disk', True, '["disk","volume","block_storage"]'),
            ('yandex', 'network', 'Сеть', 'network', True, '["network","vpc"]'),
            ('yandex', 'subnet', 'Подсеть', 'subnet', True, '["subnet","subnetwork"]'),
            ('yandex', 'load_balancer', 'Балансировщик нагрузки', 'load_balancer', True, '["load_balancer","lb"]'),
            ('yandex', 'database', 'База данных', 'database', True, '["database","db","managed_database"]'),
            ('yandex', 'kubernetes_cluster', 'Кластер Kubernetes', 'kubernetes', True, '["kubernetes","k8s","mks"]'),
            ('yandex', 's3_bucket', 'Object Storage', 's3', True, '["bucket","s3","object_storage"]'),
        ]
        
        for provider_type, unified_type, display_name, icon, enabled, raw_aliases in yandex_resource_types:
            # Check if this mapping already exists
            existing = conn.execute(
                sa.text("""
                    SELECT id FROM provider_resource_types 
                    WHERE provider_type = :provider_type AND unified_type = :unified_type
                """),
                {'provider_type': provider_type, 'unified_type': unified_type}
            ).fetchone()
            
            if not existing:
                conn.execute(
                    sa.text("""
                        INSERT INTO provider_resource_types
                        (provider_type, unified_type, display_name, icon, enabled, raw_aliases, created_at, updated_at)
                        VALUES (:provider_type, :unified_type, :display_name, :icon, :enabled, :raw_aliases, NOW(), NOW())
                    """),
                    {
                        'provider_type': provider_type,
                        'unified_type': unified_type,
                        'display_name': display_name,
                        'icon': icon,
                        'enabled': enabled,
                        'raw_aliases': raw_aliases,
                    }
                )
        
        print(f"✅ Added {len(yandex_resource_types)} Yandex Cloud resource type mappings")
    except Exception as e:
        print(f"⚠️  Resource types seeding: {e}")
        # Continue even if this fails


def downgrade() -> None:
    """
    Revert Yandex Cloud integration changes
    """
    conn = op.get_bind()
    
    # Note: We don't delete the provider_catalog entry, just disable it
    try:
        conn.execute(
            sa.text("""
                UPDATE provider_catalog
                SET is_enabled = FALSE, updated_at = NOW()
                WHERE provider_type = 'yandex'
            """)
        )
        print("✅ Disabled Yandex Cloud provider in catalog")
    except Exception as e:
        print(f"⚠️  Provider catalog downgrade: {e}")
    
    # Remove Yandex resource type mappings
    try:
        conn.execute(
            sa.text("DELETE FROM provider_resource_types WHERE provider_type = 'yandex'")
        )
        print("✅ Removed Yandex Cloud resource type mappings")
    except Exception as e:
        print(f"⚠️  Resource types cleanup: {e}")

