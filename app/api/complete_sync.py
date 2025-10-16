"""
Complete Sync API endpoints
"""
from flask import Blueprint, request, jsonify, session
from app.core.services.complete_sync_service import CompleteSyncService
from app.api.auth import check_demo_user_write_access

# Create blueprint
complete_sync_bp = Blueprint('complete_sync', __name__)

@complete_sync_bp.route('/api/complete-sync', methods=['POST'])
def start_complete_sync():
    """Start a complete sync operation for all auto-sync enabled providers"""
    try:
        if 'user' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        # Check if demo user (read-only)
        demo_check = check_demo_user_write_access()
        if demo_check:
            return demo_check
        
        user_id = int(float(session['user']['id']))
        sync_type = request.json.get('sync_type', 'manual') if request.is_json else 'manual'
        
        # Create complete sync service
        complete_sync_service = CompleteSyncService(user_id)
        
        # Start complete sync
        result = complete_sync_service.start_complete_sync(sync_type)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Complete sync started successfully',
                'complete_sync_id': result['complete_sync_id'],
                'sync_status': result['sync_status'],
                'total_providers_synced': result['total_providers_synced'],
                'successful_providers': result['successful_providers'],
                'failed_providers': result['failed_providers'],
                'total_resources_found': result['total_resources_found'],
                'total_daily_cost': result['total_daily_cost'],
                'total_monthly_cost': result['total_monthly_cost'],
                'cost_by_provider': result['cost_by_provider'],
                'resources_by_provider': result['resources_by_provider'],
                'sync_duration_seconds': result['sync_duration_seconds']
            })
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
        
        user_id = int(float(session['user']['id']))
        
        # Create complete sync service
        complete_sync_service = CompleteSyncService(user_id)
        
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
    """Get complete sync history for the user"""
    try:
        if 'user' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        user_id = int(float(session['user']['id']))
        limit = request.args.get('limit', 30, type=int)
        
        # Create complete sync service
        complete_sync_service = CompleteSyncService(user_id)
        
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
