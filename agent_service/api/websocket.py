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
from agent_service.core.session_manager import SessionManager
from agent_service.agents import ChatAgent

logger = logging.getLogger(__name__)

router = APIRouter()

# Singletons will be initialized on first use
_session_manager: Optional[SessionManager] = None
_chat_agent: Optional[ChatAgent] = None


def get_session_manager(app_state) -> SessionManager:
    """Get or create session manager singleton."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(app_state.flask_app)
    return _session_manager


def get_chat_agent(app_state) -> ChatAgent:
    """Get or create chat agent singleton."""
    global _chat_agent
    if _chat_agent is None:
        _chat_agent = ChatAgent(app_state.flask_app)
    return _chat_agent


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
    user_id = None
    
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
        
        # Get session manager and chat agent from app state
        session_manager = get_session_manager(websocket.app.state)
        chat_agent = get_chat_agent(websocket.app.state)
        
        # Get or create session and load history
        session_id, message_history = session_manager.get_or_create_session(user_id, rec_id)
        
        # Accept connection
        await manager.connect(session_id, websocket)
        
        # Send system message with session info
        await manager.send_message(session_id, {
            'type': 'system',
            'content': f'Чат-сессия начата. Загружено сообщений: {len(message_history)}',
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Send message history
        for msg in message_history:
            await manager.send_message(session_id, {
                'type': msg['role'],
                'content': msg['content'],
                'timestamp': msg['timestamp']
            })
        
        logger.info(f"WebSocket connected: user={user_id}, rec={rec_id}, session={session_id}, history={len(message_history)}")
        
        # Handle incoming messages
        while True:
            data = await websocket.receive_json()
            
            logger.debug(f"Received message from session {session_id}: {data}")
            
            # Parse message
            message = data.get('content', '')
            
            if not message:
                continue
            
            # Save user message to DB
            session_manager.save_message(session_id, 'user', message)
            
            # Send typing indicator
            await manager.send_message(session_id, {
                'type': 'typing',
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Process message with chat agent
            response, tokens = await chat_agent.process_message(
                user_message=message,
                recommendation_id=rec_id,
                chat_history=message_history
            )
            
            await manager.send_message(session_id, {
                'type': 'assistant',
                'content': response,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Save assistant response to DB with token count
            session_manager.save_message(session_id, 'assistant', response, tokens=tokens)
            
            # Add to message history for next iteration
            message_history.append({'role': 'user', 'content': message, 'timestamp': datetime.utcnow().isoformat()})
            message_history.append({'role': 'assistant', 'content': response, 'timestamp': datetime.utcnow().isoformat(), 'tokens': tokens})
            
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

