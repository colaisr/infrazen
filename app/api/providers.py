"""
Providers API routes
"""
from flask import Blueprint, jsonify, request
from app.core.models.provider import CloudProvider
from app.core.models.user import User

providers_bp = Blueprint('providers', __name__)


@providers_bp.route('/', methods=['GET'])
def list_providers():
    """List all providers, excluding demo user providers by default"""
    # Check if we should include demo user data
    include_demo = request.args.get('include_demo', 'false').lower() == 'true'
    
    # Get all providers
    query = CloudProvider.query
    
    # Exclude demo user providers unless explicitly requested
    if not include_demo:
        # Get demo user IDs
        demo_user_ids = [u.id for u in User.query.filter_by(role='demouser').all()]
        if demo_user_ids:
            query = query.filter(~CloudProvider.user_id.in_(demo_user_ids))
    
    providers = query.all()
    
    return jsonify({
        'success': True,
        'providers': [
            {
                'id': p.id,
                'provider_type': p.provider_type,
                'code': p.provider_type,
                'name': p.connection_name,
                'is_active': p.is_active,
            } for p in providers
        ]
    })
