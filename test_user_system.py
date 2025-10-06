#!/usr/bin/env python3
"""
Test script for the new user system
"""
import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.core.database import db
from app.core.models.user import User

def test_user_system():
    """Test the enhanced user system"""
    app = create_app()
    
    with app.app_context():
        print("🧪 Testing InfraZen User System")
        print("=" * 50)
        
        try:
            # Test 1: Create a test user
            print("\n1. Testing user creation...")
            test_user = User(
                email='test@infrazen.com',
                username='testuser',
                first_name='Test',
                last_name='User',
                role='user',
                is_active=True
            )
            db.session.add(test_user)
            db.session.commit()
            print(f"✅ Created user: {test_user.email}")
            
            # Test 2: Test Google OAuth user creation
            print("\n2. Testing Google OAuth user creation...")
            google_data = {
                'sub': 'google-123456789',
                'email': 'google@infrazen.com',
                'given_name': 'Google',
                'family_name': 'User',
                'picture': 'https://example.com/avatar.jpg',
                'email_verified': True,
                'locale': 'en'
            }
            
            google_user = User.create_from_google(google_data)
            print(f"✅ Created Google user: {google_user.email}")
            print(f"   Google ID: {google_user.google_id}")
            print(f"   Picture: {google_user.google_picture}")
            
            # Test 3: Test role and permissions
            print("\n3. Testing role and permissions...")
            admin_user = User(
                email='admin@infrazen.com',
                username='admin',
                first_name='Admin',
                last_name='User',
                role='admin',
                is_active=True
            )
            
            # Set admin permissions
            admin_permissions = {
                'manage_users': True,
                'impersonate_users': True,
                'view_all_data': True
            }
            admin_user.set_permissions(admin_permissions)
            
            db.session.add(admin_user)
            db.session.commit()
            
            print(f"✅ Created admin user: {admin_user.email}")
            print(f"   Role: {admin_user.role}")
            print(f"   Is Admin: {admin_user.is_admin()}")
            print(f"   Can Impersonate: {admin_user.can_impersonate()}")
            print(f"   Permissions: {admin_user.get_permissions()}")
            
            # Test 4: Test user queries
            print("\n4. Testing user queries...")
            all_users = User.query.all()
            print(f"✅ Total users: {len(all_users)}")
            
            admin_users = User.query.filter(User.role.in_(['admin', 'super_admin'])).all()
            print(f"✅ Admin users: {len(admin_users)}")
            
            google_users = User.query.filter(User.google_id.isnot(None)).all()
            print(f"✅ Google OAuth users: {len(google_users)}")
            
            # Test 5: Test user methods
            print("\n5. Testing user methods...")
            user = User.find_by_email('test@infrazen.com')
            if user:
                print(f"✅ Found user by email: {user.email}")
                print(f"   User dict: {user.to_dict()}")
            
            google_user = User.find_by_google_id('google-123456789')
            if google_user:
                print(f"✅ Found user by Google ID: {google_user.email}")
            
            # Test 6: Test login tracking
            print("\n6. Testing login tracking...")
            user.update_login_info()
            print(f"✅ Updated login info for: {user.email}")
            print(f"   Login count: {user.login_count}")
            print(f"   Last login: {user.last_login}")
            
            # Test 7: Test user serialization
            print("\n7. Testing user serialization...")
            user_dict = user.to_dict()
            print(f"✅ User serialization:")
            for key, value in user_dict.items():
                print(f"   {key}: {value}")
            
            print("\n🎉 All tests passed successfully!")
            print("\n📊 Database Statistics:")
            print(f"   Total users: {User.query.count()}")
            
            # Show role distribution
            roles = db.session.query(User.role, db.func.count(User.id)).group_by(User.role).all()
            for role, count in roles:
                print(f"   {role}: {count}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True

if __name__ == "__main__":
    success = test_user_system()
    sys.exit(0 if success else 1)
