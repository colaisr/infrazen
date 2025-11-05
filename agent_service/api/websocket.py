"""
WebSocket API for recommendation chat.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from pydantic import BaseModel

from agent_service.auth import validate_jwt_token
from agent_service.core.connection_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str
    content: str


@router.websocket("/v1/chat/rec/{rec_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    rec_id: int,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for recommendation chat.
    
    Args:
        websocket: WebSocket connection
        rec_id: Recommendation ID
        token: JWT token for authentication
    """
    session_id = None
    
    try:
        # Validate JWT token
        if not token:
            logger.warning(f"WebSocket connection rejected: no token provided (rec={rec_id})")
            await websocket.close(code=1008, reason="Authentication required")
            return
            
        payload = validate_jwt_token(token)
        if not payload:
            logger.warning(f"WebSocket connection rejected: invalid token (rec={rec_id})")
            await websocket.close(code=1008, reason="Invalid token")
            return
            
        user_id = payload['user_id']
        token_rec_id = payload['recommendation_id']
        
        # Verify recommendation ID matches token
        if token_rec_id != rec_id:
            logger.warning(f"WebSocket connection rejected: rec_id mismatch (token={token_rec_id}, url={rec_id})")
            await websocket.close(code=1008, reason="Recommendation ID mismatch")
            return
            
        # Generate session ID (will be replaced with DB lookup/create in task 1.8)
        session_id = f"session_{user_id}_{rec_id}_{uuid.uuid4().hex[:8]}"
        
        # Accept connection
        await manager.connect(session_id, websocket)
        
        # Send welcome message
        await manager.send_message(session_id, {
            'type': 'system',
            'content': f'Чат-сессия начата. Session ID: {session_id}',
            'timestamp': datetime.utcnow().isoformat()
        })
        
        logger.info(f"WebSocket connected: user={user_id}, rec={rec_id}, session={session_id}")
        
        # Handle incoming messages
        while True:
            data = await websocket.receive_json()
            
            logger.debug(f"Received message from session {session_id}: {data}")
            
            # Parse message
            message = data.get('content', '')
            
            if not message:
                continue
                
            # Echo back for now (will be replaced with agent in task 1.10)
            await manager.send_message(session_id, {
                'type': 'assistant',
                'content': f'Echo: {message}',
                'timestamp': datetime.utcnow().isoformat()
            })
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session={session_id}")
        
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        
    finally:
        if session_id:
            manager.disconnect(session_id)


@router.get("/v1/chat/connections")
async def get_connection_count():
    """Get count of active WebSocket connections."""
    return {
        'active_connections': manager.get_connection_count(),
        'timestamp': datetime.utcnow().isoformat()
    }

