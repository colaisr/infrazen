"""
Provider Catalog Model - Manages available cloud providers for price comparison
"""
from datetime import datetime
from app.core.database import db


class ProviderCatalog(db.Model):
    """Catalog of available cloud providers for price comparison"""
    
    __tablename__ = 'provider_catalog'
    
    id = db.Column(db.Integer, primary_key=True)
    provider_type = db.Column(db.String(50), nullable=False, unique=True)  # 'beget', 'selectel', 'aws', etc.
    display_name = db.Column(db.String(100), nullable=False)  # 'Beget', 'Selectel', 'AWS', etc.
    description = db.Column(db.Text)  # Provider description
    logo_url = db.Column(db.String(255))  # Path to provider logo
    
    # Pricing configuration
    is_enabled = db.Column(db.Boolean, default=True)  # Whether provider is available for price comparison
    has_pricing_api = db.Column(db.Boolean, default=False)  # Whether provider has official pricing API
    pricing_method = db.Column(db.String(50), default='scraping')  # 'api', 'scraping', 'billing', 'manual'
    
    # Sync status
    last_price_sync = db.Column(db.DateTime)  # Last successful price sync
    sync_status = db.Column(db.String(20), default='never')  # 'never', 'success', 'failed', 'in_progress'
    sync_error = db.Column(db.Text)  # Last sync error message
    
    # Metadata
    website_url = db.Column(db.String(255))  # Provider website
    documentation_url = db.Column(db.String(255))  # API documentation
    supported_regions = db.Column(db.Text)  # JSON list of supported regions
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ProviderCatalog {self.provider_type}: {self.display_name}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'provider_type': self.provider_type,
            'display_name': self.display_name,
            'description': self.description,
            'logo_url': self.logo_url,
            'is_enabled': self.is_enabled,
            'has_pricing_api': self.has_pricing_api,
            'pricing_method': self.pricing_method,
            'last_price_sync': self.last_price_sync.isoformat() if self.last_price_sync else None,
            'sync_status': self.sync_status,
            'sync_error': self.sync_error,
            'website_url': self.website_url,
            'documentation_url': self.documentation_url,
            'supported_regions': self.supported_regions,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
