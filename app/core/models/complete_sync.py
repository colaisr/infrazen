"""
Complete Sync models for tracking unified synchronization across all user providers
"""
import json
from datetime import datetime
from app.core.models import db
from .base import BaseModel

class CompleteSync(BaseModel):
    """Model for tracking complete sync operations across all user providers"""
    __tablename__ = 'complete_syncs'
    
    # User relationship
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Sync metadata
    sync_type = db.Column(db.String(20), nullable=False, default='manual')  # manual, scheduled, api
    sync_status = db.Column(db.String(20), nullable=False, default='running')  # running, success, error, partial
    sync_started_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    sync_completed_at = db.Column(db.DateTime)
    sync_duration_seconds = db.Column(db.Integer)  # Duration in seconds
    
    # Aggregated statistics
    total_providers_synced = db.Column(db.Integer, default=0)
    successful_providers = db.Column(db.Integer, default=0)
    failed_providers = db.Column(db.Integer, default=0)
    total_resources_found = db.Column(db.Integer, default=0)
    total_monthly_cost = db.Column(db.Float, default=0.0)
    total_daily_cost = db.Column(db.Float, default=0.0)
    
    # Cost breakdown by provider
    cost_by_provider = db.Column(db.Text)  # JSON: {"beget": 660.0, "selectel": 1200.0}
    resources_by_provider = db.Column(db.Text)  # JSON: {"beget": 9, "selectel": 15}
    
    # Error handling
    error_message = db.Column(db.Text)
    error_details = db.Column(db.Text)  # JSON with detailed error info
    
    # Sync configuration
    sync_config = db.Column(db.Text)  # JSON with sync parameters
    
    # Relationships
    provider_syncs = db.relationship('ProviderSyncReference', backref='complete_sync', lazy=True, cascade='all, delete-orphan')
    
    def get_cost_by_provider(self):
        """Get parsed cost breakdown by provider"""
        try:
            return json.loads(self.cost_by_provider) if self.cost_by_provider else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_cost_by_provider(self, cost_dict):
        """Set cost breakdown by provider from dictionary"""
        self.cost_by_provider = json.dumps(cost_dict)
    
    def get_resources_by_provider(self):
        """Get parsed resources breakdown by provider"""
        try:
            return json.loads(self.resources_by_provider) if self.resources_by_provider else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_resources_by_provider(self, resources_dict):
        """Set resources breakdown by provider from dictionary"""
        self.resources_by_provider = json.dumps(resources_dict)
    
    def get_sync_config(self):
        """Get parsed sync configuration"""
        try:
            return json.loads(self.sync_config) if self.sync_config else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_sync_config(self, config_dict):
        """Set sync configuration from dictionary"""
        self.sync_config = json.dumps(config_dict)
    
    def get_error_details(self):
        """Get parsed error details"""
        try:
            return json.loads(self.error_details) if self.error_details else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_error_details(self, error_dict):
        """Set error details from dictionary"""
        self.error_details = json.dumps(error_dict)
    
    def calculate_duration(self):
        """Calculate and set sync duration"""
        if self.sync_completed_at and self.sync_started_at:
            duration = self.sync_completed_at - self.sync_started_at
            self.sync_duration_seconds = int(duration.total_seconds())
    
    def mark_completed(self, status='success', error_message=None, error_details=None):
        """Mark complete sync as completed"""
        self.sync_completed_at = datetime.now()
        self.sync_status = status
        if error_message:
            self.error_message = error_message
        if error_details:
            self.set_error_details(error_details)
        self.calculate_duration()
    
    def to_dict(self):
        """Convert complete sync to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'sync_type': self.sync_type,
            'sync_status': self.sync_status,
            'sync_started_at': self.sync_started_at.isoformat() if self.sync_started_at else None,
            'sync_completed_at': self.sync_completed_at.isoformat() if self.sync_completed_at else None,
            'sync_duration_seconds': self.sync_duration_seconds,
            'total_providers_synced': self.total_providers_synced,
            'successful_providers': self.successful_providers,
            'failed_providers': self.failed_providers,
            'total_resources_found': self.total_resources_found,
            'total_monthly_cost': self.total_monthly_cost,
            'total_daily_cost': self.total_daily_cost,
            'cost_by_provider': self.get_cost_by_provider(),
            'resources_by_provider': self.get_resources_by_provider(),
            'error_message': self.error_message,
            'error_details': self.get_error_details(),
            'sync_config': self.get_sync_config(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<CompleteSync {self.sync_type}:{self.sync_status}>'


class ProviderSyncReference(BaseModel):
    """Model for tracking individual provider syncs within a complete sync"""
    __tablename__ = 'provider_sync_references'
    
    # Relationships
    complete_sync_id = db.Column(db.Integer, db.ForeignKey('complete_syncs.id'), nullable=False, index=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('cloud_providers.id'), nullable=False, index=True)
    sync_snapshot_id = db.Column(db.Integer, db.ForeignKey('sync_snapshots.id'), nullable=False, index=True)
    
    # Sync execution details
    sync_order = db.Column(db.Integer, nullable=False)  # Order of sync execution
    sync_status = db.Column(db.String(20), nullable=False)  # success, error, skipped
    sync_duration_seconds = db.Column(db.Integer)  # Duration for this provider
    resources_synced = db.Column(db.Integer, default=0)
    provider_cost = db.Column(db.Float, default=0.0)
    
    # Error details for this provider
    error_message = db.Column(db.Text)
    error_details = db.Column(db.Text)  # JSON with detailed error info
    
    def get_error_details(self):
        """Get parsed error details"""
        try:
            return json.loads(self.error_details) if self.error_details else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_error_details(self, error_dict):
        """Set error details from dictionary"""
        self.error_details = json.dumps(error_dict)
    
    def to_dict(self):
        """Convert provider sync reference to dictionary"""
        return {
            'id': self.id,
            'complete_sync_id': self.complete_sync_id,
            'provider_id': self.provider_id,
            'sync_snapshot_id': self.sync_snapshot_id,
            'sync_order': self.sync_order,
            'sync_status': self.sync_status,
            'sync_duration_seconds': self.sync_duration_seconds,
            'resources_synced': self.resources_synced,
            'provider_cost': self.provider_cost,
            'error_message': self.error_message,
            'error_details': self.get_error_details(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<ProviderSyncReference {self.provider_id}:{self.sync_status}>'
