"""
Cost allocation and trend models
"""
from app.core.models import db
from .base import BaseModel

class CostAllocation(BaseModel):
    """Cost allocation to business units and projects"""
    __tablename__ = 'cost_allocations'
    
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False, index=True)
    business_unit = db.Column(db.String(100), nullable=False, index=True)
    project_id = db.Column(db.String(100), index=True)
    cost_center = db.Column(db.String(100))
    allocation_percentage = db.Column(db.Float, default=100.0)
    allocated_cost = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='RUB')
    
    def __repr__(self):
        return f'<CostAllocation {self.business_unit}:{self.allocated_cost}>'

class CostTrend(BaseModel):
    """Historical cost data for trend analysis"""
    __tablename__ = 'cost_trends'
    
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False, index=True)
    period_start = db.Column(db.DateTime, nullable=False, index=True)
    period_end = db.Column(db.DateTime, nullable=False)
    total_cost = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='RUB')
    cost_breakdown = db.Column(db.Text)  # JSON breakdown by service/component
    
    def __repr__(self):
        return f'<CostTrend {self.period_start}:{self.total_cost}>'
