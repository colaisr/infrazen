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
from app.core.models.business_board import BusinessBoard
from app.core.models.board_resource import BoardResource
from app.core.models.board_group import BoardGroup
import random
import uuid

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
        
        # Delete business context data
        board_ids = [b.id for b in BusinessBoard.query.filter_by(user_id=demo_user.id).all()]
        if board_ids:
            BoardResource.query.filter(BoardResource.board_id.in_(board_ids)).delete(synchronize_session=False)
            db.session.commit()
            BoardGroup.query.filter(BoardGroup.board_id.in_(board_ids)).delete(synchronize_session=False)
            db.session.commit()
            BusinessBoard.query.filter(BusinessBoard.id.in_(board_ids)).delete(synchronize_session=False)
            db.session.commit()
            print("  ✓ Deleted business context boards, groups, and resources")
        
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
        # 1 Major rightsizing - High-value CPU optimization
        {
            'p': selectel_bu_a, 'name': 'api-backend-prod-01', 'type': 'rightsizing', 'sev': 'critical',
            'title': 'Критическое снижение vCPU для api-backend-prod-01',
            'desc': 'Средняя загрузка CPU 6% за 30 дней. Рекомендуется уменьшить конфигурацию с 16 до 4 vCPU.',
            'save': 10500.0, 'metrics': {'cpu_avg': 0.06, 'current_vcpu': 16, 'recommended_vcpu': 4}
        },
        # 2 Stop idle production VM
        {
            'p': selectel_bu_b, 'name': 'ci-runner-spot', 'type': 'shutdown', 'sev': 'critical',
            'title': 'Остановить неиспользуемую production VM ci-runner-spot',
            'desc': 'Нет входящего трафика и загрузки CPU за 45 дней. Критическая экономия.',
            'save': 7200.0, 'metrics': {'cpu_avg': 0.0, 'net_in': 0, 'idle_days': 45}
        },
        # 3 Major storage cleanup
        {
            'p': selectel_bu_b, 'name': 'pg-backup-volume', 'type': 'cleanup', 'sev': 'high',
            'title': 'Удалить неиспользуемые backup тома (2TB)',
            'desc': 'Томы не подключены более 60 дней. Общий объем 2TB неиспользуемого хранилища.',
            'save': 4800.0, 'metrics': {'attachments': 0, 'last_used_days': 60, 'size_tb': 2}
        },
        # 4 Major region migration
        {'p': selectel_bu_a, 'name': 'k8s-worker-02', 'type': 'migrate', 'sev': 'high', 
         'title': 'Перенести k8s-worker-02 в более дешёвый регион', 
         'desc': 'Стоимость в целевом регионе на ~40% ниже при сопоставимых параметрах. Крупная экономия.', 
         'save': 6800.0, 'metrics': {'current_region': 'ru-1', 'target_region': 'ru-2', 'savings_percent': 40}},
        # 5 Major RAM rightsizing
        {'p': selectel_bu_b, 'name': 'db-mysql-staging', 'type': 'rightsizing', 'sev': 'high', 
         'title': 'Критическое снижение RAM для db-mysql-staging', 
         'desc': 'Пиковое использование памяти за 30 дней 25%. Можно снизить с 32GB до 16GB.', 
         'save': 8500.0, 'metrics': {'mem_avg_gb': 8.2, 'mem_p95_gb': 12.5, 'current_gb': 32, 'recommended_gb': 16}},
        # 6 Major storage class optimization
        {'p': selectel_bu_b, 'name': 's3-media-bucket', 'type': 'migrate', 'sev': 'high', 
         'title': 'Перевести s3-media-bucket в архивное хранилище', 
         'desc': 'Доступ реже 1 раза за 90 дней. Архивное хранилище в 5 раз дешевле.', 
         'save': 3800.0, 'metrics': {'access_per_90d': 0, 'size_tb': 1.2, 'savings_percent': 80}},
        # 7 Major snapshot cleanup
        {'p': selectel_bu_a, 'name': 'snapshot-storage', 'type': 'cleanup', 'sev': 'high', 
         'title': 'Удалить устаревшие снапшоты (15TB)', 
         'desc': '25 снапшотов старше 90 дней. Общий объем 15TB неиспользуемого хранилища.', 
         'save': 5400.0, 'metrics': {'snapshots': 25, 'oldest_days': 120, 'size_tb': 15}},
        # 8 Major volume rightsizing
        {'p': selectel_bu_a, 'name': 'postgres-data-volume', 'type': 'rightsizing', 'sev': 'critical', 
         'title': 'Критическое уменьшение тома postgres-data-volume', 
         'desc': 'Использование диска 35% стабильно. Можно уменьшить с 2TB до 1TB.', 
         'save': 6800.0, 'metrics': {'disk_used_gb': 700, 'disk_size_gb': 2000, 'recommended_gb': 1000}},
        # 9 Major commitment discount
        {'p': beget_prod, 'name': 'vps-app-01', 'type': 'commitment', 'sev': 'high', 
         'title': 'Перейти на 3-летний коммит для vps-app-01', 
         'desc': 'Стабильное использование за 180 дней. 3-летний коммит даст скидку 35%.', 
         'save': 4800.0, 'metrics': {'lookback_days': 180, 'commitment_years': 3, 'discount_percent': 35}},
        # 10 Major cross-provider migration
        {'p': selectel_bu_b, 'name': 'web-frontend-01', 'type': 'migrate', 'sev': 'critical', 
         'title': 'Мигрировать web-frontend-01 к более дешёвому провайдеру', 
         'desc': 'Найдены эквивалентные характеристики с экономией ~45%. Крупная миграция.', 
         'save': 10500.0, 'metrics': {'match_score': 0.92, 'savings_percent': 45}},
        # 11 Major dev environment optimization
        {'p': beget_dev, 'name': 'dev-vps-01', 'type': 'shutdown', 'sev': 'high', 
         'title': 'Останавливать dev-vps-01 на ночь и выходные (крупная экономия)', 
         'desc': 'Рабочие часы 09:00–18:00 Пн-Пт. Остановка на 75% времени.', 
         'save': 6800.0, 'metrics': {'work_hours': '9-18', 'days': 'Mon-Fri', 'uptime_percent': 25}},
        # 12 Major IP cleanup
        {'p': beget_dev, 'name': 'dev-public-ip', 'type': 'cleanup', 'sev': 'medium', 
         'title': 'Освободить неиспользуемые публичные IP (5 адресов)', 
         'desc': '5 IP не привязаны к ресурсам, тарифицируются отдельно.', 
         'save': 1400.0, 'metrics': {'attached': False, 'count': 5}},
        # 13 Major load balancer optimization
        {'p': selectel_bu_a, 'name': 'lb-prod-01', 'type': 'rightsizing', 'sev': 'high', 
         'title': 'Критическое понижение тарифа балансировщика lb-prod-01', 
         'desc': 'Средний трафик <5% лимита текущего плана. Можно снизить в 3 раза.', 
         'save': 4800.0, 'metrics': {'avg_rps': 8, 'plan_rps_cap': 500, 'reduction_factor': 3}},
        # 14 Major volume consolidation
        {'p': beget_prod, 'name': 'extra-volumes', 'type': 'migrate', 'sev': 'high', 
         'title': 'Объединить малые тома для снижения накладных расходов', 
         'desc': '12 томов <50 ГБ могут быть объединены в 3 больших тома.', 
         'save': 3800.0, 'metrics': {'volumes': 12, 'avg_size_gb': 35, 'consolidated': 3}},
        # 15 Major disk type optimization
        {'p': selectel_bu_a, 'name': 'db-postgres-prod-01', 'type': 'migrate', 'sev': 'high', 
         'title': 'Сменить тип диска на стандартный для db-postgres-prod-01', 
         'desc': 'IOPS/latency низкие — премиум-диск избыточен. Экономия 60%.', 
         'save': 8500.0, 'metrics': {'iops_avg': 120, 'disk_type': 'premium', 'savings_percent': 60}},
        # 16 Major image cleanup
        {'p': selectel_bu_a, 'name': 's3-cdn-static', 'type': 'cleanup', 'sev': 'high', 
         'title': 'Удалить неиспользуемые образы (>180 дней)', 
         'desc': 'Образы не запускались в течение 6 месяцев. 2TB неиспользуемых образов.', 
         'save': 4800.0, 'metrics': {'images': 15, 'oldest_days': 200, 'size_tb': 2}},
        # 17 Major database rightsizing
        {'p': beget_prod, 'name': 'vps-db-01', 'type': 'rightsizing', 'sev': 'critical', 
         'title': 'Критическое уменьшение конфигурации БД (vps-db-01)', 
         'desc': 'Нагрузка БД стабильно низкая, буферный кеш не заполняется. Можно снизить в 2 раза.', 
         'save': 12500.0, 'metrics': {'cpu_avg': 0.12, 'mem_avg': 0.35, 'reduction_factor': 2}},
        # 18 Major autoscaling implementation
        {'p': selectel_bu_b, 'name': 'web-frontend-02', 'type': 'commitment', 'sev': 'high', 
         'title': 'Включить авто-масштабирование вместо фиксированных VM', 
         'desc': 'Нагрузка по часам меняется значительно, авто-скейлинг сэкономит 50%.', 
         'save': 8500.0, 'metrics': {'variance': 0.7, 'savings_percent': 50}},
        # 19 Major K8s optimization
        {'p': selectel_bu_a, 'name': 'k8s-worker-01', 'type': 'rightsizing', 'sev': 'critical', 
         'title': 'Критическая оптимизация узлов Kubernetes', 
         'desc': 'Requests/limits значительно превышают фактическое потребление. Можно снизить в 3 раза.', 
         'save': 14000.0, 'metrics': {'requests_cpu': 32, 'used_cpu': 8, 'reduction_factor': 3}},
        # 20 Major cold storage migration
        {'p': selectel_bu_a, 'name': 'archive-cold-storage', 'type': 'migrate', 'sev': 'high', 
         'title': 'Перевести архивные объекты в холодное хранилище', 
         'desc': 'Чтение реже 1 раза в 180 дней — cold-tier в 10 раз дешевле.', 
         'save': 6800.0, 'metrics': {'access_per_180d': 0, 'size_tb': 5, 'savings_percent': 90}},
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

