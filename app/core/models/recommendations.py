"""
Optimization recommendations model
"""
from app.core.models import db
from .base import BaseModel


class OptimizationRecommendation(BaseModel):
    """AI-generated cost optimization recommendations"""
    __tablename__ = 'optimization_recommendations'

    # Relations
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False, index=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('cloud_providers.id'), index=True)

    # Core identification
    recommendation_type = db.Column(db.String(50), nullable=False, index=True)  # resize, shutdown, migrate, etc.
    category = db.Column(db.String(20), default='cost', index=True)  # cost (extensible: security, reliability, ops)
    severity = db.Column(db.String(10), default='medium', index=True)  # info, low, medium, high, critical
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(50))  # rule identifier, e.g., rightsizing_cpu

    # Cached resource fields for fast display/filtering
    resource_type = db.Column(db.String(50), index=True)
    resource_name = db.Column(db.String(200))
    
    # Provider-specific tracking for cross-provider recommendations
    target_provider = db.Column(db.String(50), index=True)  # Which provider is being recommended
    target_sku = db.Column(db.String(200), index=True)      # Specific SKU identifier
    target_region = db.Column(db.String(100))               # Target region for migration

    # Savings and confidence
    potential_savings = db.Column(db.Float, default=0.0)
    estimated_monthly_savings = db.Column(db.Float, default=0.0, index=True)
    estimated_one_time_savings = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='RUB')
    confidence_score = db.Column(db.Float, default=0.0)  # 0-1 confidence in recommendation

    # Detailed insights/inputs (JSON encoded as text)
    metrics_snapshot = db.Column(db.Text)
    insights = db.Column(db.Text)
    
    # AI-generated text (HTML)
    ai_short_description = db.Column(db.Text)  # Short description for collapsed card
    ai_detailed_description = db.Column(db.Text)  # Detailed description for expanded view
    ai_generated_at = db.Column(db.DateTime)  # When AI text was generated

    # Lifecycle state
    status = db.Column(
        db.String(20),
        default='pending',
        index=True
    )  # pending, seen, snoozed, implemented, dismissed
    first_seen_at = db.Column(db.DateTime)
    seen_at = db.Column(db.DateTime)
    snoozed_until = db.Column(db.DateTime)
    applied_at = db.Column(db.DateTime)
    dismissed_at = db.Column(db.DateTime)
    dismissed_reason = db.Column(db.Text)
    
    # Verification tracking for auto-cleanup of obsolete recommendations
    last_verified_at = db.Column(db.DateTime, index=True)  # Last time rule regenerated this recommendation
    verification_fail_count = db.Column(db.Integer, default=0)  # Consecutive scans without regeneration

    # Indexes (implicit via index=True on columns). Ensure created_at is indexed via BaseModel is not; add here via composite idx if needed.

    def __repr__(self):
        return f'<OptimizationRecommendation {self.severity}:{self.recommendation_type}:{self.title}>'
