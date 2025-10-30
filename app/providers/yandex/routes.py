"""
Yandex Cloud provider routes
"""
from flask import Blueprint, jsonify, request, session, redirect, url_for, flash
from app.core.models.provider import CloudProvider
from app.core.models.user import User
from app.providers.yandex.service import YandexService
from app.core.database import db
import json
import logging

logger = logging.getLogger(__name__)

yandex_bp = Blueprint('yandex', __name__, url_prefix='/api/providers/yandex')


@yandex_bp.route('/test', methods=['POST'])
def test_yandex_connection_form():
    """Test Yandex Cloud connection from connection form"""
    try:
        # Get credentials from form data (JSON from modal)
        data = request.get_json()
        
        if not data or 'service_account_key' not in data:
            return jsonify({
                'success': False,
                'error': 'Service account key is required'
            }), 400
        
        # Parse service account key JSON
        try:
            service_account_key = json.loads(data['service_account_key'])
        except json.JSONDecodeError:
            return jsonify({
                'success': False,
                'error': 'Invalid JSON format for service account key. Please paste the complete JSON file from Yandex Cloud.'
            }), 400
        
        # Validate service account key structure
        required_fields = ['id', 'service_account_id', 'private_key']
        missing_fields = [f for f in required_fields if f not in service_account_key]
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Invalid service account key. Missing fields: {", ".join(missing_fields)}'
            }), 400
        
        # Create temporary client for testing
        # Wrap the service account key in a credentials dict
        from app.providers.yandex.client import YandexClient
        credentials = {'service_account_key': service_account_key}
        client = YandexClient(credentials)
        
        # Test connection
        result = client.test_connection()
        
        # Add account info for display
        if result.get('success') and result.get('clouds'):
            clouds = result.get('clouds', [])
            if clouds:
                first_cloud = clouds[0]
                result['account_info'] = {
                    'name': first_cloud.get('name', 'Unknown'),
                    'id': first_cloud.get('id', '')
                }
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error testing Yandex connection from form: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@yandex_bp.route('/add', methods=['POST'])
def add_yandex_connection():
    """Add new Yandex Cloud connection"""
    try:
        # Get user from session
        if 'user' not in session:
            flash('Not authenticated', 'error')
            return redirect(url_for('main.connections'))
        
        user_email = session['user'].get('email')
        user = User.query.filter_by(email=user_email).first()
        
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('main.connections'))
        
        # Get form data
        connection_name = request.form.get('connection_name')
        service_account_key_str = request.form.get('service_account_key')
        auto_sync = request.form.get('auto_sync') == 'on'
        description = request.form.get('description', '')
        
        if not connection_name or not service_account_key_str:
            flash('Connection name and service account key are required', 'error')
            return redirect(url_for('main.connections'))
        
        # Parse and validate service account key
        try:
            service_account_key = json.loads(service_account_key_str)
        except json.JSONDecodeError:
            flash('Invalid JSON format for service account key', 'error')
            return redirect(url_for('main.connections'))
        
        # Extract cloud_id if available (for account_id)
        cloud_id = service_account_key.get('cloud_id', service_account_key.get('service_account_id', 'yandex_cloud'))
        
        # Wrap service account key in credentials dict for consistent storage
        credentials_dict = {
            'service_account_key': service_account_key
        }
        
        # Create provider entry
        provider = CloudProvider(
            user_id=user.id,
            provider_type='yandex',
            connection_name=connection_name,
            account_id=cloud_id,
            credentials=json.dumps(credentials_dict),
            is_active=True,
            auto_sync=auto_sync,
            sync_status='pending',
            provider_metadata=json.dumps({
                'description': description,
                'added_via': 'web_form'
            })
        )
        
        db.session.add(provider)
        db.session.commit()
        
        logger.info(f"Added Yandex Cloud connection: {connection_name} (ID: {provider.id})")
        flash(f'✅ Yandex Cloud connection "{connection_name}" added successfully!', 'success')
        
        return redirect(url_for('main.connections'))
    
    except Exception as e:
        logger.error(f"Error adding Yandex connection: {e}")
        db.session.rollback()
        flash(f'Error adding connection: {str(e)}', 'error')
        return redirect(url_for('main.connections'))