def seed_usage_data_tags(demo_user, providers):
    """
    Generate usage data tags (CPU/memory statistics) for demo user resources
    This creates realistic daily usage data for the last 30 days
    """
    print("\n" + "="*60)
    print("🔄 Generating usage data tags for demo resources...")
    print("="*60)
    
    # Get all server resources for the demo user
    server_resources = []
    for provider in providers.values():
        resources = Resource.query.filter_by(provider_id=provider.id, resource_type='server').all()
        server_resources.extend(resources)
    
    print(f"Found {len(server_resources)} server resources to add usage data")
    
    tags_created = 0
    
    for resource in server_resources:
        # Check if this resource already has usage tags
        existing_usage_tags = ResourceTag.query.filter_by(resource_id=resource.id).filter(
            ResourceTag.tag_key.in_(['cpu_avg_usage', 'memory_avg_usage_mb'])
        ).count()
        
        if existing_usage_tags == 0:
            # Generate realistic CPU usage data (daily for 30 days)
            cpu_data = generate_daily_usage_data('cpu', resource.resource_name)
            memory_data = generate_daily_usage_data('memory', resource.resource_name)
            
            # Add CPU usage tags
            resource.add_tag('cpu_avg_usage', f"{cpu_data['avg_usage']:.1f}")
            resource.add_tag('cpu_max_usage', f"{cpu_data['max_usage']:.1f}")
            resource.add_tag('cpu_min_usage', f"{cpu_data['min_usage']:.1f}")
            resource.add_tag('cpu_raw_data', json.dumps(cpu_data['raw_data']))
            
            # Add memory usage tags
            resource.add_tag('memory_avg_usage_mb', f"{memory_data['avg_usage']:.1f}")
            resource.add_tag('memory_max_usage_mb', f"{memory_data['max_usage']:.1f}")
            resource.add_tag('memory_min_usage_mb', f"{memory_data['min_usage']:.1f}")
            resource.add_tag('memory_raw_data', json.dumps(memory_data['raw_data']))
            
            tags_created += 8
            print(f"  ✓ Added usage data for {resource.resource_name}")
        else:
            print(f"  ⏭️  Skipping {resource.resource_name} (already has usage data)")
    
    db.session.commit()
    print(f"\n✅ Created {tags_created} usage data tags for {len(server_resources)} resources")

