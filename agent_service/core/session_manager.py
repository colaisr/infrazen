"""
Chat session management for loading and saving chat history.
"""

import logging
import uuid
import json
from datetime import datetime
from typing import List, Optional, Dict, Union

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages chat sessions and message history."""
    
    def __init__(self, flask_app):
        """
        Initialize session manager with Flask app context.
        
        Args:
            flask_app: Flask application instance for database access
        """
        self.flask_app = flask_app
        
    def get_or_create_session(
        self,
        user_id: int,
        recommendation_id: Optional[int],
        scenario: str = 'recommendation',
        context: Optional[Union[Dict, str]] = None
    ) -> tuple[str, List[Dict]]:
        """
        Get existing session or create a new one.
        
        Args:
            user_id: User ID
            recommendation_id: Recommendation ID (required for recommendation scenario)
            scenario: Chat scenario identifier ('recommendation', 'analytics', ...)
            context: Optional context payload for non-recommendation scenarios
            
        Returns:
            Tuple of (session_id, message_history)
            message_history is a list of dicts: [{role, content, timestamp}, ...]
        """
        logger.info(
            "DB: Getting session for user_id=%s, scenario=%s, rec_id=%s",
            user_id,
            scenario,
            recommendation_id,
        )
        
        with self.flask_app.app_context():
            from app.core.models import ChatSession, ChatMessage, db, ChatSessionStatus
            
            # Normalize context to string for persistence
            normalized_context = None
            if isinstance(context, dict):
                normalized_context = json.dumps(context, ensure_ascii=False, sort_keys=True)
            elif context is not None:
                normalized_context = str(context)

            query = db.session.query(ChatSession).filter_by(
                user_id=user_id,
                scenario=scenario,
                status=ChatSessionStatus.ACTIVE
            )

            if scenario == 'recommendation':
                query = query.filter_by(recommendation_id=recommendation_id)
            else:
                query = query.filter(ChatSession.recommendation_id.is_(None))
                if normalized_context is None:
                    query = query.filter(ChatSession.context.is_(None))
                else:
                    query = query.filter(ChatSession.context == normalized_context)

            session = query.first()
            
            if session:
                # Load message history (last 10 messages)
                messages = ChatMessage.query.filter_by(
                    session_id=session.id
                ).order_by(ChatMessage.created_at.desc()).limit(10).all()
                
                # Reverse to chronological order
                messages = list(reversed(messages))
                
                message_history = [
                    {
                        'role': msg.role.value if hasattr(msg.role, 'value') else msg.role,
                        'content': msg.content,
                        'timestamp': msg.created_at.isoformat() if msg.created_at else None,
                        'tokens': msg.tokens
                    }
                    for msg in messages
                ]
                
                logger.info(
                    "Loaded existing session: %s (user=%s, scenario=%s, rec=%s, messages=%s)",
                    session.id,
                    user_id,
                    scenario,
                    recommendation_id,
                    len(message_history)
                )
                return session.id, message_history
            else:
                # Create new session
                session_id = str(uuid.uuid4())
                
                new_session = ChatSession(
                    id=session_id,
                    user_id=user_id,
                    recommendation_id=recommendation_id if scenario == 'recommendation' else None,
                    scenario=scenario,
                    context=normalized_context,
                    created_at=datetime.utcnow(),
                    last_activity_at=datetime.utcnow(),
                    message_count=0,
                    status=ChatSessionStatus.ACTIVE
                )
                
                db.session.add(new_session)
                db.session.commit()
                
                logger.info(
                    "Created new session: %s (user=%s, scenario=%s, rec=%s)",
                    session_id,
                    user_id,
                    scenario,
                    recommendation_id
                )
                return session_id, []
                
    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tokens: Optional[int] = None
    ) -> bool:
        """
        Save a message to the database.
        
        Args:
            session_id: Session ID
            role: Message role (user, assistant, system)
            content: Message content
            tokens: Token count (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.flask_app.app_context():
                from app.core.models import ChatSession, ChatMessage, db, ChatMessageRole
                
                # Verify session exists
                session = ChatSession.query.filter_by(id=session_id).first()
                if not session:
                    logger.warning(f"Session not found: {session_id}")
                    return False
                
                # Convert role string to enum
                try:
                    role_enum = ChatMessageRole[role.upper()]
                except KeyError:
                    logger.warning(f"Invalid role: {role}")
                    role_enum = ChatMessageRole.USER
                
                # Create message
                message = ChatMessage(
                    session_id=session_id,
                    role=role_enum,
                    content=content,
                    tokens=tokens,
                    created_at=datetime.utcnow()
                )
                
                db.session.add(message)
                
                # Update session
                session.message_count += 1
                session.last_activity_at = datetime.utcnow()
                
                db.session.commit()
                
                logger.debug(f"Saved message to session {session_id}: role={role}, tokens={tokens}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving message to session {session_id}: {e}", exc_info=True)
            return False
            
    def archive_session(self, session_id: str) -> bool:
        """
        Archive a session (mark as inactive).
        
        Args:
            session_id: Session ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.flask_app.app_context():
                from app.core.models import ChatSession, db, ChatSessionStatus
                
                session = ChatSession.query.filter_by(id=session_id).first()
                if not session:
                    logger.warning(f"Session not found: {session_id}")
                    return False
                    
                session.status = ChatSessionStatus.ARCHIVED
                session.last_activity_at = datetime.utcnow()
                
                db.session.commit()
                
                logger.info(f"Archived session: {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error archiving session {session_id}: {e}", exc_info=True)
            return False
            
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """
        Get session information.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session info dict or None if not found
        """
        try:
            with self.flask_app.app_context():
                from app.core.models import ChatSession
                
                session = ChatSession.query.filter_by(id=session_id).first()
                if not session:
                    return None
                    
                return session.to_dict()
                
        except Exception as e:
            logger.error(f"Error getting session info {session_id}: {e}", exc_info=True)
            return None

