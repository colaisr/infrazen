#!/usr/bin/env python3
"""
Seed demo user with mock providers, resources, and cost data
"""
import os
import sys
from datetime import datetime, timedelta
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import db
from app.core.models.user import User
from app.core.models.provider import CloudProvider
from app.core.models.resource import Resource
from app.core.models.sync import SyncSnapshot, ResourceState
from app.core.models.complete_sync import CompleteSync, ProviderSyncReference
from app.core.models.recommendations import OptimizationRecommendation
from app.core.models.tags import ResourceTag
from app.core.models.metrics import ResourceMetric, ResourceUsageSummary
from app.core.models.logs import ResourceLog, ResourceComponent
from app.core.models.costs import CostAllocation, CostTrend
import random

def seed_demo_user():
    """
    Create demo user with realistic mock data
    This user is used for demonstrations and testing
    """
    print("🔄 Checking for existing demo user...")
    
    # Check if demo user already exists
    demo_user = User.query.filter_by(email='demo@infrazen.com').first()
    
    if demo_user:
        print("⚠️  Demo user already exists. Deleting existing demo data...")
        # Collect provider, resource, and snapshot ids
        providers = CloudProvider.query.filter_by(user_id=demo_user.id).all()
        provider_ids = [p.id for p in providers]
        if provider_ids:
            # Delete complete syncs and their references first
            complete_sync_ids = [cs.id for cs in CompleteSync.query.filter_by(user_id=demo_user.id).all()]
            if complete_sync_ids:
                ProviderSyncReference.query.filter(ProviderSyncReference.complete_sync_id.in_(complete_sync_ids)).delete(synchronize_session=False)
                db.session.commit()
                CompleteSync.query.filter(CompleteSync.id.in_(complete_sync_ids)).delete(synchronize_session=False)
                db.session.commit()
                print("  ✓ Deleted complete syncs and references")
            
            # Delete dependent snapshots and states
            snapshot_ids = [s.id for s in SyncSnapshot.query.filter(SyncSnapshot.provider_id.in_(provider_ids)).all()]
            if snapshot_ids:
                ResourceState.query.filter(ResourceState.sync_snapshot_id.in_(snapshot_ids)).delete(synchronize_session=False)
                db.session.commit()
                SyncSnapshot.query.filter(SyncSnapshot.id.in_(snapshot_ids)).delete(synchronize_session=False)
                db.session.commit()
                print("  ✓ Deleted sync snapshots and resource states")
            # Delete recommendations for these providers/resources
            res_ids = [rid for (rid,) in db.session.query(Resource.id).filter(Resource.provider_id.in_(provider_ids)).all()]
            if res_ids:
                # Child tables referencing resources (no ON DELETE CASCADE in MySQL schema)
                ResourceTag.query.filter(ResourceTag.resource_id.in_(res_ids)).delete(synchronize_session=False)
                ResourceMetric.query.filter(ResourceMetric.resource_id.in_(res_ids)).delete(synchronize_session=False)
                ResourceUsageSummary.query.filter(ResourceUsageSummary.resource_id.in_(res_ids)).delete(synchronize_session=False)
                ResourceLog.query.filter(ResourceLog.resource_id.in_(res_ids)).delete(synchronize_session=False)
                ResourceComponent.query.filter(ResourceComponent.resource_id.in_(res_ids)).delete(synchronize_session=False)
                CostAllocation.query.filter(CostAllocation.resource_id.in_(res_ids)).delete(synchronize_session=False)
                CostTrend.query.filter(CostTrend.resource_id.in_(res_ids)).delete(synchronize_session=False)
                db.session.commit()
                OptimizationRecommendation.query.filter(OptimizationRecommendation.resource_id.in_(res_ids)).delete(synchronize_session=False)
                db.session.commit()
            OptimizationRecommendation.query.filter(OptimizationRecommendation.provider_id.in_(provider_ids)).delete(synchronize_session=False)
            db.session.commit()
            # Delete resources (safe after child tables)
            Resource.query.filter(Resource.provider_id.in_(provider_ids)).delete(synchronize_session=False)
            db.session.commit()
            # Delete providers
            CloudProvider.query.filter(CloudProvider.id.in_(provider_ids)).delete(synchronize_session=False)
            db.session.commit()
        # Delete user last
        db.session.delete(demo_user)
        db.session.commit()
        print("✅ Existing demo user deleted")
    
    print("🔄 Creating demo user...")
    
    # Create demo user
    demo_user = User(
        email='demo@infrazen.com',
        username='demo',
        first_name='Demo',
        last_name='User',
        role='demouser',
        is_active=True,
        is_verified=True,
        timezone='Europe/Moscow',
        currency='RUB',
        language='ru',
        created_by_admin=True,
        admin_notes='Demo user for testing and demonstrations. Read-only access. Do not delete.'
    )
    
    # Set a password for demo user (same as username for simplicity)
    demo_user.set_password('demo')
    
    db.session.add(demo_user)
    db.session.commit()
    
    print(f"✅ Demo user created (ID: {demo_user.id})")
    
    # Create Beget provider
    print("🔄 Creating provider connections (4 total)...")
    # Beget Prod
    beget_prod = CloudProvider(
        user_id=demo_user.id,
        provider_type='beget',
        connection_name='Beget Prod',
        account_id='demo_beget_prod',
        api_endpoint=None,
        credentials=json.dumps({'login': 'demo_beget_prod', 'password': '***DEMO***'}),
        is_active=True,
        last_sync=datetime.now() - timedelta(hours=2),
        sync_status='success',
        auto_sync=True,
        sync_interval='daily'
    )
    db.session.add(beget_prod)
    db.session.commit()
    
    # Beget Dev
    beget_dev = CloudProvider(
        user_id=demo_user.id,
        provider_type='beget',
        connection_name='Beget Dev',
        account_id='demo_beget_dev',
        api_endpoint=None,
        credentials=json.dumps({'login': 'demo_beget_dev', 'password': '***DEMO***'}),
        is_active=True,
        last_sync=datetime.now() - timedelta(hours=2),
        sync_status='success',
        auto_sync=True,
        sync_interval='daily'
    )
    db.session.add(beget_dev)
    db.session.commit()

    # Selectel BU-A (prod)
    selectel_bu_a = CloudProvider(
        user_id=demo_user.id,
        provider_type='selectel',
        connection_name='Selectel BU-A',
        account_id='demo_selectel_bu_a',
        api_endpoint=None,
        credentials=json.dumps({'account_id': 'demo_selectel_bu_a', 'api_token': '***DEMO***'}),
        is_active=True,
        last_sync=datetime.now() - timedelta(hours=1),
        sync_status='success',
        auto_sync=True,
        sync_interval='daily'
    )
    db.session.add(selectel_bu_a)
    db.session.commit()

    # Selectel BU-B (dev/stage)
    selectel_bu_b = CloudProvider(
        user_id=demo_user.id,
        provider_type='selectel',
        connection_name='Selectel BU-B',
        account_id='demo_selectel_bu_b',
        api_endpoint=None,
        credentials=json.dumps({'account_id': 'demo_selectel_bu_b', 'api_token': '***DEMO***'}),
        is_active=True,
        last_sync=datetime.now() - timedelta(minutes=45),
        sync_status='success',
        auto_sync=True,
        sync_interval='daily'
    )
    db.session.add(selectel_bu_b)
    db.session.commit()
    
    print(f"✅ Providers created (IDs: BegetProd={beget_prod.id}, BegetDev={beget_dev.id}, SelA={selectel_bu_a.id}, SelB={selectel_bu_b.id})")
    
    # Note: Sync snapshots will be created by seed_historical_complete_syncs()
    # to generate 90 days of historical data with realistic variations
    
    # Helper to add resources
    def add_resources(resource_defs):
        created = []
        for r in resource_defs:
            res = Resource(**r)
            # Set daily cost baseline from effective monthly cost for UI consistency
            try:
                if res.effective_cost and res.effective_cost > 0:
                    res.set_daily_cost_baseline(res.effective_cost, 'monthly', 'recurring')
            except Exception:
                pass
            db.session.add(res)
            created.append(res)
        db.session.commit()
        return created

    print("🔄 Creating resources for all connections...")

    # Selectel BU-A resources (~166,600 ₽)
    add_resources([
        {
            'provider_id': selectel_bu_a.id,
            'resource_id': 'sel-a-srv-api-backend-prod-01',
            'resource_type': 'server', 'resource_name': 'api-backend-prod-01', 'region': 'ru-1', 'status': 'active',
            'service_name': 'Cloud Servers', 'effective_cost': 28500.0, 'currency': 'RUB', 'billing_period': 'monthly',
            'provider_config': json.dumps({'cpu': '8 vCPU', 'memory': '32 GB', 'storage': '200 GB NVMe', 'os': 'Debian 11'})
        },
        {
            'provider_id': selectel_bu_a.id,
            'resource_id': 'sel-a-srv-db-postgres-prod-01',
            'resource_type': 'server', 'resource_name': 'db-postgres-prod-01', 'region': 'ru-2', 'status': 'active',
            'service_name': 'Cloud Servers', 'effective_cost': 22950.0, 'currency': 'RUB', 'billing_period': 'monthly',
            'provider_config': json.dumps({'cpu': '8 vCPU', 'memory': '64 GB', 'storage': '500 GB SSD', 'os': 'Ubuntu 22.04'})
        },
        {
            'provider_id': selectel_bu_a.id,
            'resource_id': 'sel-a-vol-postgres-data-01',
            'resource_type': 'volume', 'resource_name': 'postgres-data-volume', 'region': 'ru-2', 'status': 'active',
            'service_name': 'Block Storage', 'effective_cost': 4000.0, 'currency': 'RUB', 'billing_period': 'monthly',
            'provider_config': json.dumps({'size': '500 GB', 'type': 'SSD'})
        },
        {'provider_id': selectel_bu_a.id, 'resource_id': 'sel-a-k8s-worker-01', 'resource_type': 'server', 'resource_name': 'k8s-worker-01', 'region': 'ru-1', 'status': 'active', 'service_name': 'Cloud Servers', 'effective_cost': 18000.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '8 vCPU', 'memory': '32 GB'})},
        {'provider_id': selectel_bu_a.id, 'resource_id': 'sel-a-k8s-worker-02', 'resource_type': 'server', 'resource_name': 'k8s-worker-02', 'region': 'ru-1', 'status': 'active', 'service_name': 'Cloud Servers', 'effective_cost': 18000.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '8 vCPU', 'memory': '32 GB'})},
        {'provider_id': selectel_bu_a.id, 'resource_id': 'sel-a-k8s-master-01', 'resource_type': 'server', 'resource_name': 'k8s-master-01', 'region': 'ru-1', 'status': 'active', 'service_name': 'Cloud Servers', 'effective_cost': 12000.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '4 vCPU', 'memory': '16 GB'})},
        {'provider_id': selectel_bu_a.id, 'resource_id': 'sel-a-lb-prod-01', 'resource_type': 'load_balancer', 'resource_name': 'lb-prod-01', 'region': 'ru-1', 'status': 'active', 'service_name': 'Load Balancer', 'effective_cost': 8000.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'plan': 'XL'})},
        {'provider_id': selectel_bu_a.id, 'resource_id': 'sel-a-obj-s3-cdn-static', 'resource_type': 'file_storage', 'resource_name': 's3-cdn-static', 'region': 'ru-1', 'status': 'active', 'service_name': 'S3 Object Storage', 'effective_cost': 2000.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'size': '250 GB'})},
        {'provider_id': selectel_bu_a.id, 'resource_id': 'sel-a-eip-01', 'resource_type': 'ip', 'resource_name': 'eip-01', 'region': 'ru-1', 'status': 'active', 'service_name': 'Networking', 'effective_cost': 150.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'type': 'public'})},
        {'provider_id': selectel_bu_a.id, 'resource_id': 'sel-a-analytics-etl-01', 'resource_type': 'server', 'resource_name': 'analytics-etl-01', 'region': 'ru-1', 'status': 'active', 'service_name': 'Cloud Servers', 'effective_cost': 20000.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '8 vCPU', 'memory': '32 GB'})},
        {'provider_id': selectel_bu_a.id, 'resource_id': 'sel-a-cache-redis', 'resource_type': 'server', 'resource_name': 'app-cache-redis', 'region': 'ru-1', 'status': 'active', 'service_name': 'Cloud Servers', 'effective_cost': 6500.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '2 vCPU', 'memory': '8 GB'})},
        {'provider_id': selectel_bu_a.id, 'resource_id': 'sel-a-archive-cold-storage', 'resource_type': 'file_storage', 'resource_name': 'archive-cold-storage', 'region': 'ru-1', 'status': 'active', 'service_name': 'Object Storage', 'effective_cost': 15000.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'tier': 'cold', 'size': '10 TB'})},
        {'provider_id': selectel_bu_a.id, 'resource_id': 'sel-a-snapshot-storage', 'resource_type': 'snapshots', 'resource_name': 'snapshot-storage', 'region': 'ru-1', 'status': 'active', 'service_name': 'Snapshots', 'effective_cost': 11500.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'count': 12})},
    ])

    # Selectel BU-B resources (~104,300 ₽)
    add_resources([
        {'provider_id': selectel_bu_b.id, 'resource_id': 'sel-b-web-frontend-01', 'resource_type': 'server', 'resource_name': 'web-frontend-01', 'region': 'ru-1', 'status': 'active', 'service_name': 'Cloud Servers', 'effective_cost': 18500.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '4 vCPU', 'memory': '16 GB'})},
        {'provider_id': selectel_bu_b.id, 'resource_id': 'sel-b-web-frontend-02', 'resource_type': 'server', 'resource_name': 'web-frontend-02', 'region': 'ru-1', 'status': 'active', 'service_name': 'Cloud Servers', 'effective_cost': 18500.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '4 vCPU', 'memory': '16 GB'})},
        {'provider_id': selectel_bu_b.id, 'resource_id': 'sel-b-db-mysql-staging', 'resource_type': 'server', 'resource_name': 'db-mysql-staging', 'region': 'ru-1', 'status': 'active', 'service_name': 'Cloud Servers', 'effective_cost': 12000.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '4 vCPU', 'memory': '16 GB'})},
        {'provider_id': selectel_bu_b.id, 'resource_id': 'sel-b-dev-k8s-node-01', 'resource_type': 'server', 'resource_name': 'dev-k8s-node-01', 'region': 'ru-1', 'status': 'active', 'service_name': 'Cloud Servers', 'effective_cost': 9500.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '4 vCPU', 'memory': '16 GB'})},
        {'provider_id': selectel_bu_b.id, 'resource_id': 'sel-b-dev-k8s-node-02', 'resource_type': 'server', 'resource_name': 'dev-k8s-node-02', 'region': 'ru-1', 'status': 'active', 'service_name': 'Cloud Servers', 'effective_cost': 9500.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '4 vCPU', 'memory': '16 GB'})},
        {'provider_id': selectel_bu_b.id, 'resource_id': 'sel-b-s3-media-bucket', 'resource_type': 'file_storage', 'resource_name': 's3-media-bucket', 'region': 'ru-1', 'status': 'active', 'service_name': 'Object Storage', 'effective_cost': 5500.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'size': '1.2 TB'})},
        {'provider_id': selectel_bu_b.id, 'resource_id': 'sel-b-test-runner-01', 'resource_type': 'server', 'resource_name': 'test-runner-01', 'region': 'ru-1', 'status': 'active', 'service_name': 'Cloud Servers', 'effective_cost': 6500.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '4 vCPU', 'memory': '8 GB'})},
        {'provider_id': selectel_bu_b.id, 'resource_id': 'sel-b-ci-runner-spot', 'resource_type': 'server', 'resource_name': 'ci-runner-spot', 'region': 'ru-1', 'status': 'active', 'service_name': 'Cloud Servers', 'effective_cost': 8500.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '8 vCPU', 'memory': '8 GB'})},
        {'provider_id': selectel_bu_b.id, 'resource_id': 'sel-b-lb-dev', 'resource_type': 'load_balancer', 'resource_name': 'load-balancer-dev', 'region': 'ru-1', 'status': 'active', 'service_name': 'Load Balancer', 'effective_cost': 4000.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'plan': 'S'})},
        {'provider_id': selectel_bu_b.id, 'resource_id': 'sel-b-vpn-gw', 'resource_type': 'network', 'resource_name': 'vpn-gateway', 'region': 'ru-1', 'status': 'active', 'service_name': 'VPN', 'effective_cost': 3500.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'type': 'site2site'})},
        {'provider_id': selectel_bu_b.id, 'resource_id': 'sel-b-pg-backup-volume', 'resource_type': 'volume', 'resource_name': 'pg-backup-volume', 'region': 'ru-1', 'status': 'active', 'service_name': 'Block Storage', 'effective_cost': 6500.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'size': '1 TB', 'attached_to': None})},
        {'provider_id': selectel_bu_b.id, 'resource_id': 'sel-b-egress-and-ips', 'resource_type': 'network', 'resource_name': 'misc-egress-and-ips', 'region': 'ru-1', 'status': 'active', 'service_name': 'Networking', 'effective_cost': 1800.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'egress_tb': 0.5})},
    ])

    # Beget Prod resources (~104,250 ₽)
    add_resources([
        {'provider_id': beget_prod.id, 'resource_id': 'beget-prod-vps-app-01', 'resource_type': 'server', 'resource_name': 'vps-app-01', 'region': 'ru-msk', 'status': 'active', 'service_name': 'VPS', 'effective_cost': 12500.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '4 vCPU', 'memory': '8 GB', 'storage': '100 GB SSD'})},
        {'provider_id': beget_prod.id, 'resource_id': 'beget-prod-vps-app-02', 'resource_type': 'server', 'resource_name': 'vps-app-02', 'region': 'ru-msk', 'status': 'active', 'service_name': 'VPS', 'effective_cost': 12500.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '4 vCPU', 'memory': '8 GB', 'storage': '100 GB SSD'})},
        {'provider_id': beget_prod.id, 'resource_id': 'beget-prod-vps-db-01', 'resource_type': 'server', 'resource_name': 'vps-db-01', 'region': 'ru-msk', 'status': 'active', 'service_name': 'VPS', 'effective_cost': 18000.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '8 vCPU', 'memory': '32 GB'})},
        {'provider_id': beget_prod.id, 'resource_id': 'beget-prod-vps-cache-01', 'resource_type': 'server', 'resource_name': 'vps-cache-01', 'region': 'ru-msk', 'status': 'active', 'service_name': 'VPS', 'effective_cost': 7000.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '2 vCPU', 'memory': '8 GB'})},
        {'provider_id': beget_prod.id, 'resource_id': 'beget-prod-vps-batch-01', 'resource_type': 'server', 'resource_name': 'vps-batch-01', 'region': 'ru-msk', 'status': 'active', 'service_name': 'VPS', 'effective_cost': 9000.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '4 vCPU', 'memory': '8 GB'})},
        {'provider_id': beget_prod.id, 'resource_id': 'beget-prod-vps-mq-01', 'resource_type': 'server', 'resource_name': 'vps-mq-01', 'region': 'ru-msk', 'status': 'active', 'service_name': 'VPS', 'effective_cost': 8500.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '2 vCPU', 'memory': '8 GB'})},
        {'provider_id': beget_prod.id, 'resource_id': 'beget-prod-domain', 'resource_type': 'domain', 'resource_name': 'infrazen-demo.ru', 'region': 'global', 'status': 'active', 'service_name': 'Domains', 'effective_cost': 50.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'registrar': 'beget'})},
        {'provider_id': beget_prod.id, 'resource_id': 'beget-prod-obj-storage', 'resource_type': 'file_storage', 'resource_name': 'obj-storage-prod', 'region': 'ru-msk', 'status': 'active', 'service_name': 'Object Storage', 'effective_cost': 6000.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'size': '2 TB'})},
        {'provider_id': beget_prod.id, 'resource_id': 'beget-prod-backup-service', 'resource_type': 'backup', 'resource_name': 'backup-service', 'region': 'ru-msk', 'status': 'active', 'service_name': 'Backups', 'effective_cost': 10000.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'policy': 'daily'})},
        {'provider_id': beget_prod.id, 'resource_id': 'beget-prod-lb-service', 'resource_type': 'load_balancer', 'resource_name': 'lb-service', 'region': 'ru-msk', 'status': 'active', 'service_name': 'Load Balancer', 'effective_cost': 6600.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'plan': 'M'})},
        {'provider_id': beget_prod.id, 'resource_id': 'beget-prod-nat-firewall', 'resource_type': 'network', 'resource_name': 'nat-firewall', 'region': 'ru-msk', 'status': 'active', 'service_name': 'Firewall', 'effective_cost': 4800.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'rules': 25})},
        {'provider_id': beget_prod.id, 'resource_id': 'beget-prod-extra-volumes', 'resource_type': 'volume', 'resource_name': 'extra-volumes', 'region': 'ru-msk', 'status': 'active', 'service_name': 'Block Storage', 'effective_cost': 9300.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'volumes': 3, 'total_size_gb': 180})},
    ])

    # Beget Dev resources (~41,850 ₽)
    add_resources([
        {'provider_id': beget_dev.id, 'resource_id': 'beget-dev-vps-01', 'resource_type': 'server', 'resource_name': 'dev-vps-01', 'region': 'ru-msk', 'status': 'active', 'service_name': 'VPS', 'effective_cost': 8000.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '4 vCPU', 'memory': '8 GB'})},
        {'provider_id': beget_dev.id, 'resource_id': 'beget-dev-vps-02', 'resource_type': 'server', 'resource_name': 'dev-vps-02', 'region': 'ru-msk', 'status': 'active', 'service_name': 'VPS', 'effective_cost': 8000.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '4 vCPU', 'memory': '8 GB'})},
        {'provider_id': beget_dev.id, 'resource_id': 'beget-dev-db-01', 'resource_type': 'server', 'resource_name': 'dev-db-01', 'region': 'ru-msk', 'status': 'active', 'service_name': 'VPS', 'effective_cost': 9000.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '4 vCPU', 'memory': '16 GB'})},
        {'provider_id': beget_dev.id, 'resource_id': 'beget-stage-web-01', 'resource_type': 'server', 'resource_name': 'stage-web-01', 'region': 'ru-msk', 'status': 'active', 'service_name': 'VPS', 'effective_cost': 7500.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '4 vCPU', 'memory': '8 GB'})},
        {'provider_id': beget_dev.id, 'resource_id': 'beget-dev-s3-bucket', 'resource_type': 'file_storage', 'resource_name': 's3-dev-bucket', 'region': 'ru-msk', 'status': 'active', 'service_name': 'Object Storage', 'effective_cost': 2800.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'size': '300 GB'})},
        {'provider_id': beget_dev.id, 'resource_id': 'beget-ci-dev-runner', 'resource_type': 'server', 'resource_name': 'ci-dev-runner', 'region': 'ru-msk', 'status': 'active', 'service_name': 'VPS', 'effective_cost': 5500.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'cpu': '4 vCPU', 'memory': '8 GB'})},
        {'provider_id': beget_dev.id, 'resource_id': 'beget-dev-public-ip', 'resource_type': 'ip', 'resource_name': 'dev-public-ip', 'region': 'ru-msk', 'status': 'active', 'service_name': 'Networking', 'effective_cost': 150.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'type': 'public'})},
        {'provider_id': beget_dev.id, 'resource_id': 'beget-dev-logs-storage', 'resource_type': 'file_storage', 'resource_name': 'dev-logs-storage', 'region': 'ru-msk', 'status': 'active', 'service_name': 'Object Storage', 'effective_cost': 1900.0, 'currency': 'RUB', 'billing_period': 'monthly', 'provider_config': json.dumps({'size': '500 GB'})},
    ])

    # Tags for key resources
    try:
        # Selectel BU-A
        for name, tags in [
            ('api-backend-prod-01', {'env': 'production', 'tier': 'api'}),
            ('db-postgres-prod-01', {'env': 'production', 'tier': 'database'}),
            ('postgres-data-volume', {'type': 'storage'}),
            ('s3-cdn-static', {'type': 'cdn', 'public': 'true'}),
        ]:
            r = Resource.query.filter_by(provider_id=selectel_bu_a.id, resource_name=name).first()
            if r:
                for k, v in tags.items():
                    r.add_tag(k, v)

        # Selectel BU-B
        for name, tags in [
            ('web-frontend-01', {'env': 'staging', 'tier': 'web'}),
            ('web-frontend-02', {'env': 'staging', 'tier': 'web'}),
            ('db-mysql-staging', {'env': 'staging', 'tier': 'database'}),
            ('s3-media-bucket', {'type': 'media'}),
        ]:
            r = Resource.query.filter_by(provider_id=selectel_bu_b.id, resource_name=name).first()
            if r:
                for k, v in tags.items():
                    r.add_tag(k, v)

        # Beget Prod
        for name, tags in [
            ('vps-app-01', {'env': 'production', 'app': 'web'}),
            ('vps-app-02', {'env': 'production', 'app': 'web'}),
            ('vps-db-01', {'env': 'production', 'tier': 'database'}),
        ]:
            r = Resource.query.filter_by(provider_id=beget_prod.id, resource_name=name).first()
            if r:
                for k, v in tags.items():
                    r.add_tag(k, v)

        # Beget Dev
        for name, tags in [
            ('dev-vps-01', {'env': 'development'}),
            ('dev-vps-02', {'env': 'development'}),
        ]:
            r = Resource.query.filter_by(provider_id=beget_dev.id, resource_name=name).first()
            if r:
                for k, v in tags.items():
                    r.add_tag(k, v)
        db.session.commit()
    except Exception:
        db.session.rollback()
    print("✅ Resources and tags created")
    
    # Note: ResourceStates will be created by seed_historical_complete_syncs()
    # for the latest (day 0) snapshot only

    # Create recommendations (20, RU)
    print("🔄 Creating cost optimization recommendations (20)...")
    def R(p, name):
        return Resource.query.filter_by(provider_id=p.id, resource_name=name).first()

    recs = [
        # 1 Resize CPU down
        {
            'p': selectel_bu_a, 'name': 'api-backend-prod-01', 'type': 'rightsizing', 'sev': 'high',
            'title': 'Снизить vCPU для api-backend-prod-01',
            'desc': 'Средняя загрузка CPU 8% за 30 дней. Рекомендуется уменьшить конфигурацию с 8 до 4 vCPU.',
            'save': 1800.0, 'metrics': {'cpu_avg': 0.08}
        },
        # 2 Stop idle VM
        {
            'p': selectel_bu_b, 'name': 'ci-runner-spot', 'type': 'shutdown', 'sev': 'critical',
            'title': 'Остановить неиспользуемую VM ci-runner-spot',
            'desc': 'Нет входящего трафика и загрузки CPU за 30 дней.',
            'save': 3200.0, 'metrics': {'cpu_avg': 0.0, 'net_in': 0}
        },
        # 3 Delete unused volume
        {
            'p': selectel_bu_b, 'name': 'pg-backup-volume', 'type': 'cleanup', 'sev': 'medium',
            'title': 'Удалить неиспользуемый том pg-backup-volume',
            'desc': 'Том не подключён ни к одному инстансу более 45 дней.',
            'save': 450.0, 'metrics': {'attachments': 0, 'last_used_days': 45}
        },
        # 4 Cheaper region
        {'p': selectel_bu_a, 'name': 'k8s-worker-02', 'type': 'migrate', 'sev': 'low', 'title': 'Перенести k8s-worker-02 в более дешёвый регион', 'desc': 'Стоимость в целевом регионе на ~25% ниже при сопоставимых параметрах.', 'save': 700.0, 'metrics': {'current_region': 'ru-1', 'target_region': 'ru-2'}},
        # 5 Resize RAM down
        {'p': selectel_bu_b, 'name': 'db-mysql-staging', 'type': 'rightsizing', 'sev': 'medium', 'title': 'Снизить RAM для db-mysql-staging', 'desc': 'Пиковое использование памяти за 14 дней 38%.', 'save': 900.0, 'metrics': {'mem_avg_gb': 3.1, 'mem_p95_gb': 6.2}},
        # 6 Storage class switch
        {'p': selectel_bu_b, 'name': 's3-media-bucket', 'type': 'migrate', 'sev': 'low', 'title': 'Перевести s3-media-bucket в класс хранения «нечастый доступ»', 'desc': 'Доступ реже 1 раза за 30 дней.', 'save': 350.0, 'metrics': {'access_per_30d': 0}},
        # 7 Old snapshots
        {'p': selectel_bu_a, 'name': 'snapshot-storage', 'type': 'cleanup', 'sev': 'medium', 'title': 'Удалить устаревшие снапшоты', 'desc': '5 снапшотов старше 60 дней.', 'save': 520.0, 'metrics': {'snapshots': 5, 'oldest_days': 120}},
        # 8 Shrink volume
        {'p': selectel_bu_a, 'name': 'postgres-data-volume', 'type': 'rightsizing', 'sev': 'high', 'title': 'Уменьшить том postgres-data-volume', 'desc': 'Использование диска 48% стабильно.', 'save': 600.0, 'metrics': {'disk_used_gb': 240, 'disk_size_gb': 500}},
        # 9 Commitment
        {'p': beget_prod, 'name': 'vps-app-01', 'type': 'commitment', 'sev': 'info', 'title': 'Перейти на подписку с коммитом для vps-app-01', 'desc': 'Стабильное использование за 90 дней, коммит даст скидку.', 'save': 800.0, 'metrics': {'lookback_days': 90}},
        # 10 Cross-provider migrate
        {'p': selectel_bu_b, 'name': 'web-frontend-01', 'type': 'migrate', 'sev': 'high', 'title': 'Мигрировать web-frontend-01 к более дешёвому провайдеру', 'desc': 'Найдены эквивалентные характеристики с экономией ~22%.', 'save': 2100.0, 'metrics': {'match_score': 0.86}},
        # 11 Night/weekend shutdown
        {'p': beget_dev, 'name': 'dev-vps-01', 'type': 'shutdown', 'sev': 'medium', 'title': 'Останавливать dev-vps-01 на ночь и выходные', 'desc': 'Рабочие часы 08:00–20:00 Пн-Пт, вне окна простаивает.', 'save': 1100.0, 'metrics': {'work_hours': '8-20', 'days': 'Mon-Fri'}},
        # 12 Release unused IP
        {'p': beget_dev, 'name': 'dev-public-ip', 'type': 'cleanup', 'sev': 'low', 'title': 'Освободить неиспользуемый публичный IP', 'desc': 'IP не привязан к ресурсам, тарифицируется отдельно.', 'save': 150.0, 'metrics': {'attached': False}},
        # 13 Downsize LB
        {'p': selectel_bu_a, 'name': 'lb-prod-01', 'type': 'rightsizing', 'sev': 'medium', 'title': 'Понизить тариф балансировщика lb-prod-01', 'desc': 'Средний трафик <10% лимита текущего плана.', 'save': 400.0, 'metrics': {'avg_rps': 12, 'plan_rps_cap': 200}},
        # 14 Merge small volumes
        {'p': beget_prod, 'name': 'extra-volumes', 'type': 'migrate', 'sev': 'low', 'title': 'Объединить малые тома для снижения накладных расходов', 'desc': 'Несколько томов <20 ГБ могут быть объединены.', 'save': 260.0, 'metrics': {'volumes': 3, 'avg_size_gb': 12}},
        # 15 Switch disk type
        {'p': selectel_bu_a, 'name': 'db-postgres-prod-01', 'type': 'migrate', 'sev': 'medium', 'title': 'Сменить тип диска на стандартный для db-postgres-prod-01', 'desc': 'IOPS/latency низкие — премиум-диск избыточен.', 'save': 980.0, 'metrics': {'iops_avg': 150, 'disk_type': 'premium'}},
        # 16 Remove old images (use BU-A as placeholder store)
        {'p': selectel_bu_a, 'name': 's3-cdn-static', 'type': 'cleanup', 'sev': 'low', 'title': 'Удалить неиспользуемые образы (>90 дней)', 'desc': 'Образы не запускались в течение 3 месяцев.', 'save': 320.0, 'metrics': {'images': 4, 'oldest_days': 120}},
        # 17 Downsize DB
        {'p': beget_prod, 'name': 'vps-db-01', 'type': 'rightsizing', 'sev': 'high', 'title': 'Уменьшить конфигурацию БД (vps-db-01)', 'desc': 'Нагрузка БД стабильно низкая, буферный кеш не заполняется.', 'save': 2400.0, 'metrics': {'cpu_avg': 0.09, 'mem_avg': 0.28}},
        # 18 Enable autoscaling
        {'p': selectel_bu_b, 'name': 'web-frontend-02', 'type': 'commitment', 'sev': 'medium', 'title': 'Включить авто-масштабирование вместо фиксированных VM', 'desc': 'Нагрузка по часам меняется, выгоднее авто-скейлинг.', 'save': 1300.0, 'metrics': {'variance': 0.4}},
        # 19 Rightsize K8s nodes
        {'p': selectel_bu_a, 'name': 'k8s-worker-01', 'type': 'rightsizing', 'sev': 'high', 'title': 'Правильный размер узлов Kubernetes', 'desc': 'Requests/limits значительно превышают фактическое потребление.', 'save': 1750.0, 'metrics': {'requests_cpu': 16, 'used_cpu': 6}},
        # 20 Move cold objects
        {'p': selectel_bu_a, 'name': 'archive-cold-storage', 'type': 'migrate', 'sev': 'low', 'title': 'Перевести нечасто используемые объекты в холодное хранилище', 'desc': 'Чтение реже 1 раза в 60 дней — cold-tier выгоднее.', 'save': 540.0, 'metrics': {'access_per_60d': 0}},
    ]

    created = 0
    for rec in recs:
        res = R(rec['p'], rec['name'])
        if not res:
            continue
        db.session.add(OptimizationRecommendation(
            resource_id=res.id,
            provider_id=rec['p'].id,
            recommendation_type=rec['type'],
            category='cost',
            severity=rec['sev'],
            title=rec['title'],
            description=rec['desc'],
            estimated_monthly_savings=rec['save'],
            currency='RUB',
            resource_type=res.resource_type,
            resource_name=res.resource_name,
            metrics_snapshot=json.dumps(rec.get('metrics', {})),
            insights=json.dumps({'explanation': 'Автоматически сгенерировано для демо'}),
            status='pending'
        ))
        created += 1
    db.session.commit()
    print(f"✅ Created {created} recommendations")
    
    # Summary
    print("\n" + "="*60)
    print("✅ Demo user base seeding completed successfully!")
    print("="*60)
    print(f"Demo User ID: {demo_user.id}")
    print(f"Email: {demo_user.email}")
    print(f"Password: demo")
    total_monthly = 166600 + 104300 + 104250 + 41850
    print(f"\nProviders: 4 (Selectel BU-A, Selectel BU-B, Beget Prod, Beget Dev)")
    # Count resources for demo user
    total_resources = Resource.query.join(CloudProvider, Resource.provider_id == CloudProvider.id).filter(CloudProvider.user_id == demo_user.id).count()
    print(f"Resources: {total_resources}")
    print(f"Recommendations: {created}")
    print(f"Total Monthly Cost: ₽{total_monthly:,}")
    print("="*60)
    
    # Return demo user and providers for historical sync generation
    providers_dict = {
        'selectel_bu_a': selectel_bu_a,
        'selectel_bu_b': selectel_bu_b,
        'beget_prod': beget_prod,
        'beget_dev': beget_dev
    }
    
    return demo_user, providers_dict

