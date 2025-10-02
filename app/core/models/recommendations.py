"""
Optimization recommendations model
"""
from app.core.models import db
from .base import BaseModel

class OptimizationRecommendation(BaseModel):
    """AI-generated cost optimization recommendations"""
    __tablename__ = 'optimization_recommendations'
    
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False, index=True)
    recommendation_type = db.Column(db.String(50), nullable=False, index=True)  # resize, shutdown, migrate, etc.
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    potential_savings = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='RUB')
    confidence_score = db.Column(db.Float, default=0.0)  # 0-1 confidence in recommendation
    status = db.Column(db.String(20), default='pending', index=True)  # pending, applied, dismissed
    applied_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<OptimizationRecommendation {self.recommendation_type}:{self.title}>'
