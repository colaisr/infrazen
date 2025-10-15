"""
Selectel provider routes
"""
from flask import Blueprint, request, jsonify, redirect, url_for, flash, render_template, session
from app.core.database import db
from app.core.models.provider import CloudProvider
from app.providers.selectel.service import SelectelService
from app.providers.selectel.client import SelectelClient
import json
import logging

logger = logging.getLogger(__name__)

# Create blueprint
selectel_bp = Blueprint('selectel', __name__)


@selectel_bp.route('/test', methods=['POST'])
def test_selectel_connection():
    """Test Selectel connection without saving"""
    try:
        # Get form data
        api_key = request.json.get('api_key') if request.is_json else request.form.get('api_key')
        service_username = request.json.get('service_username') if request.is_json else request.form.get('service_username')
        service_password = request.json.get('service_password') if request.is_json else request.form.get('service_password')
        
        # Validate required fields
        if not api_key or not service_username or not service_password:
            return jsonify({
                'success': False,
                'message': 'API Key, Service Username, and Service Password are required'
            }), 400
        
        # Test the connection
        credentials = {
            'api_key': api_key,
            'service_username': service_username,
            'service_password': service_password
        }
        test_client = SelectelClient(credentials)
        test_result = test_client.test_connection()
        
        return jsonify(test_result)
        
    except Exception as e:
        logger.error(f"Selectel connection test failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Connection test failed'
        }), 500


@selectel_bp.route('/add', methods=['POST'])
def add_connection():
    """Add a new Selectel connection"""
    try:
        # Check if user is authenticated
        if 'user' not in session:
            flash('Authentication required', 'error')
            return redirect(url_for('main.connections'))
        
        user_id = session['user']['id']
        
        # Get form data
        connection_name = request.form.get('connection_name')
        api_key = request.form.get('api_key')
        service_username = request.form.get('service_username')
        service_password = request.form.get('service_password')
        auto_sync = request.form.get('auto_sync') == 'on'
        collect_performance_stats = request.form.get('collect_performance_stats') == 'on'
        
        # Handle sync interval conversion
        sync_interval_value = request.form.get('sync_interval', 'daily')
        sync_interval_map = {
            'hourly': 3600,      # 1 hour
            'daily': 86400,      # 24 hours
            'weekly': 604800,    # 7 days
            'manual': 0          # Manual only
        }
        sync_interval = sync_interval_map.get(sync_interval_value, 86400)  # Default to daily
        
        # Validate required fields
        if not connection_name or not api_key or not service_username or not service_password:
            flash('Connection name, API key, service username, and service password are required', 'error')
            return redirect(url_for('main.connections'))
        
        # Test the connection
        credentials = {
            'api_key': api_key,
            'service_username': service_username,
            'service_password': service_password
        }
        test_client = SelectelClient(credentials)
        test_result = test_client.test_connection()
        
        if not test_result['success']:
            flash(f'Connection test failed: {test_result.get("message", "Unknown error")}', 'error')
            return redirect(url_for('main.connections'))
        
        # Extract account_id from API response
        account_id = test_result.get('account_info', {}).get('name', '')
        
        # Prepare provider metadata with settings
        provider_metadata = test_result.get('account_info', {})
        provider_metadata['collect_performance_stats'] = collect_performance_stats
        
        # Create provider record
        provider = CloudProvider(
            user_id=user_id,
            provider_type='selectel',
            connection_name=connection_name,
            account_id=account_id,
            credentials=json.dumps({
                'api_key': api_key,
                'service_username': service_username,
                'service_password': service_password
            }),
            provider_metadata=json.dumps(provider_metadata),
            is_active=True,
            auto_sync=auto_sync,
            sync_interval=sync_interval
        )
        
        db.session.add(provider)
        db.session.commit()
        
        flash('Selectel connection added successfully', 'success')
        return redirect(url_for('main.connections'))
        
    except Exception as e:
        logger.error(f"Failed to add Selectel connection: {str(e)}")
        flash(f'Failed to add connection: {str(e)}', 'error')
        return redirect(url_for('main.connections'))


