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
from app.core.models.recommendations import OptimizationRecommendation
from app.core.models.tags import ResourceTag
from app.core.models.metrics import ResourceMetric, ResourceUsageSummary
from app.core.models.logs import ResourceLog, ResourceComponent
from app.core.models.costs import CostAllocation, CostTrend

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
            # Delete dependent snapshots and states
            snapshot_ids = [s.id for s in SyncSnapshot.query.filter(SyncSnapshot.provider_id.in_(provider_ids)).all()]
            if snapshot_ids:
                ResourceState.query.filter(ResourceState.sync_snapshot_id.in_(snapshot_ids)).delete(synchronize_session=False)
                db.session.commit()
                SyncSnapshot.query.filter(SyncSnapshot.id.in_(snapshot_ids)).delete(synchronize_session=False)
                db.session.commit()
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
        role='user',
        is_active=True,
        is_verified=True,
        timezone='Europe/Moscow',
        currency='RUB',
        language='ru',
        created_by_admin=True,
        admin_notes='Demo user for testing and demonstrations. Do not delete.'
    )
    
    # Set a password for demo user (same as username for simplicity)
    demo_user.set_password('demo')
    
    db.session.add(demo_user)
    db.session.commit()
    
    print(f"✅ Demo user created (ID: {demo_user.id})")
    
    # Create Beget provider
    print("🔄 Creating Beget provider connection...")
    beget_provider = CloudProvider(
        user_id=demo_user.id,
        provider_type='beget',
        connection_name='Beget VPS Demo',
        account_id='demo_beget',
        api_endpoint=None,
        credentials=json.dumps({
            'login': 'demo_beget',
            'password': '***DEMO***'
        }),
        is_active=True,
        last_sync=datetime.now() - timedelta(hours=2),
        sync_status='success',
        auto_sync=True,
        sync_interval='daily'
    )
    db.session.add(beget_provider)
    db.session.commit()
    
    print(f"✅ Beget provider created (ID: {beget_provider.id})")
    
    # Create Selectel provider
    print("🔄 Creating Selectel provider connection...")
    selectel_provider = CloudProvider(
        user_id=demo_user.id,
        provider_type='selectel',
        connection_name='Selectel Cloud Demo',
        account_id='demo_selectel_123',
        api_endpoint=None,
        credentials=json.dumps({
            'account_id': 'demo_selectel_123',
            'api_token': '***DEMO***'
        }),
        is_active=True,
        last_sync=datetime.now() - timedelta(hours=1),
        sync_status='success',
        auto_sync=True,
        sync_interval='daily'
    )
    db.session.add(selectel_provider)
    db.session.commit()
    
    print(f"✅ Selectel provider created (ID: {selectel_provider.id})")
    
    # Create sync snapshots for Beget
    print("🔄 Creating sync snapshots...")
    beget_snapshot = SyncSnapshot(
        provider_id=beget_provider.id,
        sync_type='full',
        sync_status='success',
        sync_started_at=datetime.now() - timedelta(hours=2, minutes=5),
        sync_completed_at=datetime.now() - timedelta(hours=2),
        total_resources_found=5,
        resources_created=5,
        resources_updated=0,
        resources_deleted=0,
        resources_unchanged=0,
        total_monthly_cost=660.0
    )
    db.session.add(beget_snapshot)
    
    # Create sync snapshot for Selectel
    selectel_snapshot = SyncSnapshot(
        provider_id=selectel_provider.id,
        sync_type='full',
        sync_status='success',
        sync_started_at=datetime.now() - timedelta(hours=1, minutes=3),
        sync_completed_at=datetime.now() - timedelta(hours=1),
        total_resources_found=4,
        resources_created=4,
        resources_updated=0,
        resources_deleted=0,
        resources_unchanged=0,
        total_monthly_cost=57450.0
    )
    db.session.add(selectel_snapshot)
    db.session.commit()
    
    print("✅ Sync snapshots created")
    
    # Create Beget resources
    print("🔄 Creating Beget resources...")
    
    beget_resources = [
        Resource(
            provider_id=beget_provider.id,
            resource_id='beget-vps-web-production',
            resource_type='server',
            resource_name='vps-web-production',
            region='ru-msk',
            status='active',
            service_name='VPS',
            effective_cost=660.0,
            currency='RUB',
            billing_period='monthly',
            provider_config=json.dumps({
                'cpu': '4 vCPU',
                'memory': '8 GB',
                'storage': '100 GB SSD',
                'ip': '185.104.114.123',
                'os': 'Ubuntu 22.04'
            })
        ),
        Resource(
            provider_id=beget_provider.id,
            resource_id='beget-domain-infrazen-demo-ru',
            resource_type='domain',
            resource_name='infrazen-demo.ru',
            region='global',
            status='active',
            service_name='Domains',
            effective_cost=50.0,
            currency='RUB',
            billing_period='monthly',
            provider_config=json.dumps({
                'registrar': 'beget',
                'expiry_date': '2026-03-15',
                'dns_records': 5
            })
        ),
        Resource(
            provider_id=beget_provider.id,
            resource_id='beget-db-mysql-prod',
            resource_type='database',
            resource_name='mysql-prod-db',
            region='ru-msk',
            status='active',
            service_name='MySQL Database',
            effective_cost=0.0,  # Included in VPS
            currency='RUB',
            billing_period='monthly',
            provider_config=json.dumps({
                'engine': 'MySQL 8.0',
                'size': '15 GB',
                'connections': 50
            })
        )
    ]
    
    for resource in beget_resources:
        db.session.add(resource)
    db.session.commit()

    # Add tags for Beget resources
    try:
        beget_server = Resource.query.filter_by(provider_id=beget_provider.id, resource_name='vps-web-production').first()
        if beget_server:
            beget_server.add_tag('env', 'production')
            beget_server.add_tag('app', 'web')
        beget_domain = Resource.query.filter_by(provider_id=beget_provider.id, resource_name='infrazen-demo.ru').first()
        if beget_domain:
            beget_domain.add_tag('type', 'primary')
        beget_db = Resource.query.filter_by(provider_id=beget_provider.id, resource_name='mysql-prod-db').first()
        if beget_db:
            beget_db.add_tag('env', 'production')
        db.session.commit()
    except Exception:
        db.session.rollback()
    print(f"✅ Created {len(beget_resources)} Beget resources")
    
    # Create Selectel resources
    print("🔄 Creating Selectel resources...")
    
    selectel_resources = [
        Resource(
            provider_id=selectel_provider.id,
            resource_id='sel-server-api-backend-prod-01',
            resource_type='server',
            resource_name='api-backend-prod-01',
            region='ru-1',
            status='active',
            service_name='Cloud Servers',
            effective_cost=28500.0,
            currency='RUB',
            billing_period='monthly',
            provider_config=json.dumps({
                'cpu': '8 vCPU',
                'memory': '32 GB',
                'storage': '200 GB NVMe',
                'flavor': 'SL1.4XL',
                'ip': '92.223.65.45',
                'os': 'Debian 11'
            })
        ),
        Resource(
            provider_id=selectel_provider.id,
            resource_id='sel-server-db-postgres-prod-01',
            resource_type='server',
            resource_name='db-postgres-prod-01',
            region='ru-2',
            status='active',
            service_name='Cloud Servers',
            effective_cost=22950.0,
            currency='RUB',
            billing_period='monthly',
            provider_config=json.dumps({
                'cpu': '8 vCPU',
                'memory': '64 GB',
                'storage': '500 GB SSD',
                'flavor': 'SL1.MEM.4XL',
                'ip': '92.223.66.78',
                'os': 'Ubuntu 22.04'
            })
        ),
        Resource(
            provider_id=selectel_provider.id,
            resource_id='sel-volume-postgres-data-01',
            resource_type='volume',
            resource_name='postgres-data-volume',
            region='ru-2',
            status='active',
            service_name='Block Storage',
            effective_cost=4000.0,
            currency='RUB',
            billing_period='monthly',
            provider_config=json.dumps({
                'size': '500 GB',
                'type': 'SSD',
                'attached_to': 'db-postgres-prod-01'
            })
        ),
        Resource(
            provider_id=selectel_provider.id,
            resource_id='sel-fs-cdn-static-assets',
            resource_type='file_storage',
            resource_name='cdn-static-assets',
            region='ru-1',
            status='active',
            service_name='S3 Object Storage',
            effective_cost=2000.0,
            currency='RUB',
            billing_period='monthly',
            provider_config=json.dumps({
                'size': '250 GB',
                'objects': 15000,
                'traffic': '1.5 TB/month'
            })
        )
    ]
    
    for resource in selectel_resources:
        db.session.add(resource)
    db.session.commit()

    # Add tags for Selectel resources
    try:
        api_srv = Resource.query.filter_by(provider_id=selectel_provider.id, resource_name='api-backend-prod-01').first()
        if api_srv:
            api_srv.add_tag('env', 'production')
            api_srv.add_tag('tier', 'api')
        db_srv = Resource.query.filter_by(provider_id=selectel_provider.id, resource_name='db-postgres-prod-01').first()
        if db_srv:
            db_srv.add_tag('env', 'production')
            db_srv.add_tag('tier', 'database')
        vol = Resource.query.filter_by(provider_id=selectel_provider.id, resource_name='postgres-data-volume').first()
        if vol:
            vol.add_tag('type', 'storage')
        s3 = Resource.query.filter_by(provider_id=selectel_provider.id, resource_name='cdn-static-assets').first()
        if s3:
            s3.add_tag('type', 'cdn')
            s3.add_tag('public', 'true')
        db.session.commit()
    except Exception:
        db.session.rollback()
    print(f"✅ Created {len(selectel_resources)} Selectel resources")
    
    # Create recommendations
    print("🔄 Creating cost optimization recommendations...")
    
    # Lookup created resources for FKs
    api_srv = Resource.query.filter_by(provider_id=selectel_provider.id, resource_name='api-backend-prod-01').first()
    db_srv = Resource.query.filter_by(provider_id=selectel_provider.id, resource_name='db-postgres-prod-01').first()
    beget_server = Resource.query.filter_by(provider_id=beget_provider.id, resource_name='vps-web-production').first()

    recommendations = [
        OptimizationRecommendation(
            resource_id=api_srv.id if api_srv else None,
            provider_id=selectel_provider.id,
            recommendation_type='rightsizing',
            category='cost',
            severity='high',
            title='Optimize api-backend-prod-01 instance size',
            description='CPU utilization averages 32% over the past 30 days. Consider downsizing from 8 vCPU to 4 vCPU.',
            estimated_monthly_savings=12000.0,
            currency='RUB',
            confidence_score=0.85,
            resource_type='server',
            resource_name='api-backend-prod-01',
            metrics_snapshot=json.dumps({'cpu_avg': 0.32}),
            insights=json.dumps({'source': 'seed'}),
            status='pending'
        ),
        OptimizationRecommendation(
            resource_id=beget_server.id if beget_server else None,
            provider_id=beget_provider.id,
            recommendation_type='reserved_instances',
            category='cost',
            severity='medium',
            title='Consider annual VPS plan for cost savings',
            description='Switch to annual billing to save approximately 20% on VPS hosting costs.',
            estimated_monthly_savings=132.0,
            currency='RUB',
            confidence_score=0.9,
            resource_type='server',
            resource_name='vps-web-production',
            metrics_snapshot=json.dumps({'plan': 'monthly'}),
            insights=json.dumps({'note': 'demo'}),
            status='pending'
        )
    ]
    
    for rec in recommendations:
        db.session.add(rec)
    
    db.session.commit()
    print(f"✅ Created {len(recommendations)} recommendations")
    
    # Summary
    print("\n" + "="*60)
    print("✅ Demo user seeding completed successfully!")
    print("="*60)
    print(f"Demo User ID: {demo_user.id}")
    print(f"Email: {demo_user.email}")
    print(f"Password: demo")
    print(f"\nProviders: 2 (Beget, Selectel)")
    print(f"Resources: {len(beget_resources) + len(selectel_resources)}")
    print(f"Recommendations: {len(recommendations)}")
    print(f"Total Monthly Cost: ₽{660 + 57450:,}")
    print("="*60)
    
    return demo_user

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
            seed_demo_user()
        except Exception as e:
            print(f"\n❌ Error seeding demo user: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    main()