@yandex_bp.route('/<int:provider_id>/update', methods=['POST'])
def update_yandex_connection(provider_id):
    """Update existing Yandex Cloud connection"""
    try:
        provider = CloudProvider.query.get(provider_id)
        
        if not provider:
            return jsonify({
                'success': False,
                'error': 'Provider not found'
            }), 404
        
        # Update fields
        connection_name = request.form.get('connection_name')
        service_account_key_str = request.form.get('service_account_key')
        auto_sync = request.form.get('auto_sync') == 'on'
        description = request.form.get('description', '')
        
        if connection_name:
            provider.connection_name = connection_name
        
        if service_account_key_str:
            try:
                service_account_key = json.loads(service_account_key_str)
                
                # Wrap service account key in credentials dict for consistent storage
                credentials_dict = {
                    'service_account_key': service_account_key
                }
                provider.credentials = json.dumps(credentials_dict)
                
                # Update cloud_id if changed
                cloud_id = service_account_key.get('cloud_id', service_account_key.get('service_account_id'))
                if cloud_id:
                    provider.account_id = cloud_id
            except json.JSONDecodeError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid JSON format for service account key'
                }), 400
        
        provider.auto_sync = auto_sync
        
        # Update metadata
        metadata = json.loads(provider.provider_metadata) if provider.provider_metadata else {}
        metadata['description'] = description
        provider.provider_metadata = json.dumps(metadata)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Connection updated successfully'
        })
    
    except Exception as e:
        logger.error(f"Error updating Yandex connection: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@yandex_bp.route('/<int:provider_id>/delete', methods=['DELETE'])
def delete_yandex_connection(provider_id):
    """Soft delete Yandex Cloud connection - preserves historical data"""
    try:
        from datetime import datetime
        provider = CloudProvider.query.filter_by(id=provider_id, is_deleted=False).first()
        
        if not provider:
            return jsonify({
                'success': False,
                'error': 'Provider not found'
            }), 404
        
        connection_name = provider.connection_name
        
        # Soft delete: mark as deleted instead of removing from database
        provider.is_deleted = True
        provider.deleted_at = datetime.utcnow()
        provider.is_active = False  # Also deactivate
        
        db.session.commit()
        
        logger.info(f"Soft deleted Yandex Cloud connection: {connection_name} (ID: {provider_id})")
        
        return jsonify({
            'success': True,
            'message': 'Connection removed successfully'
        })
    
    except Exception as e:
        logger.error(f"Error soft deleting Yandex connection: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@yandex_bp.route('/<int:provider_id>/edit', methods=['GET'])
def edit_yandex_connection(provider_id):
    """Get Yandex Cloud connection for editing"""
    try:
        provider = CloudProvider.query.get(provider_id)
        
        if not provider:
            return jsonify({
                'success': False,
                'error': 'Provider not found'
            }), 404
        
        # Parse credentials to unwrap the service account key
        credentials = json.loads(provider.credentials) if provider.credentials else {}
        service_account_key = credentials.get('service_account_key', {})
        
        # Convert back to JSON string for display in textarea
        service_account_key_str = json.dumps(service_account_key, indent=2, ensure_ascii=False)
        
        metadata = json.loads(provider.provider_metadata) if provider.provider_metadata else {}
        
        return jsonify({
            'success': True,
            'data': {
                'id': provider.id,
                'provider': 'yandex',
                'connection_name': provider.connection_name,
                'service_account_key': service_account_key_str,
                'auto_sync': provider.auto_sync,
                'description': metadata.get('description', ''),
                'sync_interval': provider.sync_interval
            }
        })
    
    except Exception as e:
        logger.error(f"Error getting Yandex connection for edit: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@yandex_bp.route('/<int:provider_id>/sync', methods=['POST'])
def sync_yandex_provider(provider_id):
    """Sync Yandex Cloud resources"""
    try:
        provider = CloudProvider.query.get(provider_id)
        if not provider:
            return jsonify({'success': False, 'error': 'Provider not found'}), 404
        
        service = YandexService(provider)
        result = service.sync_resources()
        
        # Ensure cost fields match what the JavaScript expects
        if result.get('success'):
            daily_cost = float(result.get('estimated_daily_cost', 0))
            result['total_daily_cost'] = daily_cost
            result['total_monthly_cost'] = daily_cost * 30
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error syncing Yandex resources: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@yandex_bp.route('/clouds/<int:provider_id>', methods=['GET'])
def get_yandex_clouds(provider_id):
    """Get Yandex Cloud clouds for a provider"""
    try:
        provider = CloudProvider.query.get(provider_id)
        if not provider:
            return jsonify({'success': False, 'error': 'Provider not found'}), 404
        
        service = YandexService(provider)
        clouds = service.client.list_clouds()
        
        return jsonify({'success': True, 'clouds': clouds})
    except Exception as e:
        logger.error(f"Error getting Yandex clouds: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@yandex_bp.route('/folders/<int:provider_id>', methods=['GET'])
def get_yandex_folders(provider_id):
    """Get Yandex Cloud folders for a provider"""
    try:
        provider = CloudProvider.query.get(provider_id)
        if not provider:
            return jsonify({'success': False, 'error': 'Provider not found'}), 404
        
        service = YandexService(provider)
        folders = service.client.list_folders()
        
        return jsonify({'success': True, 'folders': folders})
    except Exception as e:
        logger.error(f"Error getting Yandex folders: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
