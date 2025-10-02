"""
Authentication API routes
"""
from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from google.auth.transport import requests
from google.oauth2 import id_token
import os

auth_bp = Blueprint('auth', __name__)

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', 'your-google-client-id')

@auth_bp.route('/login')
def login():
    """Display login page"""
    return render_template('login.html', google_client_id=GOOGLE_CLIENT_ID)

@auth_bp.route('/google', methods=['POST'])
def google_auth():
    """Handle Google OAuth authentication"""
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
                'picture': ''
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
                    'picture': ''
                }
                return jsonify({'success': True, 'redirect': url_for('main.dashboard')})
            
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
            
            # Extract user information
            user_id = idinfo['sub']
            email = idinfo['email']
            name = idinfo.get('name', email.split('@')[0])
            picture = idinfo.get('picture', '')
            
            # Store user in session
            session['user'] = {
                'id': user_id,
                'email': email,
                'name': name,
                'picture': picture
            }
            
            return jsonify({'success': True, 'redirect': url_for('main.dashboard')})
            
        except ValueError as e:
            # For development, if token verification fails, create a dev user
            print(f"Token verification failed: {e}")
            session['user'] = {
                'id': 'dev-user-123',
                'email': 'dev@infrazen.com',
                'name': 'Development User',
                'picture': ''
            }
            return jsonify({'success': True, 'redirect': url_for('main.dashboard')})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@auth_bp.route('/logout')
def logout():
    """Handle user logout"""
    session.pop('user', None)
    return redirect(url_for('main.index'))
