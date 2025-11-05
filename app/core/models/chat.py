"""
Chat models for recommendation chat sessions and messages.
"""

import enum
from datetime import datetime
from app.core.database import db


class ChatSessionStatus(enum.Enum):
    """Chat session status enum."""
    ACTIVE = 'active'
    ARCHIVED = 'archived'


class ChatMessageRole(enum.Enum):
    """Chat message role enum."""
    USER = 'user'
    ASSISTANT = 'assistant'
    SYSTEM = 'system'


class ChatSession(db.Model):
    """Chat session model."""
    
    __tablename__ = 'chat_sessions'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    recommendation_id = db.Column(db.Integer, db.ForeignKey('optimization_recommendations.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_activity_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    message_count = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.Enum(ChatSessionStatus), nullable=False, default=ChatSessionStatus.ACTIVE)
    
    # Relationships
    user = db.relationship('User', backref='chat_sessions')
    recommendation = db.relationship('OptimizationRecommendation', backref='chat_sessions')
    messages = db.relationship('ChatMessage', backref='session', lazy='dynamic', cascade='all, delete-orphan', order_by='ChatMessage.created_at')
    
    def __repr__(self):
        return f'<ChatSession {self.id} user={self.user_id} rec={self.recommendation_id}>'
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'recommendation_id': self.recommendation_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_activity_at': self.last_activity_at.isoformat() if self.last_activity_at else None,
            'message_count': self.message_count,
            'status': self.status.value if self.status else None
        }


class ChatMessage(db.Model):
    """Chat message model."""
    
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    session_id = db.Column(db.String(36), db.ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.Enum(ChatMessageRole), nullable=False)
    content = db.Column(db.Text, nullable=False)
    tokens = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ChatMessage {self.id} session={self.session_id} role={self.role.value}>'
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'role': self.role.value if self.role else None,
            'content': self.content,
            'tokens': self.tokens,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

