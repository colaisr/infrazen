"""
Recommendations API endpoints
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.database import db
from agent_service.core.recommendation_generator import RecommendationGenerator

router = APIRouter()
logger = logging.getLogger(__name__)


class GenerateRecommendationRequest(BaseModel):
    """Request to generate recommendation text"""
    recommendation_id: int


class GenerateRecommendationResponse(BaseModel):
    """Response with generated texts"""
    recommendation_id: int
    short_description_html: str
    detailed_description_html: str
    model: str = None
    tokens: int = None
    error: str = None


def get_flask_app():
    """Get Flask app from FastAPI state"""
    from agent_service.main import app as fastapi_app
    return fastapi_app.state.flask_app


@router.post("/generate/recommendation-text")
async def generate_recommendation_text(request: GenerateRecommendationRequest) -> Dict[str, Any]:
    """
    Generate user-friendly recommendation texts using LLM
    
    Returns short and detailed HTML descriptions for UI display
    """
    logger.info(f"Generating text for recommendation {request.recommendation_id}")
    
    try:
        # Get Flask app and run within its context
        flask_app = get_flask_app()
        
        with flask_app.app_context():
            # Create generator with database session
            generator = RecommendationGenerator(db.session)
            
            # Generate texts
            result = generator.generate(request.recommendation_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate recommendation text: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendation text: {str(e)}"
        )

