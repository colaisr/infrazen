"""
Authentication API routes
"""
from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps
from google.auth.transport import requests
from google.oauth2 import id_token
import os
import time
from datetime import datetime
from app.core.database import db
from app.core.models.user import User

auth_bp = Blueprint('auth', __name__)

# Google OAuth configuration will be accessed from app config

def validate_session(f):
    """Decorator to validate user session and ensure user exists in database"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_data = session.get('user')
        if not user_data:
            return jsonify({'success': False, 'error': 'Not authenticated', 'redirect': '/api/auth/login'}), 401
        
        # Skip validation for demo users (they don't have db_id)
        if user_data.get('id') == 'demo-user-123' or user_data.get('id') == 'dev-user-123':
            return f(*args, **kwargs)
        
        # Get user ID from session for real users
        user_id = user_data.get('db_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Invalid session', 'redirect': '/api/auth/login'}), 401
        
        # Check if user still exists in database
        user = User.find_by_id(user_id)
        if not user:
            # User no longer exists - clear session and redirect to login
            session.clear()
            return jsonify({'success': False, 'error': 'User account no longer exists', 'redirect': '/api/auth/login'}), 401
        
        # Check if user is still active
        if not user.is_active:
            session.clear()
            return jsonify({'success': False, 'error': 'Account is deactivated', 'redirect': '/api/auth/login'}), 401
        
        # Update session with current user data
        session['user'].update({
            'email': user.email,
            'name': f"{user.first_name} {user.last_name}".strip() or user.email.split('@')[0],
            'initials': user.get_initials(),
            'role': user.role,
            'is_admin': user.is_admin(),
            'permissions': user.get_permissions()
        })
        
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login')
def login():
    """Display login page"""
    return render_template('login.html', google_client_id=current_app.config.get('GOOGLE_CLIENT_ID'))

@auth_bp.route('/google', methods=['POST'])
def google_auth():
    """Handle Google OAuth authentication with database integration"""
    try:
        # Get the ID token from the request
        token = request.json.get('credential')
        is_demo = request.json.get('demo', False)
        
        # Handle demo login
        if is_demo or token == 'demo-token':
            # Ensure a real DB-backed demo user exists and log in as that user
            demo_email = 'demo@infrazen.com'
            user = User.find_by_email(demo_email)
            if not user:
                # Create a minimal demo user if missing
                user = User(
                    email=demo_email,
                    first_name='Demo',
                    last_name='User',
                    role='user',
                    is_active=True,
                    is_verified=True,
                    created_by_admin=True,
                    admin_notes='Auto-created demo user'
                )
                db.session.add(user)
                db.session.commit()
                # Set a simple password for completeness
                try:
                    user.set_password('demo')
                except Exception:
                    pass
            # Update login info and store full session with db_id to make pages use real DB flow
            user.update_login_info()
            session['user'] = {
                'id': str(user.id),
                'db_id': user.id,
                'google_id': user.google_id,
                'email': user.email,
                'name': f"{user.first_name} {user.last_name}".strip() or user.email.split('@')[0],
                'initials': user.get_initials(),
                'picture': user.google_picture or '',
                'role': user.role,
                'is_admin': True,  # keep admin capabilities for demo walkthrough
                'permissions': {
                    'manage_users': True,
                    'impersonate_users': True,
                    'view_all_data': True,
                    'manage_providers': True,
                    'manage_resources': True
                }
            }
            return jsonify({'success': True, 'redirect': url_for('main.dashboard')})
        
        # Verify the Google ID token
        try:
            # For development, we'll be more lenient with token verification
            GOOGLE_CLIENT_ID = current_app.config.get('GOOGLE_CLIENT_ID')
            if GOOGLE_CLIENT_ID == 'your-google-client-id':
                # If not properly configured, allow any token for development
                session['user'] = {
                    'id': 'dev-user-123',
                    'email': 'dev@infrazen.com',
                    'name': 'Development User',
                    'initials': 'DU',
                    'picture': '',
                    'role': 'user'
                }
                return jsonify({'success': True, 'redirect': url_for('main.dashboard')})
            
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
            
            # Extract user information from Google
            google_id = idinfo['sub']
            email = idinfo['email']
            name = idinfo.get('name', email.split('@')[0])
            picture = idinfo.get('picture', '')
            
            # Check if user exists in database
            user = User.find_by_google_id(google_id)
            
            if not user:
                # Check if user exists by email (for existing users without Google ID)
                user = User.find_by_email(email)
                if user:
                    # Update existing user with Google ID
                    user.google_id = google_id
                    user.google_picture = picture
                    user.google_verified_email = idinfo.get('email_verified', False)
                    user.google_locale = idinfo.get('locale', '')
                    db.session.commit()
                else:
                    # Create new user from Google data
                    user = User.create_from_google(idinfo)
            
            # Update login information
            user.update_login_info()
            
            # Store user in session with database ID
            session['user'] = {
                'id': str(user.id),
                'db_id': user.id,
                'google_id': user.google_id,
                'email': user.email,
                'name': f"{user.first_name} {user.last_name}".strip() or user.email.split('@')[0],
                'initials': user.get_initials(),
                'picture': user.google_picture or '',
                'role': user.role,
                'is_admin': user.is_admin(),
                'permissions': user.get_permissions()
            }
            
            return jsonify({'success': True, 'redirect': url_for('main.dashboard')})
            
        except ValueError as e:
            # For development, if token verification fails, create a dev user
            print(f"Token verification failed: {e}")
            session['user'] = {
                'id': 'dev-user-123',
                'email': 'dev@infrazen.com',
                'name': 'Development User',
                'initials': 'DU',
                'picture': '',
                'role': 'user'
            }
            return jsonify({'success': True, 'redirect': url_for('main.dashboard')})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@auth_bp.route('/admin-login')
def admin_login():
    """Direct admin login for testing purposes"""
    # Get admin user from database
    admin_user = User.query.filter_by(role='super_admin').first()
    if not admin_user:
        admin_user = User.query.filter_by(role='admin').first()
    
    if admin_user:
        session['user'] = {
            'id': str(admin_user.id),
            'db_id': admin_user.id,
            'google_id': admin_user.google_id,
            'email': admin_user.email,
            'name': f"{admin_user.first_name} {admin_user.last_name}".strip() or admin_user.email.split('@')[0],
            'initials': admin_user.get_initials(),
            'picture': admin_user.google_picture or '',
            'role': admin_user.role,
            'is_admin': admin_user.is_admin(),
            'permissions': admin_user.get_permissions()
        }
        return jsonify({'success': True, 'redirect': url_for('main.dashboard')})
    else:
        return jsonify({'success': False, 'error': 'No admin user found'})

@auth_bp.route('/login-password', methods=['POST'])
def login_password():
    """Handle email/password authentication"""
    try:
        data = request.get_json()
        email = data.get('username', '').strip()  # Frontend sends email in 'username' field
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'success': False, 'error': 'Email и пароль обязательны'})
        
        # Find user by email (username field contains email)
        user = User.find_by_email(email)
        
        if not user:
            return jsonify({'success': False, 'error': 'Неверный email или пароль'})
        
        # Check if user can login with password
        if not user.can_login_with_password():
            return jsonify({'success': False, 'error': 'Password login not available for this account'})
        
        # Verify password
        if not user.check_password(password):
            return jsonify({'success': False, 'error': 'Неверный email или пароль'})
        
        # Update login information
        user.update_login_info()
        
        # Store user in session
        session['user'] = {
            'id': str(user.id),
            'db_id': user.id,
            'google_id': user.google_id,
            'email': user.email,
            'name': f"{user.first_name} {user.last_name}".strip() or user.email.split('@')[0],
            'initials': user.get_initials(),
            'picture': user.google_picture or '',
            'role': user.role,
            'is_admin': user.is_admin(),
            'permissions': user.get_permissions(),
            'login_method': 'password'
        }
        
        return jsonify({'success': True, 'redirect': url_for('main.dashboard')})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@auth_bp.route('/me')
def current_user():
    """Get current user session info"""
    user = session.get('user', {})
    return jsonify({
        'authenticated': bool(user),
        'user': user,
        'is_admin': user.get('is_admin', False) if user else False
    })

@auth_bp.route('/set-password', methods=['POST'])
def set_password():
    """Set password for current user"""
    try:
        # Check if user is logged in
        user_data = session.get('user')
        if not user_data:
            return jsonify({'success': False, 'error': 'Not authenticated'})
        
        data = request.get_json()
        password = data.get('password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()
        
        if not password or not confirm_password:
            return jsonify({'success': False, 'error': 'Password and confirmation are required'})
        
        if password != confirm_password:
            return jsonify({'success': False, 'error': 'Passwords do not match'})
        
        if len(password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters'})
        
        # Get user from database
        user = User.find_by_id(user_data.get('db_id'))
        if not user:
            return jsonify({'success': False, 'error': 'User not found'})
        
        # Set password
        user.set_password(password)
        
        return jsonify({'success': True, 'message': 'Password set successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """Change password for current user (requires current password)"""
    try:
        # Check if user is logged in
        user_data = session.get('user')
        if not user_data:
            return jsonify({'success': False, 'error': 'Not authenticated'})
        
        data = request.get_json()
        current_password = data.get('current_password', '').strip()
        new_password = data.get('password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()
        
        if not current_password or not new_password or not confirm_password:
            return jsonify({'success': False, 'error': 'All fields are required'})
        
        if new_password != confirm_password:
            return jsonify({'success': False, 'error': 'Passwords do not match'})
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters'})
        
        # Get user from database
        user = User.find_by_id(user_data.get('db_id'))
        if not user:
            return jsonify({'success': False, 'error': 'User not found'})
        
        # Check current password
        if not user.check_password(current_password):
            return jsonify({'success': False, 'error': 'Current password is incorrect'})
        
        # Set new password
        user.set_password(new_password)
        
        return jsonify({'success': True, 'message': 'Password changed successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@auth_bp.route('/user-details')
@validate_session
def user_details():
    """Get detailed user information for settings page"""
    try:
        # Get user from database (already validated by decorator)
        user_data = session.get('user')
        user = User.find_by_id(user_data.get('db_id'))
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'name': f"{user.first_name} {user.last_name}".strip() or user.email.split('@')[0],
                'initials': user.get_initials(),
                'company': user.company,
                'role': user.role,
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'login_count': user.login_count,
                'google_id': user.google_id,
                'google_picture': user.google_picture,
                'has_password': user.has_password(),
                'can_login_with_password': user.can_login_with_password(),
                'can_login_with_google': user.can_login_with_google(),
                'current_login_method': user_data.get('login_method', 'unknown'),
                'timezone': user.timezone,
                'currency': user.currency,
                'language': user.language
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@auth_bp.route('/register')
def register():
    """Display registration page"""
    return render_template('register.html', google_client_id=current_app.config.get('GOOGLE_CLIENT_ID'))

@auth_bp.route('/register', methods=['POST'])
def handle_register():
    """Handle user registration"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        
        # No username needed - email is the primary identifier
        
        # Validation
        if not email or not password:
            return jsonify({'success': False, 'error': 'Email и пароль обязательны для заполнения'})
        
        if password != confirm_password:
            return jsonify({'success': False, 'error': 'Пароли не совпадают'})
        
        if len(password) < 6:
            return jsonify({'success': False, 'error': 'Пароль должен содержать минимум 6 символов'})
        
        # Check if user already exists
        if User.find_by_email(email):
            return jsonify({'success': False, 'error': 'Пользователь с таким email уже существует'})
        
        # Create new user
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role='user',
            is_active=True,
            is_verified=False  # Will need email verification in production
        )
        
        # Set password
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Automatically log the user in after successful registration
        session['user'] = {
            'id': str(user.id),
            'db_id': user.id,
            'email': user.email,
            'name': f"{user.first_name} {user.last_name}".strip() or user.email.split('@')[0],
            'initials': user.get_initials(),
            'picture': '',
            'role': user.role,
            'is_admin': user.is_admin(),
            'permissions': user.get_permissions(),
            'login_method': 'registration'
        }
        
        return jsonify({
            'success': True, 
            'message': 'Регистрация прошла успешно! Вы автоматически вошли в систему.',
            'redirect': '/dashboard'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@auth_bp.route('/connect-google')
def connect_google():
    """Redirect to Google OAuth for account linking"""
    # This is a fallback if the JavaScript Google API doesn't work
    # In a real implementation, you'd redirect to Google's OAuth endpoint
    return jsonify({'success': False, 'error': 'Please use the clickable Google OAuth card in settings'})

@auth_bp.route('/link-google', methods=['POST'])
@validate_session
def link_google_account():
    """Link Google account to existing user"""
    try:
        data = request.get_json()
        credential = data.get('credential')
        
        if not credential:
            return jsonify({'success': False, 'error': 'No credential provided'})
        
        # Get current user
        user_data = session.get('user')
        user = User.find_by_id(user_data.get('db_id'))
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found'})
        
        # Check if user already has Google connected
        if user.google_id:
            return jsonify({'success': False, 'error': 'Google account is already connected'})
        
        # Verify the Google credential using the same method as login
        try:
            GOOGLE_CLIENT_ID = current_app.config.get('GOOGLE_CLIENT_ID')
            if not GOOGLE_CLIENT_ID or GOOGLE_CLIENT_ID == 'your-google-client-id':
                # For development, allow any token (same as login behavior)
                # This matches the behavior in the login function
                idinfo = {
                    'sub': f'google-{user.id}-{int(time.time())}',
                    'email': user.email,  # Use the same email as user account
                    'given_name': user.first_name or 'User',
                    'family_name': user.last_name or '',
                    'picture': '',
                    'email_verified': True,
                    'locale': 'en'
                }
            else:
                # Production: verify real Google token
                from google.oauth2 import id_token
                from google.auth.transport import requests
                idinfo = id_token.verify_oauth2_token(credential, requests.Request(), GOOGLE_CLIENT_ID)
            
            # Verify email matches
            if idinfo.get('email') != user.email:
                return jsonify({'success': False, 'error': 'Google account email does not match your account email'})
            
            # Update user with Google information
            user.google_id = idinfo.get('sub')
            user.google_picture = idinfo.get('picture', '')
            user.google_verified_email = idinfo.get('email_verified', False)
            user.google_locale = idinfo.get('locale', '')
            
            # Update first/last name if not set
            if not user.first_name and idinfo.get('given_name'):
                user.first_name = idinfo.get('given_name')
            if not user.last_name and idinfo.get('family_name'):
                user.last_name = idinfo.get('family_name')
            
            # Update is_verified based on Google verification
            if idinfo.get('email_verified'):
                user.is_verified = True
            
            db.session.commit()
            
            # Update session with new Google data
            session['user'].update({
                'google_id': user.google_id,
                'picture': user.google_picture or '',
                'initials': user.get_initials()
            })
            
            return jsonify({
                'success': True, 
                'message': 'Google account linked successfully!'
            })
            
        except ValueError as e:
            print(f"Google token verification failed: {e}")
            return jsonify({'success': False, 'error': 'Invalid Google credential'})
        
    except Exception as e:
        print(f"Error linking Google account: {e}")
        return jsonify({'success': False, 'error': str(e)})

@auth_bp.route('/logout')
def logout():
    """Handle user logout"""
    session.pop('user', None)
    return redirect(url_for('main.index'))
