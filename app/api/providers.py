"""
Providers API routes
"""
from flask import Blueprint, jsonify
from app.core.models.provider import CloudProvider

providers_bp = Blueprint('providers', __name__)


@providers_bp.route('/', methods=['GET'])
def list_providers():
    providers = CloudProvider.query.all()
    return jsonify({
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
