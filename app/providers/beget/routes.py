"""
Beget provider routes
"""
from flask import Blueprint, request, jsonify, session, redirect, url_for, flash
from app.core.database import db
from app.core.models.provider import CloudProvider
from app.providers.beget.client import BegetAPIClient
import json

beget_bp = Blueprint('beget', __name__)

@beget_bp.route('/')
def index():
    return "Beget Provider API"

@beget_bp.route('/add', methods=['POST'])
def add_connection():
    """Add a new Beget connection"""
    try:
        # Check if user is authenticated
        if 'user' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        user_id = session['user']['id']
        
        # Get form data
        connection_name = request.form.get('connection_name')
        username = request.form.get('username')
        password = request.form.get('password')
        api_url = 'https://api.beget.com'  # Fixed API URL for Beget
        auto_sync = request.form.get('auto_sync') == 'on'
        sync_interval = request.form.get('sync_interval', 'daily')
        
        if not all([connection_name, username, password]):
            flash('Missing required fields', 'error')
            return redirect(url_for('main.connections'))
        
        # Test connection first
        client = BegetAPIClient(username, password, api_url)
        test_result = client.test_connection()
        
        if test_result['status'] != 'success':
            flash(f'Connection test failed: {test_result["message"]}', 'error')
            return redirect(url_for('main.connections'))
        
        # Create new provider connection
        provider = CloudProvider(
            user_id=user_id,
            provider_type='beget',
            connection_name=connection_name,
            account_id=username,
            credentials=json.dumps({
                'username': username,
                'password': password,  # Store in plain text for API access
                'api_url': api_url
            }),
            provider_metadata=json.dumps(test_result.get('account_info', {})),
            is_active=True,
            auto_sync=auto_sync,
            sync_interval=sync_interval
        )
        
        db.session.add(provider)
        db.session.commit()
        
        flash('Beget connection added successfully', 'success')
        return redirect(url_for('main.connections'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding connection: {str(e)}', 'error')
        return redirect(url_for('main.connections'))

@beget_bp.route('/test', methods=['POST'])
def test_connection():
    """Test Beget API connection"""
    try:
        username = request.json.get('username')
        password = request.json.get('password')
        api_url = 'https://api.beget.com'  # Fixed API URL for Beget
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password required'}), 400
        
        client = BegetAPIClient(username, password, api_url)
        result = client.test_connection()
        
        # Return in the old format that JavaScript expects
        if result.get('status') == 'success':
            return jsonify({
                'success': True,
                'message': result.get('message', 'Connection test successful'),
                'account_info': result.get('account_info', {})
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('message', 'Connection test failed')
            })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@beget_bp.route('/<int:provider_id>/edit', methods=['GET', 'POST'])
def edit_connection(provider_id):
    """Edit Beget connection"""
    try:
        if 'user' not in session:
            return redirect(url_for('auth.login'))
        
        user_id = session['user']['id']
        provider = CloudProvider.query.filter_by(id=provider_id, user_id=user_id, provider_type='beget').first()
        
        if not provider:
            flash('Connection not found', 'error')
            return redirect(url_for('main.connections'))
        
        if request.method == 'POST':
            # Update connection
            connection_name = request.form.get('connection_name')
            username = request.form.get('username')
            password = request.form.get('password')
            api_url = 'https://api.beget.com'  # Fixed API URL for Beget
            auto_sync = request.form.get('auto_sync') == 'on'
            sync_interval = request.form.get('sync_interval', 'daily')
            
            if not all([connection_name, username, password]):
                flash('All fields are required', 'error')
                return redirect(url_for('beget.edit_connection', provider_id=provider_id))
            
            # Test connection first
            client = BegetAPIClient(username, password, api_url)
            test_result = client.test_connection()
            
            if test_result['status'] != 'success':
                flash(f'Connection test failed: {test_result["message"]}', 'error')
                return redirect(url_for('beget.edit_connection', provider_id=provider_id))
            
            # Update provider
            provider.connection_name = connection_name
            provider.account_id = username
            provider.credentials = json.dumps({
                'username': username,
                'password': password,
                'api_url': api_url
            })
            provider.provider_metadata = json.dumps(test_result.get('account_info', {}))
            provider.auto_sync = auto_sync
            provider.sync_interval = sync_interval
            
            db.session.commit()
            flash('Connection updated successfully', 'success')
            return redirect(url_for('main.connections'))
        
        # GET request - show edit form
        credentials = json.loads(provider.credentials) if provider.credentials else {}
        
        return jsonify({
            'success': True,
            'data': {
                'id': provider.id,
                'provider': 'beget',
                'connection_name': provider.connection_name,
                'username': credentials.get('username', ''),
                'password': credentials.get('password', ''),  # Include password for testing
                'auto_sync': provider.auto_sync,
                'sync_interval': provider.sync_interval
            }
        })
        
    except Exception as e:
        flash(f'Error updating connection: {str(e)}', 'error')
        return redirect(url_for('main.connections'))

@beget_bp.route('/<int:provider_id>/sync', methods=['POST'])
def sync_connection(provider_id):
    """Sync Beget connection"""
    try:
        if 'user' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        user_id = session['user']['id']
        provider = CloudProvider.query.filter_by(id=provider_id, user_id=user_id, provider_type='beget').first()
        
        if not provider:
            return jsonify({'success': False, 'error': 'Connection not found'}), 404
        
        # Get credentials
        credentials = json.loads(provider.credentials) if provider.credentials else {}
        username = credentials.get('username')
        password = credentials.get('password')
        api_url = credentials.get('api_url', 'https://api.beget.com')
        
        # Test connection
        client = BegetAPIClient(username, password, api_url)
        test_result = client.test_connection()
        
        if test_result['status'] != 'success':
            return jsonify({'success': False, 'error': test_result['message']}), 400
        
        # Update sync status
        provider.last_sync = db.func.now()
        provider.sync_status = 'success'
        provider.sync_error = None
        provider.provider_metadata = json.dumps(test_result.get('account_info', {}))
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Connection synced successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@beget_bp.route('/<int:provider_id>/delete', methods=['DELETE'])
def delete_connection(provider_id):
    """Delete Beget connection"""
    try:
        if 'user' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        user_id = session['user']['id']
        provider = CloudProvider.query.filter_by(id=provider_id, user_id=user_id, provider_type='beget').first()
        
        if not provider:
            return jsonify({'success': False, 'error': 'Connection not found'}), 404
        
        db.session.delete(provider)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Connection deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
