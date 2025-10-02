"""
Sync and snapshot models for tracking resource synchronization
"""
import json
from datetime import datetime
from app.core.models import db
from .base import BaseModel

class SyncSnapshot(BaseModel):
    """Model for tracking sync operations and their snapshots"""
    __tablename__ = 'sync_snapshots'
    
    # Provider relationship
    provider_id = db.Column(db.Integer, db.ForeignKey('cloud_providers.id'), nullable=False, index=True)
    
    # Sync metadata
    sync_type = db.Column(db.String(20), nullable=False, default='full')  # full, incremental, manual
    sync_status = db.Column(db.String(20), nullable=False, default='running')  # running, success, error, cancelled
    sync_started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    sync_completed_at = db.Column(db.DateTime)
    sync_duration_seconds = db.Column(db.Integer)  # Duration in seconds
    
    # Sync statistics
    total_resources_found = db.Column(db.Integer, default=0)
    resources_created = db.Column(db.Integer, default=0)
    resources_updated = db.Column(db.Integer, default=0)
    resources_deleted = db.Column(db.Integer, default=0)
    resources_unchanged = db.Column(db.Integer, default=0)
    
    # Cost and usage statistics
    total_monthly_cost = db.Column(db.Float, default=0.0)
    total_resources_by_type = db.Column(db.Text)  # JSON: {"VPS": 5, "Domain": 10}
    total_resources_by_status = db.Column(db.Text)  # JSON: {"active": 12, "stopped": 3}
    
    # Error handling
    error_message = db.Column(db.Text)
    error_details = db.Column(db.Text)  # JSON with detailed error info
    
    # Sync configuration used
    sync_config = db.Column(db.Text)  # JSON with sync parameters
    
    # Relationships
    resource_states = db.relationship('ResourceState', backref='sync_snapshot', lazy=True, cascade='all, delete-orphan')
    
    def get_total_resources_by_type(self):
        """Get parsed total resources by type"""
        try:
            return json.loads(self.total_resources_by_type) if self.total_resources_by_type else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_total_resources_by_type(self, data_dict):
        """Set total resources by type from dictionary"""
        self.total_resources_by_type = json.dumps(data_dict)
    
    def get_total_resources_by_status(self):
        """Get parsed total resources by status"""
        try:
            return json.loads(self.total_resources_by_status) if self.total_resources_by_status else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_total_resources_by_status(self, data_dict):
        """Set total resources by status from dictionary"""
        self.total_resources_by_status = json.dumps(data_dict)
    
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
        """Mark sync as completed"""
        self.sync_completed_at = datetime.utcnow()
        self.sync_status = status
        if error_message:
            self.error_message = error_message
        if error_details:
            self.set_error_details(error_details)
        self.calculate_duration()
    
    def to_dict(self):
        """Convert sync snapshot to dictionary"""
        return {
            'id': self.id,
            'provider_id': self.provider_id,
            'sync_type': self.sync_type,
            'sync_status': self.sync_status,
            'sync_started_at': self.sync_started_at.isoformat() if self.sync_started_at else None,
            'sync_completed_at': self.sync_completed_at.isoformat() if self.sync_completed_at else None,
            'sync_duration_seconds': self.sync_duration_seconds,
            'total_resources_found': self.total_resources_found,
            'resources_created': self.resources_created,
            'resources_updated': self.resources_updated,
            'resources_deleted': self.resources_deleted,
            'resources_unchanged': self.resources_unchanged,
            'total_monthly_cost': self.total_monthly_cost,
            'total_resources_by_type': self.get_total_resources_by_type(),
            'total_resources_by_status': self.get_total_resources_by_status(),
            'error_message': self.error_message,
            'error_details': self.get_error_details(),
            'sync_config': self.get_sync_config(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<SyncSnapshot {self.sync_type}:{self.sync_status}>'


class ResourceState(BaseModel):
    """Model for tracking individual resource states during sync"""
    __tablename__ = 'resource_states'
    
    # Relationships
    sync_snapshot_id = db.Column(db.Integer, db.ForeignKey('sync_snapshots.id'), nullable=False, index=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=True, index=True)  # Nullable for deleted resources
    
    # Resource identification (for deleted resources)
    provider_resource_id = db.Column(db.String(100), nullable=False)  # Provider's resource ID
    resource_type = db.Column(db.String(100), nullable=False)
    resource_name = db.Column(db.String(255), nullable=False)
    
    # State tracking
    state_action = db.Column(db.String(20), nullable=False)  # created, updated, unchanged, deleted
    previous_state = db.Column(db.Text)  # JSON of previous resource state
    current_state = db.Column(db.Text)  # JSON of current resource state
    changes_detected = db.Column(db.Text)  # JSON of detected changes
    
    # Resource metadata
    service_name = db.Column(db.String(100))
    region = db.Column(db.String(100))
    status = db.Column(db.String(50))
    effective_cost = db.Column(db.Float, default=0.0)
    
    # Change tracking
    has_cost_change = db.Column(db.Boolean, default=False)
    has_status_change = db.Column(db.Boolean, default=False)
    has_config_change = db.Column(db.Boolean, default=False)
    
    def get_previous_state(self):
        """Get parsed previous state"""
        try:
            return json.loads(self.previous_state) if self.previous_state else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_previous_state(self, state_dict):
        """Set previous state from dictionary"""
        self.previous_state = json.dumps(state_dict)
    
    def get_current_state(self):
        """Get parsed current state"""
        try:
            return json.loads(self.current_state) if self.current_state else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_current_state(self, state_dict):
        """Set current state from dictionary"""
        self.current_state = json.dumps(state_dict)
    
    def get_changes_detected(self):
        """Get parsed changes detected"""
        try:
            return json.loads(self.changes_detected) if self.changes_detected else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_changes_detected(self, changes_dict):
        """Set changes detected from dictionary"""
        self.changes_detected = json.dumps(changes_dict)
    
    def detect_changes(self):
        """Detect changes between previous and current state"""
        previous = self.get_previous_state()
        current = self.get_current_state()
        
        changes = {}
        
        # Compare key fields
        key_fields = ['resource_name', 'status', 'effective_cost', 'region', 'service_name']
        for field in key_fields:
            if previous.get(field) != current.get(field):
                changes[field] = {
                    'previous': previous.get(field),
                    'current': current.get(field)
                }
        
        # Check for cost changes
        self.has_cost_change = previous.get('effective_cost', 0) != current.get('effective_cost', 0)
        
        # Check for status changes
        self.has_status_change = previous.get('status') != current.get('status')
        
        # Check for config changes (provider-specific config)
        prev_config = previous.get('provider_config', {})
        curr_config = current.get('provider_config', {})
        self.has_config_change = prev_config != curr_config
        
        if self.has_config_change:
            changes['provider_config'] = {
                'previous': prev_config,
                'current': curr_config
            }
        
        self.set_changes_detected(changes)
        return changes
    
    def to_dict(self):
        """Convert resource state to dictionary"""
        return {
            'id': self.id,
            'sync_snapshot_id': self.sync_snapshot_id,
            'resource_id': self.resource_id,
            'provider_resource_id': self.provider_resource_id,
            'resource_type': self.resource_type,
            'resource_name': self.resource_name,
            'state_action': self.state_action,
            'previous_state': self.get_previous_state(),
            'current_state': self.get_current_state(),
            'changes_detected': self.get_changes_detected(),
            'service_name': self.service_name,
            'region': self.region,
            'status': self.status,
            'effective_cost': self.effective_cost,
            'has_cost_change': self.has_cost_change,
            'has_status_change': self.has_status_change,
            'has_config_change': self.has_config_change,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<ResourceState {self.resource_type}:{self.state_action}>'
