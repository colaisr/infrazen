"""
Chat session management for loading and saving chat history.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict

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
        recommendation_id: int
    ) -> tuple[str, List[Dict]]:
        """
        Get existing session or create a new one.
        
        Args:
            user_id: User ID
            recommendation_id: Recommendation ID
            
        Returns:
            Tuple of (session_id, message_history)
            message_history is a list of dicts: [{role, content, timestamp}, ...]
        """
        logger.info(f"DB: Getting session for user_id={user_id}, rec_id={recommendation_id}")
        
        with self.flask_app.app_context():
            from app.core.models import ChatSession, ChatMessage, db, ChatSessionStatus
            
            # Use the Enum object for querying, not a raw string
            session = db.session.query(ChatSession).filter_by(
                user_id=user_id,
                recommendation_id=recommendation_id,
                status=ChatSessionStatus.ACTIVE
            ).first()
            
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
                
                logger.info(f"Loaded existing session: {session.id} (user={user_id}, rec={recommendation_id}, messages={len(message_history)})")
                return session.id, message_history
            else:
                # Create new session
                session_id = str(uuid.uuid4())
                
                new_session = ChatSession(
                    id=session_id,
                    user_id=user_id,
                    recommendation_id=recommendation_id,
                    created_at=datetime.utcnow(),
                    last_activity_at=datetime.utcnow(),
                    message_count=0,
                    status=ChatSessionStatus.ACTIVE
                )
                
                db.session.add(new_session)
                db.session.commit()
                
                logger.info(f"Created new session: {session_id} (user={user_id}, rec={recommendation_id})")
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

