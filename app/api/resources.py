"""
Resources API routes
"""
from flask import Blueprint, jsonify, request
from app.core.models.resource import Resource
from app.core.models.provider import CloudProvider
from app.core.models.user import User

resources_bp = Blueprint('resources', __name__)

@resources_bp.route('/')
def list_resources():
    """List all resources, excluding demo user resources by default"""
    # Check if we should include demo user data
    include_demo = request.args.get('include_demo', 'false').lower() == 'true'
    
    # Build query to get resources
    query = Resource.query
    
    # Exclude demo user resources unless explicitly requested
    if not include_demo:
        # Get demo user IDs
        demo_user_ids = [u.id for u in User.query.filter_by(role='demouser').all()]
        if demo_user_ids:
            # Join with CloudProvider to filter by user_id
            query = query.join(CloudProvider, Resource.provider_id == CloudProvider.id)
            query = query.filter(~CloudProvider.user_id.in_(demo_user_ids))
    
    resources = query.all()
    
    return jsonify({
        'success': True,
        'resources': [
            {
                'id': r.id,
                'resource_id': r.resource_id,
                'resource_name': r.resource_name,
                'resource_type': r.resource_type,
                'status': r.status,
                'provider_id': r.provider_id
            } for r in resources
        ]
    })
