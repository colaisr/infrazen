"""
User Provider Preference Model - Manages which providers users want to include in recommendations
"""
from datetime import datetime
from app.core.database import db
from .base import BaseModel


class UserProviderPreference(BaseModel):
    """User preferences for which providers to include in recommendations comparison"""
    
    __tablename__ = 'user_provider_preferences'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    provider_type = db.Column(db.String(50), nullable=False, index=True)  # 'beget', 'selectel', 'yandex', etc.
    is_enabled = db.Column(db.Boolean, default=True, nullable=False)  # Whether to include this provider in recommendations
    
    # Relationships
    user = db.relationship('User', backref='provider_preferences', lazy=True)
    
    # Composite unique constraint (one preference per user per provider)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'provider_type', name='uq_user_provider'),
        db.Index('idx_user_provider_enabled', 'user_id', 'provider_type', 'is_enabled'),
    )
    
    def __repr__(self):
        return f'<UserProviderPreference user_id={self.user_id} provider={self.provider_type} enabled={self.is_enabled}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'provider_type': self.provider_type,
            'is_enabled': self.is_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_enabled_providers_for_user(cls, user_id):
        """Get list of enabled provider types for a user"""
        preferences = cls.query.filter_by(user_id=user_id, is_enabled=True).all()
        return [pref.provider_type for pref in preferences]
    
    @classmethod
    def get_all_preferences_for_user(cls, user_id):
        """Get all provider preferences for a user"""
        return cls.query.filter_by(user_id=user_id).all()
    
    @classmethod
    def set_provider_enabled(cls, user_id, provider_type, is_enabled):
        """Set provider enabled status for a user"""
        preference = cls.query.filter_by(user_id=user_id, provider_type=provider_type).first()
        
        if preference:
            preference.is_enabled = is_enabled
            preference.updated_at = datetime.utcnow()
        else:
            # Create new preference if it doesn't exist
            preference = cls(
                user_id=user_id,
                provider_type=provider_type,
                is_enabled=is_enabled
            )
            db.session.add(preference)
        
        db.session.commit()
        return preference
    
    @classmethod
    def initialize_for_user(cls, user_id, provider_types=None):
        """Initialize provider preferences for a new user with all providers enabled"""
        from .provider_catalog import ProviderCatalog
        
        # Get all available providers from catalog if not specified
        if provider_types is None:
            catalog_providers = ProviderCatalog.query.filter_by(is_enabled=True).all()
            provider_types = [p.provider_type for p in catalog_providers]
        
        # Create preferences for each provider (all enabled by default)
        created_prefs = []
        for provider_type in provider_types:
            # Check if preference already exists
            existing = cls.query.filter_by(user_id=user_id, provider_type=provider_type).first()
            if not existing:
                pref = cls(
                    user_id=user_id,
                    provider_type=provider_type,
                    is_enabled=True  # Default: all providers enabled
                )
                db.session.add(pref)
                created_prefs.append(pref)
        
        if created_prefs:
            db.session.commit()
        
        return created_prefs

