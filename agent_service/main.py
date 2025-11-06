"""
Agent Service main application entry point
FastAPI + WebSocket for conversational FinOps assistance
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agent_service.api import health, chat, recommendations, websocket, upload
from agent_service.core.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Reduce noisy SQLAlchemy engine logs
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info(f"Starting Agent Service v{settings.VERSION} in {settings.AGENT_ENV} mode")
    logger.info(f"Internal API base: {settings.AGENT_INTERNAL_API_BASE}")
    
    # Initialize InfraZen app context for database access
    try:
        from app import create_app
        flask_app = create_app()
        app.state.flask_app = flask_app
        logger.info("✓ Database connection initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    logger.info("Shutting down Agent Service")


# Create FastAPI app
app = FastAPI(
    title="InfraZen Agent Service",
    description="Conversational FinOps Assistant with LLM-powered recommendations",
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/v1", tags=["health"])
app.include_router(chat.router, prefix="/v1/chat", tags=["chat"])
app.include_router(websocket.router, tags=["websocket"])  # WebSocket routes (no prefix, full path in router)
app.include_router(recommendations.router, prefix="/v1", tags=["recommendations"])
app.include_router(upload.router, tags=["upload"])  # Image upload for vision


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "InfraZen Agent Service",
        "version": settings.VERSION,
        "status": "operational"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "agent_service.main:app",
        host="0.0.0.0",
        port=settings.AGENT_PORT,
        reload=settings.AGENT_ENV == "dev",
        log_level=settings.LOG_LEVEL.lower()
    )

