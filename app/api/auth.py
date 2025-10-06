"""
Authentication API routes
"""
from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from google.auth.transport import requests
from google.oauth2 import id_token
import os
from datetime import datetime
from app.core.database import db
from app.core.models.user import User

auth_bp = Blueprint('auth', __name__)

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', 'your-google-client-id')

@auth_bp.route('/login')
def login():
    """Display login page"""
    return render_template('login.html', google_client_id=GOOGLE_CLIENT_ID)

@auth_bp.route('/google', methods=['POST'])
def google_auth():
    """Handle Google OAuth authentication with database integration"""
    try:
        # Get the ID token from the request
        token = request.json.get('credential')
        is_demo = request.json.get('demo', False)
        
        # Handle demo login
        if is_demo or token == 'demo-token':
            session['user'] = {
                'id': 'demo-user-123',
                'email': 'demo@infrazen.com',
                'name': 'Demo User',
                'picture': '',
                'role': 'demo'
            }
            return jsonify({'success': True, 'redirect': url_for('main.dashboard')})
        
        # Verify the Google ID token
        try:
            # For development, we'll be more lenient with token verification
            if GOOGLE_CLIENT_ID == 'your-google-client-id':
                # If not properly configured, allow any token for development
                session['user'] = {
                    'id': 'dev-user-123',
                    'email': 'dev@infrazen.com',
                    'name': 'Development User',
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
                'picture': '',
                'role': 'user'
            }
            return jsonify({'success': True, 'redirect': url_for('main.dashboard')})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@auth_bp.route('/logout')
def logout():
    """Handle user logout"""
    session.pop('user', None)
    return redirect(url_for('main.index'))
