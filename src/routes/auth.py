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
    return render_template('login.html')

@auth_bp.route('/auth/google', methods=['POST'])
def google_auth():
    """Handle Google OAuth authentication"""
    try:
        # Get the ID token from the request
        token = request.json.get('credential')
        
        if not token:
            return jsonify({'error': 'No credential provided'}), 400
        
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            token, requests.Request(), GOOGLE_CLIENT_ID
        )
        
        # Extract user information
        user_id = idinfo['sub']
        email = idinfo['email']
        name = idinfo['name']
        picture = idinfo.get('picture', '')
        
        # Store user info in session (in a real app, you'd save to database)
        session['user'] = {
            'id': user_id,
            'email': email,
            'name': name,
            'picture': picture
        }
        
        return jsonify({
            'success': True,
            'redirect': url_for('main.dashboard')
        })
        
    except ValueError as e:
        return jsonify({'error': 'Invalid token'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout')
def logout():
    """Handle user logout"""
    session.clear()
    return redirect(url_for('main.index'))

@auth_bp.route('/profile')
def profile():
    """Get current user profile"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    return jsonify(session['user'])
