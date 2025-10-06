"""
User model for authentication and user management
"""
from app.core.models import db
from .base import BaseModel
import json

class User(BaseModel):
    """User model for authentication with Google OAuth integration and roles"""
    __tablename__ = 'users'
    
    # Basic user information
    username = db.Column(db.String(80), unique=True, nullable=True, index=True)  # Made nullable for Google OAuth users
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)  # Made nullable for Google OAuth users
    
    # Google OAuth integration
    google_id = db.Column(db.String(100), unique=True, nullable=True, index=True)
    google_picture = db.Column(db.String(500))  # Profile picture URL
    google_verified_email = db.Column(db.Boolean, default=False)
    google_locale = db.Column(db.String(10))  # User's locale from Google
    
    # User profile
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    company = db.Column(db.String(100))
    
    # Role and permissions system
    role = db.Column(db.String(20), default='user', nullable=False, index=True)  # user, admin, super_admin
    permissions = db.Column(db.Text)  # JSON-encoded custom permissions
    
    # Account status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    last_login = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, default=0)
    
    # Admin functionality
    created_by_admin = db.Column(db.Boolean, default=False)  # If user was created by admin
    admin_notes = db.Column(db.Text)  # Admin notes about the user
    
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
            'google_id': self.google_id,
            'google_picture': self.google_picture,
            'role': self.role,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'login_count': self.login_count,
            'timezone': self.timezone,
            'currency': self.currency,
            'language': self.language,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def get_permissions(self):
        """Get user permissions as dictionary"""
        if self.permissions:
            try:
                return json.loads(self.permissions)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def set_permissions(self, permissions_dict):
        """Set user permissions from dictionary"""
        self.permissions = json.dumps(permissions_dict)
    
    def has_permission(self, permission):
        """Check if user has specific permission"""
        user_permissions = self.get_permissions()
        return user_permissions.get(permission, False)
    
    def is_admin(self):
        """Check if user is admin or super_admin"""
        return self.role in ['admin', 'super_admin']
    
    def is_super_admin(self):
        """Check if user is super_admin"""
        return self.role == 'super_admin'
    
    def can_impersonate(self):
        """Check if user can impersonate other users"""
        return self.is_admin() and self.has_permission('impersonate_users')
    
    def can_manage_users(self):
        """Check if user can manage other users"""
        return self.is_admin() and self.has_permission('manage_users')
    
    def update_login_info(self):
        """Update login information"""
        from datetime import datetime
        self.last_login = datetime.now()
        self.login_count += 1
        db.session.commit()
    
    @classmethod
    def find_by_google_id(cls, google_id):
        """Find user by Google ID"""
        return cls.query.filter_by(google_id=google_id).first()
    
    @classmethod
    def find_by_email(cls, email):
        """Find user by email"""
        return cls.query.filter_by(email=email).first()
    
    @classmethod
    def create_from_google(cls, google_data):
        """Create user from Google OAuth data"""
        user = cls(
            google_id=google_data.get('sub'),
            email=google_data.get('email'),
            first_name=google_data.get('given_name', ''),
            last_name=google_data.get('family_name', ''),
            google_picture=google_data.get('picture', ''),
            google_verified_email=google_data.get('email_verified', False),
            google_locale=google_data.get('locale', ''),
            is_verified=google_data.get('email_verified', False),
            role='user'  # Default role for new users
        )
        
        # Set username from email if not provided
        if not user.username:
            user.username = user.email.split('@')[0]
        
        db.session.add(user)
        db.session.commit()
        return user
    
    def __repr__(self):
        return f'<User {self.username or self.email}>'