def generate_daily_usage_data(metric_type, resource_name):
    """
    Generate realistic daily usage data for the last 30 days
    Correlates with seeded recommendations for underuse scenarios
    """
    from datetime import datetime, timedelta
    import random
    
    # Specific correlations with recommendations for underuse scenarios
    if resource_name == 'api-backend-prod-01':
        # Recommendation: CPU 6% average - critical rightsizing needed
        base_usage = 6.0 if metric_type == 'cpu' else 25.0
        variance = 0.2  # Very low variance for consistent underuse
    elif resource_name == 'ci-runner-spot':
        # Recommendation: 0% CPU, no traffic for 45 days - should be shutdown
        base_usage = 0.0 if metric_type == 'cpu' else 5.0
        variance = 0.1  # Almost no usage
    elif resource_name == 'db-mysql-staging':
        # Recommendation: 25% memory peak - rightsizing needed
        base_usage = 20.0 if metric_type == 'cpu' else 25.0
        variance = 0.3
    elif resource_name == 'dev-vps-01':
        # Recommendation: Should be stopped nights/weekends - 25% uptime
        base_usage = 15.0 if metric_type == 'cpu' else 20.0
        variance = 0.4
    elif resource_name == 'vps-db-01':
        # Recommendation: 12% CPU, 35% memory - critical rightsizing
        base_usage = 12.0 if metric_type == 'cpu' else 35.0
        variance = 0.3
    elif resource_name == 'k8s-worker-01':
        # Recommendation: 8 CPU used vs 32 requested - 3x reduction possible
        base_usage = 8.0 if metric_type == 'cpu' else 30.0
        variance = 0.2
    elif 'prod' in resource_name.lower():
        base_usage = 45.0  # Production resources have higher usage
        variance = 0.3
    elif 'dev' in resource_name.lower() or 'test' in resource_name.lower():
        base_usage = 15.0  # Dev/test resources have lower usage
        variance = 0.5
    elif 'db' in resource_name.lower():
        base_usage = 35.0  # Database resources have moderate usage
        variance = 0.4
    elif 'cache' in resource_name.lower() or 'redis' in resource_name.lower():
        base_usage = 20.0  # Cache resources have moderate usage
        variance = 0.4
    elif 'k8s' in resource_name.lower() or 'kubernetes' in resource_name.lower():
        base_usage = 30.0  # Kubernetes resources have moderate usage
        variance = 0.4
    elif 'analytics' in resource_name.lower() or 'etl' in resource_name.lower():
        base_usage = 25.0  # Analytics resources have moderate usage
        variance = 0.4
    else:
        base_usage = 25.0  # Default moderate usage
        variance = 0.4
    
    # Generate 30 days of data
    raw_data = []
    values = []
    
    for days_ago in range(29, -1, -1):  # 29, 28, ..., 1, 0
        date = datetime.now() - timedelta(days=days_ago)
        
        # Special weekend patterns for specific resources
        if resource_name == 'dev-vps-01':
            # Recommendation: Should be stopped nights/weekends - 25% uptime
            # Simulate work hours only (9-18 Mon-Fri)
            if date.weekday() >= 5:  # Weekend
                weekend_factor = 0.0  # Completely stopped
            else:  # Weekday
                weekend_factor = 0.3  # Only during work hours
        elif resource_name == 'ci-runner-spot':
            # Recommendation: 0% CPU, no traffic for 45 days - should be shutdown
            weekend_factor = 0.0  # Always idle
        else:
            # Standard weekend effect (lower usage on weekends)
            weekend_factor = 0.7 if date.weekday() >= 5 else 1.0
        
        # Add daily variance
        daily_variance = random.uniform(1 - variance, 1 + variance)
        
        # Calculate usage for this day
        if metric_type == 'cpu':
            usage = base_usage * weekend_factor * daily_variance
        else:  # memory
            usage = base_usage * weekend_factor * daily_variance * 1024  # Convert to MB
        
        # Ensure usage is within reasonable bounds
        if metric_type == 'cpu':
            usage = max(0.0, min(95.0, usage))  # Allow 0% for idle resources
        else:  # memory
            usage = max(0.0, min(8192.0, usage))  # Allow 0MB for idle resources
        
        raw_data.append([date.strftime('%Y-%m-%d'), usage])
        values.append(usage)
    
    return {
        'avg_usage': sum(values) / len(values),
        'max_usage': max(values),
        'min_usage': min(values),
        'raw_data': raw_data
    }