def seed_historical_complete_syncs(demo_user, providers):
    """
    Generate 90 days of historical complete sync data with realistic cost variations
    This creates a complete timeline for analytics page trending
    
    Args:
        demo_user: The demo user object
        providers: Dict with keys 'beget_prod', 'beget_dev', 'selectel_bu_a', 'selectel_bu_b'
    """
    print("\n" + "="*60)
    print("🔄 Generating 3-month historical sync data...")
    print("="*60)
    
    # Base costs per provider (daily)
    BASE_COSTS = {
        'selectel_bu_a': 166600.0 / 30.0,  # ~5,553 ₽/day
        'selectel_bu_b': 104300.0 / 30.0,  # ~3,477 ₽/day
        'beget_prod': 104250.0 / 30.0,      # ~3,475 ₽/day
        'beget_dev': 41850.0 / 30.0,        # ~1,395 ₽/day
    }
    
    # Resource counts per provider (for latest snapshot)
    RESOURCE_COUNTS = {
        'selectel_bu_a': 13,
        'selectel_bu_b': 12,
        'beget_prod': 12,
        'beget_dev': 8
    }
    
    # Calculate total base daily cost
    total_base_daily = sum(BASE_COSTS.values())  # ~13,900 ₽/day
    
    print(f"Base daily cost: ₽{total_base_daily:,.2f}")
    print(f"Target annual spend: ₽{total_base_daily * 365:,.2f}")
    
    # Generate 90 days of syncs (from 90 days ago to today)
    today = datetime.now()
    
    complete_syncs_created = 0
    provider_snapshots_created = 0
    
    for days_ago in range(90, -1, -1):  # 90, 89, 88, ... 1, 0
        sync_date = today - timedelta(days=days_ago)
        
        # Calculate growth factor (2% total growth over 90 days)
        growth_factor = 1.0 + (0.02 * (90 - days_ago) / 90)
        
        # Add daily variance (±7%)
        daily_variance = random.uniform(0.93, 1.07)
        
        # Calculate costs for each provider
        provider_costs = {}
        provider_resources = {}
        provider_snapshot_ids = {}
        
        total_daily_cost = 0.0
        total_resources = 0
        
        # Create individual provider snapshots first
        for provider_key, provider in providers.items():
            base_cost = BASE_COSTS[provider_key]
            
            # Apply growth and variance
            daily_cost = base_cost * growth_factor * daily_variance
            monthly_cost = daily_cost * 30.0
            
            # Resource count (with slight variation for realism, but exact on day 0)
            if days_ago == 0:
                resource_count = RESOURCE_COUNTS[provider_key]
            else:
                resource_count = max(1, int(RESOURCE_COUNTS[provider_key] * random.uniform(0.95, 1.00)))
            
            # Create provider snapshot
            snapshot = SyncSnapshot(
                provider_id=provider.id,
                sync_type='scheduled',
                sync_status='success',
                sync_started_at=sync_date - timedelta(minutes=random.randint(5, 15)),
                sync_completed_at=sync_date,
                sync_duration_seconds=random.randint(30, 180),
                total_resources_found=resource_count,
                resources_created=resource_count if days_ago == 90 else 0,
                resources_updated=0 if days_ago == 90 else resource_count,
                resources_deleted=0,
                resources_unchanged=0,
                total_monthly_cost=monthly_cost,
                total_resources_by_type=json.dumps({'server': resource_count // 2, 'storage': resource_count // 3, 'other': resource_count // 6}),
                total_resources_by_status=json.dumps({'active': resource_count, 'stopped': 0})
            )
            
            db.session.add(snapshot)
            db.session.flush()  # Get the snapshot ID
            
            provider_costs[str(provider.id)] = daily_cost
            provider_resources[str(provider.id)] = resource_count
            provider_snapshot_ids[provider_key] = snapshot.id
            
            total_daily_cost += daily_cost
            total_resources += resource_count
            provider_snapshots_created += 1
        
        # Create complete sync record
        complete_sync = CompleteSync(
            user_id=demo_user.id,
            sync_type='scheduled',
            sync_status='success',
            sync_started_at=sync_date - timedelta(minutes=random.randint(15, 30)),
            sync_completed_at=sync_date,
            sync_duration_seconds=random.randint(120, 600),
            total_providers_synced=4,
            successful_providers=4,
            failed_providers=0,
            total_resources_found=total_resources,
            total_daily_cost=total_daily_cost,
            total_monthly_cost=total_daily_cost * 30.0,
            cost_by_provider=json.dumps(provider_costs),
            resources_by_provider=json.dumps(provider_resources),
            sync_config=json.dumps({'auto_sync': True, 'include_inactive': False})
        )
        
        db.session.add(complete_sync)
        db.session.flush()  # Get the complete_sync ID
        
        # Create provider sync references
        for provider_key, snapshot_id in provider_snapshot_ids.items():
            provider = providers[provider_key]
            ref = ProviderSyncReference(
                complete_sync_id=complete_sync.id,
                provider_id=provider.id,
                sync_snapshot_id=snapshot_id,
                sync_order=list(provider_snapshot_ids.keys()).index(provider_key) + 1,
                sync_status='success',
                sync_duration_seconds=random.randint(30, 180),
                provider_cost=provider_costs[str(provider.id)],
                resources_synced=provider_resources[str(provider.id)]
            )
            db.session.add(ref)
        
        complete_syncs_created += 1
        
        # For the latest snapshot (day 0), create ResourceState records
        if days_ago == 0:
            print("\n🔄 Creating resource states for latest snapshots...")
            for provider_key, snapshot_id in provider_snapshot_ids.items():
                provider = providers[provider_key]
                resources = Resource.query.filter_by(provider_id=provider.id).all()
                
                for r in resources:
                    state = ResourceState(
                        sync_snapshot_id=snapshot_id,
                        resource_id=r.id,
                        provider_resource_id=r.resource_id,
                        resource_type=r.resource_type,
                        resource_name=r.resource_name,
                        state_action='created',
                        previous_state=None,
                        current_state=json.dumps({
                            'resource_name': r.resource_name,
                            'status': r.status,
                            'effective_cost': r.effective_cost,
                            'region': r.region,
                            'service_name': r.service_name,
                            'provider_config': r.get_provider_config(),
                        }),
                        changes_detected=json.dumps({}),
                        service_name=r.service_name,
                        region=r.region,
                        status=r.status,
                        effective_cost=r.effective_cost,
                        has_cost_change=False,
                        has_status_change=False,
                        has_config_change=False,
                    )
                    db.session.add(state)
                
                print(f"  ✓ Created {len(resources)} resource states for {provider.connection_name}")
            
            db.session.commit()
            print("✅ Resource states for latest snapshot created")
        
        # Commit every 10 syncs to avoid memory issues
        if complete_syncs_created % 10 == 0:
            db.session.commit()
            print(f"  ✓ Generated {complete_syncs_created}/91 complete syncs (Day -{days_ago})")
    
    # Final commit
    db.session.commit()
    
    print("\n" + "="*60)
    print("✅ Historical sync data generation completed!")
    print("="*60)
    print(f"Complete Syncs Created: {complete_syncs_created}")
    print(f"Provider Snapshots Created: {provider_snapshots_created}")
    print(f"Total Records: {complete_syncs_created + provider_snapshots_created + (complete_syncs_created * 4)}")
    print(f"Date Range: {(today - timedelta(days=90)).strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}")
    print(f"Final Daily Cost: ₽{total_daily_cost:,.2f}")
    print(f"Final Monthly Projection: ₽{total_daily_cost * 30.0:,.2f}")
    print(f"Final Annual Projection: ₽{total_daily_cost * 365.0:,.2f}")
    print("="*60 + "\n")

def main():
    """Main seeding function"""
    from app import create_app
    
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("Demo User Seeding Script")
        print("=" * 60)
        print()
        
        try:
            # Seed base demo user data
            demo_user, providers = seed_demo_user()
            
            # Generate 90 days of historical complete sync data
            seed_historical_complete_syncs(demo_user, providers)
            
            print("\n" + "="*60)
            print("🎉 COMPLETE! Demo user fully seeded with 3-month history!")
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ Error seeding demo user: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    main()