@selectel_bp.route('/<int:provider_id>/sync', methods=['POST'])
def sync_resources(provider_id):
    """Manually trigger resource synchronization for a Selectel provider."""
    try:
        # Check if user is authenticated
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        user_id = session['user']['id']
        
        # Handle user ID comparison
        all_providers = CloudProvider.query.filter_by(provider_type='selectel').all()
        provider = None
        for p in all_providers:
            if p.id == provider_id and int(float(p.user_id)) == int(float(user_id)):
                provider = p
                break
        
        if not provider:
            return jsonify({'success': False, 'message': 'Provider not found'}), 404
        
        service = SelectelService(provider)
        sync_result = service.sync_resources()
        
        if sync_result.get('success'):
            return jsonify({
                'success': True,
                'message': f"Successfully synced {sync_result.get('resources_synced')} resources"
            })
        else:
            return jsonify({
                'success': False,
                'message': sync_result.get('error', 'Sync failed')
            })
            
    except Exception as e:
        logger.error(f"Error syncing Selectel resources for provider {provider_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error syncing resources: {str(e)}'
        }), 500


@selectel_bp.route('/<int:provider_id>/edit', methods=['GET'])
def edit_connection(provider_id):
    """Get Selectel provider details for editing."""
    try:
        # Check if user is authenticated
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        user_id = session['user']['id']
        
        provider = CloudProvider.query.filter_by(
            id=provider_id,
            user_id=user_id,
            provider_type='selectel'
        ).first()
        
        if not provider:
            return jsonify({'success': False, 'message': 'Provider not found'}), 404
        
        # Parse credentials and metadata
        credentials = json.loads(provider.credentials)
        provider_metadata = json.loads(provider.provider_metadata) if provider.provider_metadata else {}
        
        # Return provider data for editing
        provider_data = {
            'id': provider.id,
            'provider': 'selectel',  # Add provider type for frontend
            'connection_name': provider.connection_name,
            'account_id': provider.account_id,
            'api_key': credentials.get('api_key', ''),
            'service_username': credentials.get('service_username', ''),
            'service_password': credentials.get('service_password', ''),
            'auto_sync': provider.auto_sync,
            'collect_performance_stats': provider_metadata.get('collect_performance_stats', True),  # Default to True
            'sync_interval': provider.sync_interval,
            'is_active': provider.is_active
        }
        
        return jsonify({
            'success': True,
            'data': provider_data
        })
        
    except Exception as e:
        logger.error(f"Error getting Selectel connection {provider_id} for editing: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error loading connection data: {str(e)}'
        }), 500


@selectel_bp.route('/<int:provider_id>/update', methods=['POST'])
def update_connection(provider_id):
    """Update a Selectel cloud provider connection."""
    try:
        # Check if user is authenticated
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        user_id = session['user']['id']
        
        provider = CloudProvider.query.filter_by(
            id=provider_id,
            user_id=user_id,
            provider_type='selectel'
        ).first()
        
        if not provider:
            return jsonify({'success': False, 'message': 'Provider not found'}), 404
        
        # Get form data
        connection_name = request.form.get('connection_name')
        api_key = request.form.get('api_key')
        service_username = request.form.get('service_username')
        service_password = request.form.get('service_password')
        auto_sync = request.form.get('auto_sync') == 'on'
        collect_performance_stats = request.form.get('collect_performance_stats') == 'on'
        sync_interval = request.form.get('sync_interval', 'daily')
        
        # Validate required fields
        if not connection_name or not api_key or not service_username or not service_password:
            return jsonify({
                'success': False,
                'message': 'Connection name, API key, service username, and service password are required'
            }), 400
        
        # Convert sync interval to seconds
        sync_interval_map = {
            'hourly': 3600,
            'daily': 86400,
            'weekly': 604800,
            'monthly': 2592000
        }
        sync_interval_seconds = sync_interval_map.get(sync_interval, 86400)
        
        # Test the connection with new credentials
        credentials = {
            'api_key': api_key,
            'service_username': service_username,
            'service_password': service_password
        }
        test_client = SelectelClient(credentials)
        test_result = test_client.test_connection()
        
        if not test_result.get('success'):
            return jsonify({
                'success': False,
                'message': f'Connection test failed: {test_result.get("error", "Unknown error")}'
            }), 400
        
        # Get account info for metadata
        account_info = test_client.get_account_info()
        account_id = account_info.get('account', {}).get('name', '') if account_info else ''
        
        # Prepare provider metadata with settings
        # Preserve existing metadata and update with new settings
        existing_metadata = json.loads(provider.provider_metadata) if provider.provider_metadata else {}
        updated_metadata = {**existing_metadata, **test_result.get('account_info', {})}
        updated_metadata['collect_performance_stats'] = collect_performance_stats
        
        # Update provider record
        provider.connection_name = connection_name
        provider.account_id = account_id
        provider.credentials = json.dumps({
            'api_key': api_key,
            'service_username': service_username,
            'service_password': service_password
        })
        provider.provider_metadata = json.dumps(updated_metadata)
        provider.auto_sync = auto_sync
        provider.sync_interval = sync_interval_seconds
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Connection updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error updating Selectel connection {provider_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error updating connection: {str(e)}'
        }), 500


