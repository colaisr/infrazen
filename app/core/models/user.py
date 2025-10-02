"""
User model for authentication and user management
"""
from app.core.models import db
from .base import BaseModel

class User(BaseModel):
    """User model for authentication"""
    __tablename__ = 'users'
    
    # Basic user information
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # User profile
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    company = db.Column(db.String(100))
    
    # Account status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    last_login = db.Column(db.DateTime)
    
    # Preferences
    timezone = db.Column(db.String(50), default='UTC')
    currency = db.Column(db.String(3), default='RUB')
    language = db.Column(db.String(5), default='ru')
    
    # Relationships
    providers = db.relationship('CloudProvider', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert user to dictionary (excluding sensitive data)"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'company': self.company,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'timezone': self.timezone,
            'currency': self.currency,
            'language': self.language,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<User {self.username}>'
