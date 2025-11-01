"""
User model for authentication and user management
"""
from app.core.models import db
from .base import BaseModel
import json
from werkzeug.security import generate_password_hash, check_password_hash

class User(BaseModel):
    """User model for authentication with Google OAuth integration and roles"""
    __tablename__ = 'users'
    
    # Valid user roles
    VALID_ROLES = ['user', 'admin', 'super_admin', 'demouser']
    
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
    role = db.Column(db.String(20), default='user', nullable=False, index=True)  # user, admin, super_admin, demouser
    permissions = db.Column(db.Text)  # JSON-encoded custom permissions
    
    # Account status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    email_confirmed = db.Column(db.Boolean, default=False, nullable=False)  # Email confirmation status
    email_confirmation_token = db.Column(db.String(255), nullable=True)  # Token for email confirmation
    email_confirmation_sent_at = db.Column(db.DateTime, nullable=True)  # When confirmation email was sent
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
            'is_demo_user': self.is_demo_user(),
            'can_modify_data': self.can_modify_data(),
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'email_confirmed': self.email_confirmed,
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
    
    def is_demo_user(self):
        """Check if user is a demo user (read-only)"""
        return self.role == 'demouser'
    
    def can_modify_data(self):
        """Check if user can modify data (create, update, delete resources/providers)"""
        return not self.is_demo_user()
    
    def is_excluded_from_stats(self):
        """Check if user should be excluded from statistics and analytics"""
        return self.is_demo_user()
    
    def is_excluded_from_admin_list(self):
        """Check if user should be excluded from admin user management lists"""
        return self.is_demo_user()
    
    def set_password(self, password):
        """Set password for user"""
        self.password_hash = generate_password_hash(password)
        db.session.commit()
    
    def check_password(self, password):
        """Check if provided password is correct"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def has_password(self):
        """Check if user has a password set"""
        return bool(self.password_hash)
    
    def can_login_with_password(self):
        """Check if user can login with password"""
        return self.has_password() and self.is_active
    
    def can_login_with_google(self):
        """Check if user can login with Google OAuth"""
        return bool(self.google_id) and self.is_active
    
    def update_login_info(self):
        """Update login information"""
        from datetime import datetime
        self.last_login = datetime.now()
        self.login_count += 1
        db.session.commit()
    
    def generate_email_confirmation_token(self):
        """Generate a unique token for email confirmation"""
        import secrets
        from datetime import datetime
        self.email_confirmation_token = secrets.token_urlsafe(32)
        self.email_confirmation_sent_at = datetime.now()
        db.session.commit()
        return self.email_confirmation_token
    
    def confirm_email(self, token):
        """Confirm email using token"""
        if self.email_confirmation_token == token:
            self.email_confirmed = True
            self.email_confirmation_token = None  # Clear token after use
            db.session.commit()
            return True
        return False
    
    def is_email_confirmed(self):
        """Check if user's email is confirmed"""
        return self.email_confirmed or self.google_verified_email
    
    @classmethod
    def find_by_google_id(cls, google_id):
        """Find user by Google ID"""
        return cls.query.filter_by(google_id=google_id).first()
    
    @classmethod
    def find_by_email(cls, email):
        """Find user by email"""
        return cls.query.filter_by(email=email).first()
    
    @classmethod
    def find_by_username(cls, username):
        """Find user by username"""
        return cls.query.filter_by(username=username).first()
    
    @classmethod
    def find_by_username_or_email(cls, identifier):
        """Find user by username or email"""
        return cls.query.filter(
            db.or_(
                cls.username == identifier,
                cls.email == identifier
            )
        ).first()
    
    @classmethod
    def create_from_google(cls, google_data):
        """Create user from Google OAuth data"""
        email_verified = google_data.get('email_verified', False)
        user = cls(
            google_id=google_data.get('sub'),
            email=google_data.get('email'),
            first_name=google_data.get('given_name', ''),
            last_name=google_data.get('family_name', ''),
            google_picture=google_data.get('picture', ''),
            google_verified_email=email_verified,
            google_locale=google_data.get('locale', ''),
            is_verified=email_verified,
            email_confirmed=email_verified,  # Auto-confirm email for Google OAuth users
            role='user'  # Default role for new users
        )
        
        # No username needed - email is the primary identifier
        
        db.session.add(user)
        db.session.commit()
        
        # Initialize provider preferences for new user (all providers enabled by default)
        try:
            from .user_provider_preference import UserProviderPreference
            UserProviderPreference.initialize_for_user(user.id)
        except Exception:
            # Don't fail user creation if preference initialization fails
            pass
        
        return user
    
    def get_initials(self):
        """Get user initials from first and last name"""
        if self.first_name and self.last_name:
            return f"{self.first_name[0].upper()}{self.last_name[0].upper()}"
        elif self.first_name:
            return self.first_name[0].upper()
        elif self.last_name:
            return self.last_name[0].upper()
        elif self.email:
            # Fallback to email prefix
            return self.email.split('@')[0][0].upper()
        else:
            return "U"
    
    def __repr__(self):
        return f'<User {self.email}>'
