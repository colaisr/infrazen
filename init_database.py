#!/usr/bin/env python3
"""
Initialize database with new user schema
"""
import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.core.database import db
from app.core.models.user import User

def init_database():
    """Initialize database with new schema"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔄 Initializing database...")
            
            # Create all tables
            db.create_all()
            print("✅ Database tables created successfully")
            
            # Check if we need to create a super admin user
            super_admin = User.query.filter_by(role='super_admin').first()
            
            if not super_admin:
                print("🔄 Creating super admin user...")
                
                # Create super admin user
                super_admin = User(
                    email='admin@infrazen.com',
                    username='admin',
                    first_name='Super',
                    last_name='Admin',
                    role='super_admin',
                    is_active=True,
                    is_verified=True,
                    created_by_admin=False
                )
                
                # Set admin permissions
                admin_permissions = {
                    'manage_users': True,
                    'impersonate_users': True,
                    'view_all_data': True,
                    'manage_providers': True,
                    'manage_resources': True
                }
                super_admin.set_permissions(admin_permissions)
                
                db.session.add(super_admin)
                db.session.commit()
                
                print("✅ Super admin user created:")
                print(f"   Email: {super_admin.email}")
                print(f"   Role: {super_admin.role}")
                print(f"   Permissions: {super_admin.get_permissions()}")
            else:
                print("ℹ️  Super admin user already exists")
            
            # Show database statistics
            user_count = User.query.count()
            print(f"\n📊 Database Statistics:")
            print(f"   Total users: {user_count}")
            
            # Show role distribution
            roles = db.session.query(User.role, db.func.count(User.id)).group_by(User.role).all()
            for role, count in roles:
                print(f"   {role}: {count}")
            
            print("\n🎉 Database initialization completed successfully!")
            
        except Exception as e:
            print(f"❌ Error initializing database: {e}")
            raise

if __name__ == "__main__":
    init_database()
