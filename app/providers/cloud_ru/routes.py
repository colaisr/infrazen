"""
Cloud.ru provider routes
"""
import threading
from flask import Blueprint, request, jsonify, session, redirect, url_for, flash
from app.core.database import db
from app.core.models.provider import CloudProvider
from app.core.organization_context import get_current_organization_id, require_organization_access
import json
import logging

logger = logging.getLogger(__name__)

cloud_ru_bp = Blueprint('cloud_ru', __name__)


@cloud_ru_bp.route('/')
def index():
    return "Cloud.ru Provider API"


@cloud_ru_bp.route('/test', methods=['POST'])
def test_connection():
    """Test Cloud.ru API connection"""
    try:
        # Get credentials from request
        if request.is_json:
            api_key = request.json.get('api_key')
            api_secret = request.json.get('api_secret')
        else:
            api_key = request.form.get('api_key')
            api_secret = request.form.get('api_secret')
        
        if not api_key or not api_secret:
            return jsonify({
                'success': False,
                'error': 'API Key and API Secret are required'
            }), 400
        
        # Import client (will be created in next step)
        from .client import CloudRuClient
        
        # Test connection
        credentials = {
            'api_key': api_key,
            'api_secret': api_secret
            # account_id removed - project_id is extracted automatically from JWT token
        }
        client = CloudRuClient(credentials)
        test_result = client.test_connection()
        
        return jsonify(test_result)
        
    except Exception as e:
        logger.error(f"Cloud.ru connection test failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Connection test failed'
        }), 500


@cloud_ru_bp.route('/add', methods=['POST'])
def add_connection():
    """Add a new Cloud.ru connection"""
    try:
        # Check if user is authenticated
        if 'user' not in session:
            flash('Authentication required', 'error')
            return redirect(url_for('main.connections'))
        
        # Check if demo user (read-only)
        from app.api.auth import check_demo_user_write_access
        demo_check = check_demo_user_write_access()
        if demo_check:
            return demo_check
        
        user_id = session['user']['id']
        
        # Get form data
        connection_name = request.form.get('connection_name')
        api_key = request.form.get('api_key')
        api_secret = request.form.get('api_secret')
        agreement_id = (request.form.get('agreement_id') or '').strip()
        auto_sync = request.form.get('auto_sync') == 'on'
        sync_interval = request.form.get('sync_interval', 'daily')
        
        # Parse advanced tenants list (JSON string from form)
        advanced_tenants_raw = request.form.get('advanced_tenants', '[]')
        try:
            advanced_tenants = json.loads(advanced_tenants_raw)
            if not isinstance(advanced_tenants, list):
                advanced_tenants = []
        except (json.JSONDecodeError, TypeError):
            advanced_tenants = []
        
        if not all([connection_name, api_key, api_secret]):
            flash('Connection name, API key and API secret are required', 'error')
            return redirect(url_for('main.connections'))
        
        # Test connection first
        from .client import CloudRuClient
        credentials = {'api_key': api_key, 'api_secret': api_secret}
        if agreement_id:
            credentials['agreement_id'] = agreement_id
        if advanced_tenants:
            credentials['advanced_tenants'] = advanced_tenants
        client = CloudRuClient(credentials)
        test_result = client.test_connection()
        
        if not test_result.get('success'):
            flash(f'Connection test failed: {test_result.get("message", "Unknown error")}', 'error')
            return redirect(url_for('main.connections'))
        
        # Use agreement_id: form > auto-discovered from connection test
        aid = agreement_id or test_result.get('account_info', {}).get('agreement_id')
        if aid:
            credentials['agreement_id'] = aid
        
        # Get current organization
        org_id = get_current_organization_id()
        if not org_id:
            flash('No active organization', 'error')
            return redirect(url_for('main.connections'))
        
        # Verify user has access to organization
        try:
            require_organization_access(org_id, user_id)
        except Exception:
            flash('Access denied to organization', 'error')
            return redirect(url_for('main.connections'))
        
        # Extract project_id from test result (from token) for account_id field
        # This is for display purposes - actual project_id is extracted from token during sync
        account_id = ''
        if test_result.get('account_info'):
            account_id = test_result.get('account_info', {}).get('account_id', '')
        
        # Create provider record
        provider = CloudProvider(
            user_id=user_id,
            organization_id=org_id,
            provider_type='cloud-ru',
            connection_name=connection_name,
            account_id=account_id,  # Stored for display, but not used for API calls
            credentials=json.dumps(credentials),
            provider_metadata=json.dumps(test_result.get('account_info', {})),
            is_active=True,
            auto_sync=auto_sync,
            sync_interval=sync_interval
        )
        
        db.session.add(provider)
        db.session.commit()
        
        flash('Cloud.ru connection added successfully', 'success')
        return redirect(url_for('main.connections'))
        
    except Exception as e:
        logger.error(f"Failed to add Cloud.ru connection: {str(e)}")
        db.session.rollback()
        flash(f'Failed to add connection: {str(e)}', 'error')
        return redirect(url_for('main.connections'))