def seed_business_context(demo_user, providers):
    """
    Create business context boards for demo user
    Demonstrates FinOps insights: unit economics, feature costs, environment ratios, optimization pipeline
    """
    print("\n🔄 Creating Business Context boards...")
    
    # Show available providers
    print(f"  📦 Available providers:")
    for key, provider in providers.items():
        resource_count = Resource.query.filter_by(provider_id=provider.id).count()
        print(f"     - {key}: ID={provider.id}, Resources={resource_count}")
    
    # Helper to find resource by name and provider
    def find_resource(provider_id, resource_name):
        resource = Resource.query.filter_by(provider_id=provider_id, resource_name=resource_name).first()
        if not resource:
            print(f"     ⚠️  Resource not found: {resource_name} (provider_id: {provider_id})")
        return resource
    
    boards_created = 0
    groups_created = 0
    resources_placed = 0
    
    # ========================================================================
    # BOARD 1: Customer Allocation (Unit Economics)
    # ========================================================================
    print("  🎯 Board 1: Customer Allocation...")
    
    board1 = BusinessBoard(
        user_id=demo_user.id,
        name='Customer Allocation',
        is_default=True,
        viewport={'zoom': 1.0, 'pan_x': 0, 'pan_y': 0}
    )
    db.session.add(board1)
    db.session.commit()
    boards_created += 1
    print(f"     ✓ Board 1 created (ID: {board1.id})")
    
    # Create groups for Board 1
    group1_1 = BoardGroup(
        board_id=board1.id,
        name='Customer A (Enterprise)',
        fabric_id=str(uuid.uuid4()),
        position_x=100,
        position_y=100,
        width=350,
        height=300,
        color='#3B82F6',  # Blue
        calculated_cost=0.0
    )
    group1_2 = BoardGroup(
        board_id=board1.id,
        name='Customer B (SMB)',
        fabric_id=str(uuid.uuid4()),
        position_x=500,
        position_y=100,
        width=300,
        height=250,
        color='#10B981',  # Green
        calculated_cost=0.0
    )
    group1_3 = BoardGroup(
        board_id=board1.id,
        name='Customer C (Trial)',
        fabric_id=str(uuid.uuid4()),
        position_x=850,
        position_y=100,
        width=250,
        height=200,
        color='#F59E0B',  # Orange
        calculated_cost=0.0
    )
    group1_4 = BoardGroup(
        board_id=board1.id,
        name='Shared Infrastructure',
        fabric_id=str(uuid.uuid4()),
        position_x=100,
        position_y=450,
        width=1000,
        height=250,
        color='#6B7280',  # Gray
        calculated_cost=0.0
    )
    db.session.add_all([group1_1, group1_2, group1_3, group1_4])
    db.session.commit()
    groups_created += 4
    
    # Place resources on Board 1
    # Customer A (dedicated high-value resources)
    sel_a = providers['selectel_bu_a']
    for res_name, pos_x, pos_y, notes in [
        ('api-backend-prod-01', 150, 180, 'Выделенный API-бэкенд для Клиента A. SLA 99.9%. Критичен для корпоративного контракта.'),
        ('db-postgres-prod-01', 280, 180, 'Выделенная база данных Клиента A. Содержит конфиденциальные корпоративные данные.'),
        ('s3-cdn-static', 150, 280, 'Статические активы Клиента A и CDN-дистрибуция.')
    ]:
        res = find_resource(sel_a.id, res_name)
        if res:
            res.notes = notes  # System-wide notes
            br = BoardResource(
                board_id=board1.id,
                resource_id=res.id,
                position_x=pos_x,
                position_y=pos_y,
                group_id=group1_1.id
            )
            db.session.add(br)
            resources_placed += 1
    
    # Customer B (mid-tier)
    sel_b = providers['selectel_bu_b']
    for res_name, pos_x, pos_y in [
        ('web-frontend-01', 550, 180),
        ('db-mysql-staging', 680, 180)
    ]:
        res = find_resource(sel_b.id, res_name)
        if res:
            br = BoardResource(
                board_id=board1.id,
                resource_id=res.id,
                position_x=pos_x,
                position_y=pos_y,
                group_id=group1_2.id
            )
            db.session.add(br)
            resources_placed += 1
    
    # Customer C (trial - small resources)
    beget_dev = providers['beget_dev']
    res = find_resource(beget_dev.id, 'dev-vps-01')
    if res:
        br = BoardResource(
            board_id=board1.id,
            resource_id=res.id,
            position_x=900,
            position_y=180,
            group_id=group1_3.id
        )
        db.session.add(br)
        resources_placed += 1
    
    # Shared infrastructure
    for res_name, pos_x, pos_y, notes in [
        ('lb-prod-01', 150, 520, 'Общий балансировщик нагрузки для всех клиентов. Мультитенантная архитектура.'),
        ('k8s-worker-01', 300, 520, 'Kubernetes кластер - общие рабочие нагрузки для клиентов.'),
        ('k8s-worker-02', 450, 520, None)
    ]:
        res = find_resource(sel_a.id, res_name)
        if res:
            if notes:
                res.notes = notes
            br = BoardResource(
                board_id=board1.id,
                resource_id=res.id,
                position_x=pos_x,
                position_y=pos_y,
                group_id=group1_4.id
            )
            db.session.add(br)
            resources_placed += 1
    
    db.session.commit()
    
    # ========================================================================
    # BOARD 2: Product Features (Feature Cost Attribution)
    # ========================================================================
    print("  🎨 Board 2: Product Features...")
    
    board2 = BusinessBoard(
        user_id=demo_user.id,
        name='Product Features',
        is_default=False,
        viewport={'zoom': 1.0, 'pan_x': 0, 'pan_y': 0}
    )
    db.session.add(board2)
    db.session.commit()
    boards_created += 1
    print(f"     ✓ Board 2 created (ID: {board2.id})")
    
    # Create groups for Board 2
    group2_1 = BoardGroup(
        board_id=board2.id,
        name='Analytics Dashboard (ML/BI)',
        fabric_id=str(uuid.uuid4()),
        position_x=100,
        position_y=100,
        width=400,
        height=250,
        color='#8B5CF6',  # Purple
        calculated_cost=0.0
    )
    group2_2 = BoardGroup(
        board_id=board2.id,
        name='Mobile API',
        fabric_id=str(uuid.uuid4()),
        position_x=550,
        position_y=100,
        width=350,
        height=250,
        color='#3B82F6',  # Blue
        calculated_cost=0.0
    )
    group2_3 = BoardGroup(
        board_id=board2.id,
        name='Chat & Messaging',
        fabric_id=str(uuid.uuid4()),
        position_x=100,
        position_y=400,
        width=300,
        height=220,
        color='#10B981',  # Green
        calculated_cost=0.0
    )
    group2_4 = BoardGroup(
        board_id=board2.id,
        name='Search Engine',
        fabric_id=str(uuid.uuid4()),
        position_x=450,
        position_y=400,
        width=300,
        height=220,
        color='#F59E0B',  # Orange
        calculated_cost=0.0
    )
    db.session.add_all([group2_1, group2_2, group2_3, group2_4])
    db.session.commit()
    groups_created += 4
    
    # Place resources on Board 2
    # Analytics feature
    for res_name, pos_x, pos_y, notes in [
        ('analytics-etl-01', 150, 180, 'Обслуживает BI-дашборды. Используется 5% пользователей, но генерирует 40% корпоративных сделок.'),
        ('archive-cold-storage', 300, 180, 'Исторические данные аналитики. Требуется для compliance-отчётности.')
    ]:
        res = find_resource(sel_a.id, res_name)
        if res:
            if notes:
                res.notes = notes
            br = BoardResource(
                board_id=board2.id,
                resource_id=res.id,
                position_x=pos_x,
                position_y=pos_y,
                group_id=group2_1.id
            )
            db.session.add(br)
            resources_placed += 1
    
    # Mobile API
    for res_name, pos_x, pos_y in [
        ('api-backend-prod-01', 600, 180),
        ('s3-cdn-static', 750, 180)
    ]:
        res = find_resource(sel_a.id, res_name)
        if res:
            br = BoardResource(
                board_id=board2.id,
                resource_id=res.id,
                position_x=pos_x,
                position_y=pos_y,
                group_id=group2_2.id
            )
            db.session.add(br)
            resources_placed += 1
    
    # Chat feature
    beget_prod = providers['beget_prod']
    for res_name, pos_x, pos_y in [
        ('vps-mq-01', 150, 480),
        ('vps-cache-01', 280, 480)
    ]:
        res = find_resource(beget_prod.id, res_name)
        if res:
            br = BoardResource(
                board_id=board2.id,
                resource_id=res.id,
                position_x=pos_x,
                position_y=pos_y,
                group_id=group2_3.id
            )
            db.session.add(br)
            resources_placed += 1
    
    # Search engine
    for res_name, pos_x, pos_y in [
        ('k8s-worker-01', 500, 480),
        ('k8s-worker-02', 630, 480)
    ]:
        res = find_resource(sel_a.id, res_name)
        if res:
            br = BoardResource(
                board_id=board2.id,
                resource_id=res.id,
                position_x=pos_x,
                position_y=pos_y,
                group_id=group2_4.id
            )
            db.session.add(br)
            resources_placed += 1
    
    db.session.commit()
    
    # ========================================================================
    # BOARD 3: Environment & Teams (Operational View)
    # ========================================================================
    print("  🏗️  Board 3: Environment & Teams...")
    
    board3 = BusinessBoard(
        user_id=demo_user.id,
        name='Environment & Teams',
        is_default=False,
        viewport={'zoom': 1.0, 'pan_x': 0, 'pan_y': 0}
    )
    db.session.add(board3)
    db.session.commit()
    boards_created += 1
    print(f"     ✓ Board 3 created (ID: {board3.id})")
    
    # Create groups for Board 3
    group3_1 = BoardGroup(
        board_id=board3.id,
        name='Production (Team: Platform)',
        fabric_id=str(uuid.uuid4()),
        position_x=100,
        position_y=100,
        width=450,
        height=300,
        color='#EF4444',  # Red
        calculated_cost=0.0
    )
    group3_2 = BoardGroup(
        board_id=board3.id,
        name='Staging (Team: QA)',
        fabric_id=str(uuid.uuid4()),
        position_x=600,
        position_y=100,
        width=350,
        height=250,
        color='#F59E0B',  # Orange
        calculated_cost=0.0
    )
    group3_3 = BoardGroup(
        board_id=board3.id,
        name='Development (Team: Engineering)',
        fabric_id=str(uuid.uuid4()),
        position_x=100,
        position_y=450,
        width=400,
        height=250,
        color='#10B981',  # Green
        calculated_cost=0.0
    )
    group3_4 = BoardGroup(
        board_id=board3.id,
        name='CI/CD (Team: DevOps)',
        fabric_id=str(uuid.uuid4()),
        position_x=550,
        position_y=450,
        width=400,
        height=250,
        color='#8B5CF6',  # Purple
        calculated_cost=0.0
    )
    db.session.add_all([group3_1, group3_2, group3_3, group3_4])
    db.session.commit()
    groups_created += 4
    
    # Place resources on Board 3
    # Production environment
    for res_name, pos_x, pos_y in [
        ('api-backend-prod-01', 150, 180),
        ('db-postgres-prod-01', 280, 180),
        ('lb-prod-01', 410, 180),
        ('vps-app-01', 150, 280),
        ('vps-db-01', 280, 280)
    ]:
        # Try Selectel first
        res = find_resource(sel_a.id, res_name)
        if not res:
            res = find_resource(beget_prod.id, res_name)
        if res:
            br = BoardResource(
                board_id=board3.id,
                resource_id=res.id,
                position_x=pos_x,
                position_y=pos_y,
                group_id=group3_1.id
            )
            db.session.add(br)
            resources_placed += 1
    
    # Staging environment
    for res_name, pos_x, pos_y in [
        ('db-mysql-staging', 650, 180),
        ('stage-web-01', 780, 180)
    ]:
        res = find_resource(sel_b.id, res_name)
        if not res:
            res = find_resource(beget_dev.id, res_name)
        if res:
            br = BoardResource(
                board_id=board3.id,
                resource_id=res.id,
                position_x=pos_x,
                position_y=pos_y,
                group_id=group3_2.id
            )
            db.session.add(br)
            resources_placed += 1
    
    # Development environment
    for res_name, pos_x, pos_y in [
        ('dev-vps-01', 150, 530),
        ('dev-vps-02', 280, 530),
        ('dev-db-01', 410, 530)
    ]:
        res = find_resource(beget_dev.id, res_name)
        if res:
            br = BoardResource(
                board_id=board3.id,
                resource_id=res.id,
                position_x=pos_x,
                position_y=pos_y,
                group_id=group3_3.id
            )
            db.session.add(br)
            resources_placed += 1
    
    # CI/CD infrastructure
    for res_name, pos_x, pos_y, notes in [
        ('ci-runner-spot', 600, 530, 'Простаивает 75% времени. Рассмотреть расписание автоотключения для экономии.'),
        ('test-runner-01', 730, 530, None),
        ('ci-dev-runner', 860, 530, None)
    ]:
        res = find_resource(sel_b.id, res_name)
        if not res:
            res = find_resource(beget_dev.id, res_name)
        if res:
            if notes:
                res.notes = notes
            br = BoardResource(
                board_id=board3.id,
                resource_id=res.id,
                position_x=pos_x,
                position_y=pos_y,
                group_id=group3_4.id
            )
            db.session.add(br)
            resources_placed += 1
    
    db.session.commit()
    
    # ========================================================================
    # BOARD 4: Optimization Opportunities (FinOps Action Board)
    # ========================================================================
    print("  🎯 Board 4: Optimization Opportunities...")
    
    board4 = BusinessBoard(
        user_id=demo_user.id,
        name='Optimization Opportunities',
        is_default=False,
        viewport={'zoom': 1.0, 'pan_x': 0, 'pan_y': 0}
    )
    db.session.add(board4)
    db.session.commit()
    boards_created += 1
    print(f"     ✓ Board 4 created (ID: {board4.id})")
    
    # Create groups for Board 4 (Kanban-style)
    group4_1 = BoardGroup(
        board_id=board4.id,
        name='🔥 High Priority Savings',
        fabric_id=str(uuid.uuid4()),
        position_x=100,
        position_y=100,
        width=350,
        height=400,
        color='#EF4444',  # Red
        calculated_cost=0.0
    )
    group4_2 = BoardGroup(
        board_id=board4.id,
        name='⚠️ Medium Priority',
        fabric_id=str(uuid.uuid4()),
        position_x=500,
        position_y=100,
        width=300,
        height=400,
        color='#F59E0B',  # Orange
        calculated_cost=0.0
    )
    group4_3 = BoardGroup(
        board_id=board4.id,
        name='✅ Optimized',
        fabric_id=str(uuid.uuid4()),
        position_x=850,
        position_y=100,
        width=300,
        height=400,
        color='#10B981',  # Green
        calculated_cost=0.0
    )
    db.session.add_all([group4_1, group4_2, group4_3])
    db.session.commit()
    groups_created += 3
    
    # Place resources with critical recommendations in High Priority
    for res_name, pos_x, pos_y in [
        ('api-backend-prod-01', 150, 180),
        ('db-postgres-prod-01', 280, 180),
        ('k8s-worker-01', 150, 280)
    ]:
        res = find_resource(sel_a.id, res_name)
        if res:
            br = BoardResource(
                board_id=board4.id,
                resource_id=res.id,
                position_x=pos_x,
                position_y=pos_y,
                group_id=group4_1.id
            )
            db.session.add(br)
            resources_placed += 1
    
    # Medium priority
    for res_name, pos_x, pos_y in [
        ('lb-prod-01', 550, 180),
        ('s3-media-bucket', 680, 180)
    ]:
        res = find_resource(sel_a.id, res_name)
        if not res:
            res = find_resource(sel_b.id, res_name)
        if res:
            br = BoardResource(
                board_id=board4.id,
                resource_id=res.id,
                position_x=pos_x,
                position_y=pos_y,
                group_id=group4_2.id
            )
            db.session.add(br)
            resources_placed += 1
    
    # Already optimized
    for res_name, pos_x, pos_y, notes in [
        ('vps-app-01', 900, 180, 'Правильный размер. Мониторинг показывает оптимальное использование CPU/RAM.'),
        ('vps-cache-01', 1030, 180, 'Идеально подобранный Redis кэш. Оптимизация не требуется.')
    ]:
        res = find_resource(beget_prod.id, res_name)
        if res:
            if notes:
                res.notes = notes
            br = BoardResource(
                board_id=board4.id,
                resource_id=res.id,
                position_x=pos_x,
                position_y=pos_y,
                group_id=group4_3.id
            )
            db.session.add(br)
            resources_placed += 1
    
    db.session.commit()
    
    # Commit all resource notes
    db.session.commit()
    
    # Calculate group costs for all boards
    for board in [board1, board2, board3, board4]:
        for group in board.groups.all():
            total_cost = sum([
                br.resource.daily_cost or 0.0 
                for br in group.resources.all() 
                if br.resource and br.resource.daily_cost
            ])
            group.calculated_cost = total_cost
    
    db.session.commit()
    
    # Add text descriptions to canvas for each board
    print("  📝 Adding board descriptions...")
    
    board_descriptions = {
        'Customer Allocation': {
            'text': '💰 БИЗНЕС-ЦЕННОСТЬ: Юнит-экономика и прибыльность клиентов\n\n' +
                    '✓ Отслеживание стоимости на клиента\n' +
                    '✓ Валидация ценовых моделей\n' +
                    '✓ Определение маржинальности\n' +
                    '✓ Оптимизация высокодоходных клиентов\n\n' +
                    'ИНСАЙТ: Клиент A стоит ₽85К/мес, но платит ₽120К = маржа 41% ✅',
            'left': 100,
            'top': 720
        },
        'Product Features': {
            'text': '🎨 БИЗНЕС-ЦЕННОСТЬ: Распределение затрат по функциям и ROI\n\n' +
                    '✓ Видимость затрат на уровне функций\n' +
                    '✓ Решения "разработать или купить"\n' +
                    '✓ Приоритизация продуктовой дорожной карты\n' +
                    '✓ Закрытие функций с низким ROI\n\n' +
                    'ИНСАЙТ: ML/BI стоит 62% бюджета, но обеспечивает ключевую дифференциацию',
            'left': 100,
            'top': 770
        },
        'Environment & Teams': {
            'text': '🏗️ БИЗНЕС-ЦЕННОСТЬ: Операционное здоровье и соотношения ресурсов\n\n' +
                    '✓ Мониторинг соотношения затрат Dev/Prod\n' +
                    '✓ Метрики эффективности команд\n' +
                    '✓ Контроль разрастания окружений\n' +
                    '✓ Распределение затрат между командами\n\n' +
                    'ИНСАЙТ: Соотношение Prod:Dev 3.6:1 (здоровое для SaaS)',
            'left': 100,
            'top': 750
        },
        'Optimization Opportunities': {
            'text': '🎯 БИЗНЕС-ЦЕННОСТЬ: Визуальный пайплайн экономии и отслеживание действий\n\n' +
                    '✓ Приоритизация высокоэффективной экономии\n' +
                    '✓ Отслеживание прогресса оптимизации\n' +
                    '✓ Измерение фактической vs прогнозной экономии\n' +
                    '✓ Цикл непрерывного улучшения\n\n' +
                    'ИНСАЙТ: Выявлена экономия ₽10.4К/мес на 8 ресурсах',
            'left': 100,
            'top': 520
        }
    }
    
    for board in [board1, board2, board3, board4]:
        if board.name in board_descriptions:
            desc = board_descriptions[board.name]
            canvas_state = {
                'objects': [
                    {
                        'type': 'textbox',
                        'version': '5.3.0',
                        'originX': 'left',
                        'originY': 'top',
                        'left': desc['left'],
                        'top': desc['top'],
                        'width': 500,
                        'height': 200,
                        'fill': '#1F2937',
                        'stroke': None,
                        'strokeWidth': 0,
                        'strokeDashArray': None,
                        'strokeLineCap': 'butt',
                        'strokeDashOffset': 0,
                        'strokeLineJoin': 'miter',
                        'strokeUniform': False,
                        'strokeMiterLimit': 4,
                        'scaleX': 1,
                        'scaleY': 1,
                        'angle': 0,
                        'flipX': False,
                        'flipY': False,
                        'opacity': 1,
                        'shadow': None,
                        'visible': True,
                        'backgroundColor': '',
                        'fillRule': 'nonzero',
                        'paintFirst': 'fill',
                        'globalCompositeOperation': 'source-over',
                        'skewX': 0,
                        'skewY': 0,
                        'text': desc['text'],
                        'fontSize': 13,
                        'fontWeight': 'normal',
                        'fontFamily': 'Inter, -apple-system, sans-serif',
                        'fontStyle': 'normal',
                        'lineHeight': 1.4,
                        'underline': False,
                        'overline': False,
                        'linethrough': False,
                        'textAlign': 'left',
                        'textBackgroundColor': '',
                        'charSpacing': 0,
                        'minWidth': 20,
                        'splitByGrapheme': False,
                        'objectType': 'freeText',
                        'selectable': True,
                        'evented': True,
                        'hasControls': True
                    }
                ],
                'background': '#FFFFFF'
            }
            board.canvas_state = json.dumps(canvas_state)
    
    db.session.commit()
    print(f"     Added descriptions to {len(board_descriptions)} boards")
    
    # Final verification
    print(f"\n📊 Verifying Business Context data...")
    final_boards = BusinessBoard.query.filter_by(user_id=demo_user.id).all()
    final_groups = BoardGroup.query.join(BusinessBoard).filter(BusinessBoard.user_id == demo_user.id).all()
    final_resources = BoardResource.query.join(BusinessBoard).filter(BusinessBoard.user_id == demo_user.id).all()
    
    print(f"\n✅ Business Context seeding completed!")
    print(f"   Boards created: {boards_created}")
    print(f"   Groups created: {groups_created}")
    print(f"   Resources placed: {resources_placed}")
    print(f"   Notes added: {len([r for r in Resource.query.join(CloudProvider).filter(CloudProvider.user_id == demo_user.id).all() if r.notes])}")
    print(f"\n🔍 Database verification:")
    print(f"   Boards in DB: {len(final_boards)}")
    if len(final_boards) > 0:
        for board in final_boards:
            print(f"      - {board.name} (ID: {board.id}, default: {board.is_default})")
    print(f"   Groups in DB: {len(final_groups)}")
    print(f"   Resources in DB: {len(final_resources)}")

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
            
            # Generate usage data tags for resources
            seed_usage_data_tags(demo_user, providers)
            
            # Create business context boards
            try:
                seed_business_context(demo_user, providers)
            except Exception as bc_error:
                print(f"\n⚠️  WARNING: Business Context seeding failed: {bc_error}")
                import traceback
                traceback.print_exc()
                print("Continuing with remaining seeding steps...")
            
            print("\n" + "="*60)
            print("🎉 COMPLETE! Demo user fully seeded with 3-month history, usage data, and business context boards!")
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ Error seeding demo user: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    main()

