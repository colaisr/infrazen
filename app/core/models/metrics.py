"""
Resource metrics and usage models
"""
from app.core.models import db
from .base import BaseModel

class ResourceMetric(BaseModel):
    """Resource performance and usage metrics"""
    __tablename__ = 'resource_metrics'
    
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False, index=True)
    metric_name = db.Column(db.String(100), nullable=False, index=True)
    metric_value = db.Column(db.Float, nullable=False)
    metric_unit = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    
    def __repr__(self):
        return f'<ResourceMetric {self.metric_name}:{self.metric_value}>'

class ResourceUsageSummary(BaseModel):
    """Aggregated resource usage summaries"""
    __tablename__ = 'resource_usage_summary'
    
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False, index=True)
    period_start = db.Column(db.DateTime, nullable=False, index=True)
    period_end = db.Column(db.DateTime, nullable=False)
    total_usage = db.Column(db.Float, default=0.0)
    peak_usage = db.Column(db.Float, default=0.0)
    average_usage = db.Column(db.Float, default=0.0)
    cost = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='RUB')
    
    def __repr__(self):
        return f'<ResourceUsageSummary {self.resource_id}:{self.period_start}>'
