"""
Cloud provider model for managing provider connections
"""
import json
from app.core.models import db
from .base import BaseModel

class CloudProvider(BaseModel):
    """Model for cloud provider connections"""
    __tablename__ = 'cloud_providers'
    
    # User relationship
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Provider identification
    provider_type = db.Column(db.String(50), nullable=False, index=True)  # e.g., 'beget', 'yandex', 'aws'
    connection_name = db.Column(db.String(100), nullable=False)
    account_id = db.Column(db.String(100), nullable=False)  # Provider account identifier
    
    # Connection details
    api_endpoint = db.Column(db.String(255))
    credentials = db.Column(db.Text, nullable=False)  # JSON-encoded credentials
    
    # Status and metadata
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    last_sync = db.Column(db.DateTime)
    sync_status = db.Column(db.String(20), default='pending')  # pending, syncing, success, error
    sync_error = db.Column(db.Text)  # Last sync error message
    
    # Sync configuration
    auto_sync = db.Column(db.Boolean, default=True, nullable=False)
    sync_interval = db.Column(db.String(20), default='daily')  # hourly, daily, weekly, manual
    
    # Provider-specific metadata
    provider_metadata = db.Column(db.Text)  # JSON-encoded provider-specific data
    
    # Relationships
    resources = db.relationship('Resource', backref='provider', lazy=True, cascade='all, delete-orphan')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('user_id', 'connection_name', name='unique_user_connection'),
        db.UniqueConstraint('user_id', 'provider_type', 'account_id', name='unique_user_provider_account'),
    )
    
    def get_credentials(self):
        """Get parsed credentials"""
        try:
            return json.loads(self.credentials) if self.credentials else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_credentials(self, credentials_dict):
        """Set credentials from dictionary"""
        self.credentials = json.dumps(credentials_dict)
    
    def to_dict(self):
        """Convert provider to dictionary (excluding sensitive credentials)"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'provider_type': self.provider_type,
            'connection_name': self.connection_name,
            'account_id': self.account_id,
            'api_endpoint': self.api_endpoint,
            'is_active': self.is_active,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'sync_status': self.sync_status,
            'sync_error': self.sync_error,
            'provider_metadata': json.loads(self.provider_metadata) if self.provider_metadata else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<CloudProvider {self.provider_type}:{self.connection_name}>'
