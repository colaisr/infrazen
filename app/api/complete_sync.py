"""
Complete Sync API endpoints
"""
from flask import Blueprint, request, jsonify, session
from app.core.services.complete_sync_service import CompleteSyncService
from app.core.organization_context import get_current_organization_id
from app.api.auth import check_demo_user_write_access

# Create blueprint
complete_sync_bp = Blueprint('complete_sync', __name__)

@complete_sync_bp.route('/api/complete-sync', methods=['POST'])
def start_complete_sync():
    """Start a complete sync operation for all auto-sync enabled providers in the current organization.
    Runs in background to avoid nginx 504 timeout (sync can take 2-3+ minutes)."""
    try:
        if 'user' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        # Check if demo user (read-only)
        demo_check = check_demo_user_write_access()
        if demo_check:
            return demo_check
        
        # Get organization_id from session (set by organization context middleware)
        organization_id = get_current_organization_id()
        if not organization_id:
            return jsonify({
                'success': False,
                'error': 'Organization context required',
                'message': 'No active organization found. Please select an organization.'
            }), 400
        
        user_id = int(float(session['user']['id']))
        sync_type = request.json.get('sync_type', 'manual') if request.is_json else 'manual'
        
        # Create complete sync service for organization
        complete_sync_service = CompleteSyncService(organization_id, user_id=user_id)
        
        # Start complete sync (synchronous - returns full result)
        result = complete_sync_service.start_complete_sync(sync_type, background=False)
        
        if result['success']:
            resp = {
                'success': True,
                'message': result.get('message', 'Complete sync started successfully'),
                'complete_sync_id': result['complete_sync_id'],
                'background': result.get('background', False),
            }
            if not result.get('background'):
                resp.update({
                    'sync_status': result['sync_status'],
                    'total_providers_synced': result['total_providers_synced'],
                    'successful_providers': result['successful_providers'],
                    'failed_providers': result['failed_providers'],
                    'total_resources_found': result['total_resources_found'],
                    'total_daily_cost': result['total_daily_cost'],
                    'total_monthly_cost': result['total_monthly_cost'],
                    'cost_by_provider': result.get('cost_by_provider', {}),
                    'resources_by_provider': result.get('resources_by_provider', {}),
                    'sync_duration_seconds': result.get('sync_duration_seconds'),
                })
            return jsonify(resp)
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': result.get('message', 'Complete sync failed')
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Complete sync failed due to system error'
        }), 500

@complete_sync_bp.route('/api/complete-sync/<int:complete_sync_id>', methods=['GET'])
def get_complete_sync_status(complete_sync_id):
    """Get status of a specific complete sync"""
    try:
        if 'user' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        # Get organization_id from session
        organization_id = get_current_organization_id()
        if not organization_id:
            return jsonify({
                'success': False,
                'error': 'Organization context required',
                'message': 'No active organization found. Please select an organization.'
            }), 400
        
        user_id = int(float(session['user']['id']))
        
        # Create complete sync service for organization
        complete_sync_service = CompleteSyncService(organization_id, user_id=user_id)
        
        # Get sync status
        result = complete_sync_service.get_complete_sync_status(complete_sync_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'complete_sync_id': result['complete_sync_id'],
                'sync_status': result['sync_status'],
                'sync_started_at': result['sync_started_at'],
                'sync_completed_at': result['sync_completed_at'],
                'sync_duration_seconds': result['sync_duration_seconds'],
                'total_providers_synced': result['total_providers_synced'],
                'successful_providers': result['successful_providers'],
                'failed_providers': result['failed_providers'],
                'total_resources_found': result['total_resources_found'],
                'total_monthly_cost': result['total_monthly_cost'],
                'total_daily_cost': result['total_daily_cost'],
                'cost_by_provider': result['cost_by_provider'],
                'resources_by_provider': result['resources_by_provider'],
                'error_message': result['error_message'],
                'error_details': result['error_details']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'message': result.get('message', 'Complete sync not found')
            }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to get complete sync status'
        }), 500

@complete_sync_bp.route('/api/complete-sync/history', methods=['GET'])
def get_complete_sync_history():
    """Get complete sync history for the current organization"""
    try:
        if 'user' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        # Get organization_id from session
        organization_id = get_current_organization_id()
        if not organization_id:
            return jsonify({
                'success': False,
                'error': 'Organization context required',
                'message': 'No active organization found. Please select an organization.'
            }), 400
        
        user_id = int(float(session['user']['id']))
        limit = request.args.get('limit', 30, type=int)
        
        # Create complete sync service for organization
        complete_sync_service = CompleteSyncService(organization_id, user_id=user_id)
        
        # Get sync history
        history = complete_sync_service.get_complete_sync_history(limit)
        
        return jsonify({
            'success': True,
            'complete_syncs': history,
            'count': len(history)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to get complete sync history'
        }), 500