@cloud_ru_bp.route('/<int:provider_id>/edit', methods=['GET'])
def edit_connection(provider_id):
    """Get Cloud.ru provider details for editing"""
    try:
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        user_id = session['user']['id']
        org_id = get_current_organization_id()
        if not org_id:
            return jsonify({'success': False, 'message': 'No active organization'}), 400
        
        provider = CloudProvider.query.filter_by(
            id=provider_id,
            user_id=user_id,
            organization_id=org_id,
            provider_type='cloud-ru'
        ).first()
        
        if not provider:
            return jsonify({'success': False, 'message': 'Provider not found'}), 404
        
        # Parse credentials
        credentials = json.loads(provider.credentials) if provider.credentials else {}
        
        return jsonify({
            'success': True,
            'data': {
                'id': provider.id,
                'provider': 'cloud-ru',
                'connection_name': provider.connection_name,
                'account_id': provider.account_id,
                'api_key': credentials.get('api_key', ''),
                'api_secret': credentials.get('api_secret', ''),
                'agreement_id': credentials.get('agreement_id', ''),
                'advanced_tenants': credentials.get('advanced_tenants', []),
                'auto_sync': provider.auto_sync,
                'sync_interval': provider.sync_interval
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting Cloud.ru connection {provider_id} for editing: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error loading connection data: {str(e)}'
        }), 500


@cloud_ru_bp.route('/<int:provider_id>/update', methods=['POST'])
def update_connection(provider_id):
    """Update a Cloud.ru connection"""
    try:
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        # Check if demo user (read-only)
        from app.api.auth import check_demo_user_write_access
        demo_check = check_demo_user_write_access()
        if demo_check:
            return demo_check
        
        user_id = session['user']['id']
        org_id = get_current_organization_id()
        if not org_id:
            return jsonify({'success': False, 'message': 'No active organization'}), 400
        
        provider = CloudProvider.query.filter_by(
            id=provider_id,
            user_id=user_id,
            organization_id=org_id,
            provider_type='cloud-ru'
        ).first()
        
        if not provider:
            return jsonify({'success': False, 'message': 'Provider not found'}), 404
        
        # Get form data
        connection_name = request.form.get('connection_name')
        api_key = request.form.get('api_key')
        api_secret = request.form.get('api_secret')
        agreement_id = (request.form.get('agreement_id') or '').strip()
        auto_sync = request.form.get('auto_sync') == 'on'
        sync_interval = request.form.get('sync_interval', 'daily')
        
        # Parse advanced tenants list (JSON string from form)
        advanced_tenants_raw = request.form.get('advanced_tenants', None)
        existing_credentials = json.loads(provider.credentials) if provider.credentials else {}
        
        if not all([connection_name, api_key]):
            return jsonify({
                'success': False,
                'message': 'Connection name and API key are required'
            }), 400
        
        # If api_secret is empty, keep existing one
        if not api_secret:
            api_secret = existing_credentials.get('api_secret', '')
        
        # Parse advanced_tenants: form value takes priority; fall back to existing
        if advanced_tenants_raw is not None:
            try:
                advanced_tenants = json.loads(advanced_tenants_raw)
                if not isinstance(advanced_tenants, list):
                    advanced_tenants = []
            except (json.JSONDecodeError, TypeError):
                advanced_tenants = existing_credentials.get('advanced_tenants', [])
        else:
            advanced_tenants = existing_credentials.get('advanced_tenants', [])
        
        # For rows where SK is blank, preserve existing SK for that tenant (by name)
        existing_tenant_map = {t.get('name'): t for t in existing_credentials.get('advanced_tenants', [])}
        for tenant in advanced_tenants:
            if not tenant.get('sk') and tenant.get('name') in existing_tenant_map:
                tenant['sk'] = existing_tenant_map[tenant['name']].get('sk', '')
        
        # Test connection with new credentials
        from .client import CloudRuClient
        credentials = {'api_key': api_key, 'api_secret': api_secret}
        # agreement_id: form > existing > auto-discovered from test
        if agreement_id:
            credentials['agreement_id'] = agreement_id
        elif existing_credentials.get('agreement_id'):
            credentials['agreement_id'] = existing_credentials['agreement_id']
        if advanced_tenants:
            credentials['advanced_tenants'] = advanced_tenants
        client = CloudRuClient(credentials)
        test_result = client.test_connection()
        
        if not test_result.get('success'):
            return jsonify({
                'success': False,
                'message': f'Connection test failed: {test_result.get("message", "Unknown error")}'
            }), 400
        
        # Use agreement_id: form > auto-discovered from test > existing (from prior sync)
        aid = agreement_id or test_result.get('account_info', {}).get('agreement_id') or existing_credentials.get('agreement_id')
        if aid:
            credentials['agreement_id'] = aid
        
        # Update provider
        provider.connection_name = connection_name
        # account_id is kept from existing provider (for display) but not updated from form
        # project_id is extracted from token during sync, not from user input
        provider.credentials = json.dumps(credentials)
        provider.provider_metadata = json.dumps(test_result.get('account_info', {}))
        provider.auto_sync = auto_sync
        provider.sync_interval = sync_interval
        provider.sync_error = None  # Clear any previous errors
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Connection updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error updating Cloud.ru connection {provider_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating connection: {str(e)}'
        }), 500


