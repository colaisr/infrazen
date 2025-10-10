from datetime import datetime
from app.core.database import db


class UnrecognizedResource(db.Model):
    """
    Model to track resources that appear in billing data but are not recognized/processed
    by our sync logic. This helps identify gaps in our provider coverage.
    """
    __tablename__ = 'unrecognized_resources'

    id = db.Column(db.Integer, primary_key=True)
    
    # Provider and resource identification
    provider_id = db.Column(db.Integer, db.ForeignKey('cloud_providers.id'), nullable=False)
    resource_id = db.Column(db.String(255), nullable=False)
    resource_name = db.Column(db.String(255), nullable=True)
    resource_type = db.Column(db.String(100), nullable=True)  # From billing API
    service_type = db.Column(db.String(100), nullable=True)   # From billing API
    
    # Raw billing data for analysis
    billing_data = db.Column(db.Text, nullable=True)  # JSON string of raw billing item
    
    # User and sync context
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sync_snapshot_id = db.Column(db.Integer, db.ForeignKey('sync_snapshots.id'), nullable=True)
    discovered_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Status tracking
    is_resolved = db.Column(db.Boolean, default=False, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    provider = db.relationship('CloudProvider', backref='unrecognized_resources')
    user = db.relationship('User', foreign_keys=[user_id], backref='discovered_unrecognized_resources')
    resolver = db.relationship('User', foreign_keys=[resolved_by], backref='resolved_unrecognized_resources')
    sync_snapshot = db.relationship('SyncSnapshot', backref='unrecognized_resources')

    def __repr__(self):
        return f'<UnrecognizedResource {self.resource_id}: {self.resource_name}>'

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'provider_id': self.provider_id,
            'resource_id': self.resource_id,
            'resource_name': self.resource_name,
            'resource_type': self.resource_type,
            'service_type': self.service_type,
            'billing_data': self.billing_data,
            'user_id': self.user_id,
            'sync_snapshot_id': self.sync_snapshot_id,
            'discovered_at': self.discovered_at.isoformat() if self.discovered_at else None,
            'is_resolved': self.is_resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolved_by': self.resolved_by,
            'resolution_notes': self.resolution_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'provider': {
                'id': self.provider.id,
                'provider_type': self.provider.provider_type,
                'connection_name': self.provider.connection_name
            } if self.provider else None,
            'user': {
                'id': self.user.id,
                'email': self.user.email,
                'first_name': self.user.first_name,
                'last_name': self.user.last_name
            } if self.user else None
        }
