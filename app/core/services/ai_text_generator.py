"""
AI text generation service
Calls the Agent Service to generate recommendation texts during sync
"""
import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime
from flask import current_app

logger = logging.getLogger(__name__)


def generate_recommendation_text(recommendation_id: int) -> Optional[Dict[str, str]]:
    """
    Call Agent Service to generate AI text for a recommendation
    
    Args:
        recommendation_id: Recommendation database ID
        
    Returns:
        Dict with short_description_html and detailed_description_html, or None if disabled/failed
    """
    try:
        # Check if AI recommendations are enabled
        if not current_app.config.get('ENABLE_AI_RECOMMENDATIONS', False):
            logger.debug("AI recommendations disabled, skipping text generation")
            return None
        
        agent_url = current_app.config.get('AGENT_SERVICE_URL', 'http://127.0.0.1:8001')
        endpoint = f"{agent_url}/v1/generate/recommendation-text"
        
        logger.info(f"Generating AI text for recommendation {recommendation_id}")
        
        response = requests.post(
            endpoint,
            json={"recommendation_id": recommendation_id},
            timeout=30  # 30s timeout for LLM call
        )
        
        if not response.ok:
            logger.warning(f"Agent returned status {response.status_code} for rec {recommendation_id}")
            return None
        
        data = response.json()
        
        # Validate response
        if data.get('error'):
            logger.warning(f"Agent returned error for rec {recommendation_id}: {data['error']}")
            return None
        
        if not data.get('short_description_html') or not data.get('detailed_description_html'):
            logger.warning(f"Agent returned incomplete data for rec {recommendation_id}")
            return None
        
        logger.info(f"✓ AI text generated for rec {recommendation_id} (model: {data.get('model')}, tokens: {data.get('tokens')})")
        
        return {
            'short_description_html': data['short_description_html'],
            'detailed_description_html': data['detailed_description_html']
        }
        
    except requests.Timeout:
        logger.warning(f"Timeout generating AI text for rec {recommendation_id}")
        return None
    except Exception as e:
        logger.error(f"Error generating AI text for rec {recommendation_id}: {e}")
        return None

