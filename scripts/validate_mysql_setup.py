#!/usr/bin/env python3
"""
Validate MySQL setup and data integrity
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def validate_mysql_setup():
    """Validate MySQL database setup"""
    print("=" * 60)
    print("MySQL Setup Validation")
    print("=" * 60)
    print()
    
    try:
        from app import create_app
        from app.core.database import db
        from app.core.models.user import User
        from app.core.models.provider import CloudProvider
        from app.core.models.resource import Resource
        from app.core.models.sync import SyncSnapshot
        from app.core.models.recommendations import OptimizationRecommendation
        from sqlalchemy import inspect
        
        app = create_app()
        
        with app.app_context():
            # Check database connection
            print("🔄 Testing database connection...")
            try:
                db.engine.connect()
                print("✅ Database connection successful")
                
                # Get database info
                db_url = str(db.engine.url)
                if 'mysql' in db_url:
                    print(f"   Database: MySQL")
                    print(f"   Host: {db.engine.url.host}")
                    print(f"   Database: {db.engine.url.database}")
                else:
                    print(f"   Database: {db_url.split('://')[0].upper()}")
                    print("   ⚠️  Warning: Not using MySQL")
            except Exception as e:
                print(f"❌ Database connection failed: {e}")
                return False
            
            print()
            
            # Check tables exist
            print("🔄 Checking database tables...")
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            required_tables = [
                'users',
                'cloud_providers',
                'resources',
                'sync_snapshots',
                'optimization_recommendations'
            ]
            
            missing_tables = []
            for table in required_tables:
                if table in tables:
                    print(f"   ✅ {table}")
                else:
                    print(f"   ❌ {table} (missing)")
                    missing_tables.append(table)
            
            if missing_tables:
                print(f"\n❌ Missing tables: {', '.join(missing_tables)}")
                print("   Run: python init_database.py")
                return False
            
            print()
            
            # Check data counts
            print("🔄 Checking data...")
            
            user_count = User.query.count()
            provider_count = CloudProvider.query.count()
            resource_count = Resource.query.count()
            snapshot_count = SyncSnapshot.query.count()
            rec_count = OptimizationRecommendation.query.count()
            
            print(f"   Users: {user_count}")
            print(f"   Cloud Providers: {provider_count}")
            print(f"   Resources: {resource_count}")
            print(f"   Sync Snapshots: {snapshot_count}")
            print(f"   Recommendations: {rec_count}")
            
            print()
            
            # Check super admin
            print("🔄 Checking super admin user...")
            super_admin = User.query.filter_by(role='super_admin').first()
            if super_admin:
                print(f"   ✅ Super admin exists: {super_admin.email}")
            else:
                print("   ⚠️  No super admin user found")
                print("   Run: python init_database.py")
            
            print()
            
            # Check demo user
            print("🔄 Checking demo user...")
            demo_user = User.query.filter_by(email='demo@infrazen.com').first()
            if demo_user:
                print(f"   ✅ Demo user exists (ID: {demo_user.id})")
                
                # Check demo user data
                demo_providers = CloudProvider.query.filter_by(user_id=demo_user.id).count()
                demo_resources = Resource.query.join(CloudProvider).filter(
                    CloudProvider.user_id == demo_user.id
                ).count()
                
                print(f"   Demo Providers: {demo_providers}")
                print(f"   Demo Resources: {demo_resources}")
                
                if demo_providers == 0:
                    print("   ⚠️  Demo user has no providers")
                    print("   Run: python scripts/seed_demo_user.py")
            else:
                print("   ⚠️  No demo user found")
                print("   Run: python scripts/seed_demo_user.py")
            
            print()
            
            # Test query performance
            print("🔄 Testing query performance...")
            import time
            
            start = time.time()
            User.query.all()
            user_time = (time.time() - start) * 1000
            
            start = time.time()
            Resource.query.all()
            resource_time = (time.time() - start) * 1000
            
            print(f"   User query: {user_time:.2f}ms")
            print(f"   Resource query: {resource_time:.2f}ms")
            
            if user_time > 1000 or resource_time > 1000:
                print("   ⚠️  Queries are slow (>1 second)")
            else:
                print("   ✅ Query performance good")
            
            print()
            print("=" * 60)
            print("✅ Validation completed successfully!")
            print("=" * 60)
            
            return True
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure all dependencies are installed")
        print("   Run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = validate_mysql_setup()
    sys.exit(0 if success else 1)

