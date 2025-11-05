"""
Chat API endpoints for generating JWT tokens and chat management.
"""

from flask import Blueprint, request, jsonify
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
    data = request.get_json()
    
    if not data or 'recommendation_id' not in data:
        return jsonify({'error': 'recommendation_id is required'}), 400
    
    # Convert to int (may come as string from JavaScript)
    try:
        recommendation_id = int(data['recommendation_id'])
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid recommendation_id'}), 400
    
    # Verify recommendation exists and belongs to user
    # Recommendation -> Resource -> Provider -> user_id
    recommendation = OptimizationRecommendation.query.filter_by(
        id=recommendation_id
    ).first()
    
    if not recommendation:
        return jsonify({'error': 'Recommendation not found'}), 404
    
    # Verify ownership through provider
    if recommendation.provider_id:
        provider = CloudProvider.query.filter_by(id=recommendation.provider_id).first()
        if not provider or provider.user_id != current_user.id:
            return jsonify({'error': 'Recommendation not found'}), 404
    elif recommendation.resource_id:
        resource = Resource.query.filter_by(id=recommendation.resource_id).first()
        if resource and resource.provider:
            if resource.provider.user_id != current_user.id:
                return jsonify({'error': 'Recommendation not found'}), 404
        else:
            return jsonify({'error': 'Recommendation not found'}), 404
    else:
        return jsonify({'error': 'Recommendation not found'}), 404
    
    # Create JWT token
    payload = {
        'user_id': current_user.id,
        'recommendation_id': recommendation_id,
        'exp': datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)
    
    return jsonify({
        'token': token,
        'expires_in': Config.JWT_EXPIRATION_HOURS * 3600,  # seconds
        'recommendation_id': recommendation_id
    })

