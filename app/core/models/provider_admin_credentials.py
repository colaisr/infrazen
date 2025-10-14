"""
Provider Admin Credentials Model
Stores system-level credentials for fetching pricing data from providers
"""
from datetime import datetime
from app.core.database import db
import json
import base64
from cryptography.fernet import Fernet
import os

class ProviderAdminCredentials(db.Model):
    """
    System-level credentials for provider pricing data access
    Used by admin to configure how the system fetches pricing from each provider
    """
    __tablename__ = 'provider_admin_credentials'
    
    id = db.Column(db.Integer, primary_key=True)
    provider_type = db.Column(db.String(50), unique=True, nullable=False, index=True)  # 'beget', 'selectel', etc.
    
    # Credential information
    credential_type = db.Column(db.String(50), nullable=False)  # 'bearer_token', 'session_cookie', 'api_key', 'basic_auth', 'jwt'
    credentials = db.Column(db.Text, nullable=False)  # Encrypted JSON containing credential data
    
    # Metadata
    description = db.Column(db.Text)  # Admin notes about these credentials
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)  # Optional expiration
    last_used = db.Column(db.DateTime, nullable=True)  # Last time credentials were used
    
    # Additional configuration
    config_data = db.Column(db.JSON, default={})  # Extra configuration (headers, endpoints, etc.)
    
    def __repr__(self):
        return f'<ProviderAdminCredentials {self.provider_type} ({self.credential_type})>'
    
    @staticmethod
    def _get_encryption_key():
        """Get or generate encryption key for credentials"""
        # In production, this should be stored in environment variables
        key = os.getenv('CREDENTIALS_ENCRYPTION_KEY')
        if not key:
            # Generate a proper 32-byte key for development
            # In production, this should be pre-configured and stored securely
            key = Fernet.generate_key()
        return key
    
    def encrypt_credentials(self, credentials_dict: dict) -> str:
        """Encrypt credentials dictionary and return encrypted string"""
        try:
            key = self._get_encryption_key()
            cipher = Fernet(key)
            
            # Convert dict to JSON string
            credentials_json = json.dumps(credentials_dict)
            
            # Encrypt
            encrypted = cipher.encrypt(credentials_json.encode())
            
            # Return base64 encoded string
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            raise ValueError(f"Failed to encrypt credentials: {str(e)}")
    
    def decrypt_credentials(self) -> dict:
        """Decrypt stored credentials and return as dictionary"""
        try:
            if not self.credentials:
                return {}
            
            key = self._get_encryption_key()
            cipher = Fernet(key)
            
            # Decode base64
            encrypted = base64.urlsafe_b64decode(self.credentials.encode())
            
            # Decrypt
            decrypted = cipher.decrypt(encrypted)
            
            # Parse JSON
            return json.loads(decrypted.decode())
        except Exception as e:
            raise ValueError(f"Failed to decrypt credentials: {str(e)}")
    
    def set_credentials(self, credentials_dict: dict):
        """Set credentials by encrypting the provided dictionary"""
        self.credentials = self.encrypt_credentials(credentials_dict)
        self.updated_at = datetime.utcnow()
    
    def get_credentials(self) -> dict:
        """Get decrypted credentials as dictionary"""
        return self.decrypt_credentials()
    
    def mark_used(self):
        """Mark credentials as recently used"""
        self.last_used = datetime.utcnow()
    
    def is_expired(self) -> bool:
        """Check if credentials have expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self, include_credentials=False):
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'provider_type': self.provider_type,
            'credential_type': self.credential_type,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'is_expired': self.is_expired(),
            'config_data': self.config_data
        }
        
        # Only include decrypted credentials if explicitly requested
        if include_credentials:
            try:
                data['credentials'] = self.get_credentials()
            except Exception as e:
                data['credentials'] = {'error': str(e)}
        
        return data

