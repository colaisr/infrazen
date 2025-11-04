"""
Health check endpoints
"""
import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from agent_service.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "infrazen-agent",
            "version": settings.VERSION,
            "environment": settings.AGENT_ENV,
            "message": "Agent Service v0.1.0 - Ready for FinOps Assistance"
        }
    )


@router.get("/readiness")
async def readiness_check():
    """Readiness check - validates dependencies"""
    # TODO: Add checks for Redis, LLM provider availability
    checks = {
        "config": True,
        "redis": True,  # Placeholder
        "llm_provider": True  # Placeholder
    }
    
    is_ready = all(checks.values())
    status_code = 200 if is_ready else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "not_ready",
            "checks": checks
        }
    )

