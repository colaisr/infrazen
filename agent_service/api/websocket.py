"""
WebSocket API for recommendation chat.
"""

import logging
import json
import re
import uuid
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

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


def extract_image_references(message: str) -> Tuple[str, List[str]]:
    """
    Extract image references from message.
    
    Args:
        message: User message potentially containing [image:uuid] references
        
    Returns:
        Tuple of (cleaned_message, list_of_image_ids)
    """
    # Pattern to match [image:uuid]
    pattern = r'\[image:([a-f0-9\-]+)\]'
    image_ids = re.findall(pattern, message)
    
    # Remove image references from message (they're handled separately)
    cleaned_message = re.sub(pattern, '', message).strip()
    
    return cleaned_message, image_ids


async def _handle_chat_connection(
    websocket: WebSocket,
    *,
    user_id: int,
    scenario: str,
    recommendation_id: Optional[int] = None,
    context: Optional[Dict[str, Any]] = None
) -> None:
    session_id = None
    session_manager = get_session_manager(websocket.app.state)
    chat_agent = get_chat_agent(websocket.app.state)

    # Ensure context is immutable dict for storage
    context_payload = context or {}

    try:
        session_id, message_history = session_manager.get_or_create_session(
            user_id=user_id,
            recommendation_id=recommendation_id,
            scenario=scenario,
            context=context_payload
        )

        await manager.connect(session_id, websocket)

        await manager.send_message(session_id, {
            'type': 'system',
            'content': f'Чат-сессия ({scenario}) начата. Загружено сообщений: {len(message_history)}',
            'timestamp': datetime.utcnow().isoformat()
        })

        for msg in message_history:
            await manager.send_message(session_id, {
                'type': msg['role'],
                'content': msg['content'],
                'timestamp': msg['timestamp']
            })

        logger.debug(
            "WebSocket connected: user=%s scenario=%s rec=%s session=%s history=%s",
            user_id,
            scenario,
            recommendation_id,
            session_id,
            len(message_history)
        )

        while True:
            data = await websocket.receive_json()
            message = data.get('content', '')
            if not message:
                continue

            cleaned_message, image_ids = extract_image_references(message)

            image_context = ""
            if image_ids:
                logger.info(f"User message contains {len(image_ids)} image(s): {image_ids}")
                vision_tools = chat_agent.vision_tools

                for image_id in image_ids:
                    try:
                        question = cleaned_message if cleaned_message else (
                            "Что на этом изображении? Какие выводы по расходам или инфраструктуре?"
                        )
                        result = vision_tools.analyze_screenshot(image_id, question, user_id)

                        if result.get('success'):
                            image_context += f"\n\n[Анализ загруженного изображения]:\n{result['analysis']}\n"
                        else:
                            image_context += f"\n\n[Ошибка анализа изображения: {result.get('error', 'Unknown error')}]\n"
                    except Exception as vision_error:  # noqa: BLE001
                        logger.error("Error analyzing image %s: %s", image_id, vision_error, exc_info=True)
                        image_context += "\n\n[Ошибка при обработке изображения]\n"

                if image_context:
                    cleaned_message = f"{image_context}\n\n{cleaned_message if cleaned_message else 'Пользователь загрузил изображение для анализа.'}"

            session_manager.save_message(session_id, 'user', message)

            await manager.send_message(session_id, {
                'type': 'typing',
                'timestamp': datetime.utcnow().isoformat()
            })

            response, tokens = await chat_agent.process_message(
                user_message=cleaned_message,
                user_id=user_id,
                scenario=scenario,
                recommendation_id=recommendation_id,
                context=context_payload,
                chat_history=message_history
            )

            await manager.send_message(session_id, {
                'type': 'assistant',
                'content': response,
                'timestamp': datetime.utcnow().isoformat()
            })

            session_manager.save_message(session_id, 'assistant', response, tokens=tokens)

            message_history.append({
                'role': 'user',
                'content': message,
                'timestamp': datetime.utcnow().isoformat()
            })
            message_history.append({
                'role': 'assistant',
                'content': response,
                'timestamp': datetime.utcnow().isoformat(),
                'tokens': tokens
            })

    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected: session=%s", session_id)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"WebSocket error: {exc}", exc_info=True)
    finally:
        if session_id:
            manager.disconnect(session_id)


@router.websocket("/v1/chat/rec/{rec_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    rec_id: int,
    token: Optional[str] = Query(None)
):
    if not token:
        logger.warning("WebSocket connection rejected: no token provided (rec=%s)", rec_id)
        await websocket.close(code=1008, reason="Authentication required")
        return

    payload = validate_jwt_token(token)
    if not payload:
        logger.warning("WebSocket connection rejected: invalid token (rec=%s)", rec_id)
        await websocket.close(code=1008, reason="Invalid token")
        return

    scenario = payload.get('scenario', 'recommendation')
    if scenario != 'recommendation':
        logger.warning("WebSocket rejected: scenario mismatch (%s != recommendation)", scenario)
        await websocket.close(code=1008, reason="Unsupported scenario for this endpoint")
        return

    token_rec_id = payload.get('recommendation_id')
    if token_rec_id != rec_id:
        logger.warning(
            "WebSocket connection rejected: rec_id mismatch (token=%s, url=%s)",
            token_rec_id,
            rec_id
        )
        await websocket.close(code=1008, reason="Recommendation ID mismatch")
        return

    user_id = payload['user_id']
    context_payload = payload.get('context') or {}

    await _handle_chat_connection(
        websocket,
        user_id=user_id,
        scenario='recommendation',
        recommendation_id=rec_id,
        context=context_payload
    )


@router.websocket("/v1/chat/analytics")
async def websocket_analytics_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    if not token:
        logger.warning("WebSocket analytics rejected: no token provided")
        await websocket.close(code=1008, reason="Authentication required")
        return

    payload = validate_jwt_token(token)
    if not payload:
        logger.warning("WebSocket analytics rejected: invalid token")
        await websocket.close(code=1008, reason="Invalid token")
        return

    scenario = payload.get('scenario', 'recommendation')
    if scenario != 'analytics':
        logger.warning("WebSocket analytics rejected: scenario mismatch (%s)", scenario)
        await websocket.close(code=1008, reason="Unsupported scenario for this endpoint")
        return

    user_id = payload['user_id']
    raw_context = payload.get('context')

    if isinstance(raw_context, str):
        try:
            context_payload = json.loads(raw_context)
        except json.JSONDecodeError:
            context_payload = {'raw': raw_context}
    else:
        context_payload = raw_context or {}

    await _handle_chat_connection(
        websocket,
        user_id=user_id,
        scenario='analytics',
        recommendation_id=None,
        context=context_payload
    )


@router.get("/v1/chat/connections")
async def get_connection_count():
    """Get count of active WebSocket connections."""
    return {
        'active_connections': manager.get_connection_count(),
        'timestamp': datetime.utcnow().isoformat()
    }