@cloud_ru_bp.route('/<int:provider_id>/delete', methods=['DELETE'])
def delete_connection(provider_id):
    """Soft delete Cloud.ru connection"""
    try:
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        # Check if demo user (read-only)
        from app.api.auth import check_demo_user_write_access
        demo_check = check_demo_user_write_access()
        if demo_check:
            return demo_check
        
        from datetime import datetime
        user_id = session['user']['id']
        org_id = get_current_organization_id()
        
        provider = CloudProvider.query.filter_by(
            id=provider_id,
            user_id=user_id,
            organization_id=org_id,
            provider_type='cloud-ru',
            is_deleted=False
        ).first()
        
        if not provider:
            return jsonify({'success': False, 'message': 'Provider not found'}), 404
        
        # Soft delete
        provider.is_deleted = True
        provider.deleted_at = datetime.utcnow()
        provider.is_active = False
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Connection deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting Cloud.ru connection {provider_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting connection: {str(e)}'
        }), 500


@cloud_ru_bp.route('/<int:provider_id>/sync', methods=['POST'])
def sync_connection(provider_id):
    """Manually trigger resource synchronization for Cloud.ru.
    Runs in background to avoid HTTP timeout when syncing 2500+ resources (~15s).
    """
    try:
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        # Check if demo user (read-only)
        from app.api.auth import check_demo_user_write_access
        demo_check = check_demo_user_write_access()
        if demo_check:
            return demo_check
        
        user_id = session['user']['id']
        org_id = get_current_organization_id()
        if not org_id:
            return jsonify({'success': False, 'message': 'No active organization'}), 400
        
        provider = CloudProvider.query.filter_by(
            id=provider_id,
            user_id=user_id,
            organization_id=org_id,
            provider_type='cloud-ru'
        ).first()
        
        if not provider:
            return jsonify({'success': False, 'message': 'Provider not found'}), 404
        
        from app.providers import sync_orchestrator
        from app import create_app

        def background_sync():
            app = create_app()
            with app.app_context():
                try:
                    sync_orchestrator.sync_provider(provider_id, sync_type='manual')
                except Exception as e:
                    logger.error(f"Background Cloud.ru sync failed for provider {provider_id}: {e}", exc_info=True)

        thread = threading.Thread(target=background_sync, daemon=True)
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Синхронизация запущена в фоне. Обновите страницу через 15–30 секунд.',
            'resources_synced': 0,
            'total_daily_cost': 0,
            'total_monthly_cost': 0,
            'background': True,
        })
            
    except Exception as e:
        logger.error(f"Error starting Cloud.ru sync for provider {provider_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error syncing resources: {str(e)}'
        }), 500

