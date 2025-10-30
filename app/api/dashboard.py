"""
Dashboard API endpoints
"""
from flask import Blueprint, jsonify, session
from app.core.models.provider import CloudProvider
from app.core.models.resource import Resource
from app.core.models.sync import SyncSnapshot, ResourceState
from app.core.models.user import User

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard/resources', methods=['GET'])
def get_dashboard_resources():
    """Get top 10 resources from last sync for dashboard card"""
    try:
        # Resolve current user
        current_user_id = None
        try:
            user_data = session.get('user') or {}
            if user_data.get('email') == 'demo@infrazen.com':
                demo_user = User.find_by_email('demo@infrazen.com')
                if demo_user:
                    current_user_id = demo_user.id
            else:
                current_user_id = user_data.get('db_id') or int(float(user_data.get('id')))
        except Exception:
            current_user_id = None

        if not current_user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401

        # Get latest successful complete sync for this user
        from app.core.models.complete_sync import CompleteSync, ProviderSyncReference
        
        latest_complete_sync = (
            CompleteSync.query
            .filter_by(user_id=current_user_id, sync_status='success')
            .order_by(CompleteSync.sync_completed_at.desc())
            .first()
        )
        
        if not latest_complete_sync:
            return jsonify({'success': True, 'resources': [], 'total': 0})

        # Get provider IDs that were part of this complete sync
        provider_refs = [
            ref for ref in latest_complete_sync.provider_syncs or [] 
            if ref.sync_status == 'success'
        ]
        
        if not provider_refs:
            return jsonify({'success': True, 'resources': [], 'total': 0})

        provider_ids = [ref.provider_id for ref in provider_refs]
        
        # Collect resources: use ResourceState where available, fallback to active resources by provider
        all_resources = []
        
        for ref in provider_refs:
            # Try ResourceState first
            resource_states = ResourceState.query.filter_by(sync_snapshot_id=ref.sync_snapshot_id).all()
            
            if resource_states:
                # Use ResourceState (preferred)
                resource_ids = [rs.resource_id for rs in resource_states if rs.resource_id]
                if resource_ids:
                    provider_resources = Resource.query.filter(Resource.id.in_(resource_ids)).all()
                    all_resources.extend(provider_resources)
            else:
                # Fallback: get active resources for this provider
                # This happens when ResourceState entries weren't created during sync
                provider_resources = Resource.query.filter_by(
                    provider_id=ref.provider_id,
                    is_active=True
                ).all()
                all_resources.extend(provider_resources)

        # Sort by daily cost descending
        all_resources.sort(key=lambda r: r.daily_cost or 0, reverse=True)

        # Serialize ALL resources (not just top 10, so client-side filtering works)
        resources_data = []
        for r in all_resources:
            provider = CloudProvider.query.get(r.provider_id)
            resources_data.append({
                'id': r.id,
                'resource_id': r.resource_id,
                'resource_name': r.resource_name,
                'name': r.resource_name,
                'resource_type': r.resource_type,
                'type': r.resource_type,
                'status': r.status,
                'region': r.region,
                'daily_cost': float(r.daily_cost or 0),
                'provider_id': r.provider_id,
                'provider_name': provider.connection_name if provider else None,
                'provider_type': provider.provider_type if provider else None
            })

        return jsonify({
            'success': True,
            'resources': resources_data,
            'total': len(all_resources)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

