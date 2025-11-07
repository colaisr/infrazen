"""
Chat API endpoints for generating JWT tokens and chat management.
"""

from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user
import jwt
from datetime import datetime, timedelta

from app.config import Config
from app.core.models import OptimizationRecommendation, Resource, CloudProvider, db

chat_api = Blueprint('chat_api', __name__)


@chat_api.route('/token', methods=['POST'])
@login_required
def generate_chat_token():
    """
    Generate a JWT token for chat authentication.
    
    Request JSON:
        recommendation_id (int): ID of the recommendation to chat about
        
    Returns:
        JSON with token and expiration
    """
    data = request.get_json() or {}
    scenario = data.get('scenario', 'recommendation')

    user_data = session.get('user', {})
    effective_user_id = user_data.get('db_id') or current_user.id

    context_payload = None
    recommendation_id = None

    if scenario == 'recommendation':
        if 'recommendation_id' not in data:
            return jsonify({'error': 'recommendation_id is required'}), 400

        try:
            recommendation_id = int(data['recommendation_id'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid recommendation_id'}), 400

    elif scenario == 'analytics':
        # Optional: allow client to specify time range and filters
        time_range_days = data.get('time_range_days', 30)
        try:
            time_range_days = int(time_range_days)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid time_range_days'}), 400

        filters = data.get('filters') if isinstance(data.get('filters'), dict) else None
        context_payload = {'time_range_days': time_range_days}
        if filters:
            context_payload['filters'] = filters
    else:
        return jsonify({'error': f'Unsupported scenario: {scenario}'}), 400

    # Verify recommendation exists and belongs to user
    if scenario == 'recommendation':
        recommendation = OptimizationRecommendation.query.filter_by(
            id=recommendation_id
        ).first()

        if not recommendation:
            return jsonify({'error': 'Recommendation not found'}), 404

        if recommendation.provider_id:
            provider = CloudProvider.query.filter_by(id=recommendation.provider_id).first()
            if not provider or provider.user_id != effective_user_id:
                return jsonify({'error': 'Recommendation not found'}), 404
        elif recommendation.resource_id:
            resource = Resource.query.filter_by(id=recommendation.resource_id).first()
            if resource and resource.provider:
                if resource.provider.user_id != effective_user_id:
                    return jsonify({'error': 'Recommendation not found'}), 404
            else:
                return jsonify({'error': 'Recommendation not found'}), 404
        else:
            return jsonify({'error': 'Recommendation not found'}), 404
    
    # Create JWT token with effective user ID (impersonated user if applicable)
    payload = {
        'user_id': effective_user_id,
        'scenario': scenario,
        'recommendation_id': recommendation_id,
        'context': context_payload,
        'exp': datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)
    
    return jsonify({
        'token': token,
        'expires_in': Config.JWT_EXPIRATION_HOURS * 3600,  # seconds
        'recommendation_id': recommendation_id,
        'scenario': scenario,
        'context': context_payload
    })

