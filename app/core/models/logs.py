"""
Resource logs and component models
"""
import json
from app.core.models import db
from .base import BaseModel

class ResourceLog(BaseModel):
    """Resource operational logs"""
    __tablename__ = 'resource_logs'
    
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False, index=True)
    log_level = db.Column(db.String(20), nullable=False, index=True)  # INFO, WARN, ERROR
    log_message = db.Column(db.Text, nullable=False)
    log_source = db.Column(db.String(100))  # Where the log came from
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    log_metadata = db.Column(db.Text)  # Additional log data as JSON
    
    def get_metadata(self):
        """Get parsed log metadata"""
        try:
            return json.loads(self.log_metadata) if self.log_metadata else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def __repr__(self):
        return f'<ResourceLog {self.log_level}:{self.log_message[:50]}>'

class ResourceComponent(BaseModel):
    """Internal resource components discovered through log analysis"""
    __tablename__ = 'resource_components'
    
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False, index=True)
    component_name = db.Column(db.String(100), nullable=False)
    component_type = db.Column(db.String(50), nullable=False)  # service, database, cache, etc.
    component_status = db.Column(db.String(20), default='active')
    discovered_at = db.Column(db.DateTime, nullable=False)
    
    def __repr__(self):
        return f'<ResourceComponent {self.component_name}:{self.component_type}>'
