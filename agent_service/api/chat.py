"""
WebSocket chat endpoints for conversational AI
"""
import logging
import json
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket, session: str = Query(None)):
    """
    WebSocket endpoint for chat sessions
    Echo mode for initial testing; will be replaced with LangGraph agent
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established (session: {session})")
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "system",
            "message": "Connected to InfraZen Agent Service (echo mode)",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Echo loop for testing
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received: {data}")
            
            try:
                message = json.loads(data)
                
                # Echo back with metadata
                response = {
                    "type": "echo",
                    "original": message,
                    "timestamp": datetime.utcnow().isoformat(),
                    "session": session
                }
                
                await websocket.send_json(response)
                
            except json.JSONDecodeError:
                # Handle plain text
                await websocket.send_json({
                    "type": "echo",
                    "message": data,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected (session: {session})")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await websocket.close(code=1011, reason=str(e))


@router.post("/start")
async def start_chat_session(request: Dict[str, Any]):
    """
    Create a new chat session
    Returns session ID and context metadata
    """
    # TODO: Implement session creation with Redis
    session_id = f"session_{datetime.utcnow().timestamp()}"
    
    return {
        "session_id": session_id,
        "status": "created",
        "context": request.get("context", {}),
        "created_at": datetime.utcnow().isoformat()
    }