@selectel_bp.route('/<int:provider_id>/delete', methods=['DELETE'])
def delete_connection(provider_id):
    """Delete a Selectel cloud provider connection."""
    try:
        # Check if user is authenticated
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        user_id = session['user']['id']
        
        provider = CloudProvider.query.filter_by(
            id=provider_id,
            user_id=user_id,
            provider_type='selectel'
        ).first()
        
        if not provider:
            return jsonify({'success': False, 'message': 'Provider not found'}), 404
        
        db.session.delete(provider)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Connection deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting Selectel connection {provider_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error deleting connection: {str(e)}'
        }), 500


@selectel_bp.route('/<int:provider_id>/projects', methods=['GET'])
def get_projects(provider_id):
    """Get projects for a Selectel provider."""
    try:
        # Check if user is authenticated
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        user_id = session['user']['id']
        
        provider = CloudProvider.query.filter_by(
            id=provider_id,
            user_id=user_id,
            provider_type='selectel'
        ).first()
        
        if not provider:
            return jsonify({'success': False, 'message': 'Provider not found'}), 404
        
        service = SelectelService(provider)
        projects = service.client.get_projects()
        
        return jsonify({'success': True, 'projects': projects})
        
    except Exception as e:
        logger.error(f"Error getting Selectel projects for provider {provider_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting projects: {str(e)}'
        }), 500


@selectel_bp.route('/<int:provider_id>/account_info', methods=['GET'])
def get_account_info(provider_id):
    """Get account information for a Selectel provider."""
    try:
        # Check if user is authenticated
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        user_id = session['user']['id']
        
        provider = CloudProvider.query.filter_by(
            id=provider_id,
            user_id=user_id,
            provider_type='selectel'
        ).first()
        
        if not provider:
            return jsonify({'success': False, 'message': 'Provider not found'}), 404
        
        service = SelectelService(provider)
        account_info = service.client.get_account_info()
        
        return jsonify({
            'success': True,
            'account_info': account_info.get('account', {})
        })
        
    except Exception as e:
        logger.error(f"Error getting Selectel account info for provider {provider_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting account info: {str(e)}'
        }), 500


@selectel_bp.route('/<int:provider_id>/summary', methods=['GET'])
def get_resource_summary(provider_id):
    """Get a summary of resources for a Selectel provider."""
    try:
        # Check if user is authenticated
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        user_id = session['user']['id']
        
        provider = CloudProvider.query.filter_by(
            id=provider_id,
            user_id=user_id,
            provider_type='selectel'
        ).first()
        
        if not provider:
            return jsonify({'success': False, 'message': 'Provider not found'}), 404
        
        service = SelectelService(provider)
        summary = service.get_resource_summary()
        
        return jsonify({'success': True, 'summary': summary})
        
    except Exception as e:
        logger.error(f"Error getting Selectel resource summary for provider {provider_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting resource summary: {str(e)}'
        }), 500