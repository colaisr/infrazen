"""
JWT token validation for WebSocket authentication.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict

import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

logger = logging.getLogger(__name__)

# Load JWT configuration from environment
# Prefer AGENT_SERVICE_JWT_SECRET (historical name), fallback to JWT_SECRET_KEY
JWT_SECRET_KEY = (
    os.environ.get('AGENT_SERVICE_JWT_SECRET')
    or os.environ.get('JWT_SECRET_KEY')
    or 'dev-jwt-secret-change-in-production'
)
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '24'))


def create_jwt_token(user_id: int, recommendation_id: int) -> str:
    """
    Create a JWT token for chat authentication.
    
    Args:
        user_id: User ID
        recommendation_id: Recommendation ID
        
    Returns:
        JWT token string
    """
    payload = {
        'user_id': user_id,
        'recommendation_id': recommendation_id,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def validate_jwt_token(token: str) -> Optional[Dict]:
    """
    Validate JWT token and extract payload.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload dict if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Verify required fields
        if 'user_id' not in payload or 'recommendation_id' not in payload:
            logger.warning("JWT token missing required fields")
            return None
            
        return payload
        
    except ExpiredSignatureError:
        logger.warning("JWT token has expired")
        return None
        
    except InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None
        
    except Exception as e:
        logger.error(f"Unexpected error validating JWT: {e}", exc_info=True)
        return None

