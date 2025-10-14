"""
Pricing models for multi-provider price comparison and optimization
"""
import json
from datetime import datetime
from app.core.database import db
from .base import BaseModel


class ProviderPrice(BaseModel):
    """Store provider-specific pricing data for cross-provider comparison"""
    
    __tablename__ = 'provider_prices'
    
    # Provider identification
    provider = db.Column(db.String(50), nullable=False, index=True)  # 'beget', 'selectel', 'aws', etc.
    resource_type = db.Column(db.String(100), nullable=False, index=True)  # Universal taxonomy type
    provider_sku = db.Column(db.String(200))  # Provider-specific SKU/plan name
    region = db.Column(db.String(50), index=True)  # Normalized region code
    
    # Core specifications
    cpu_cores = db.Column(db.Integer)
    ram_gb = db.Column(db.Integer)
    storage_gb = db.Column(db.Integer)
    storage_type = db.Column(db.String(20))  # 'SSD', 'HDD', 'NVMe'
    
    # Extended specifications (JSON for flexibility)
    extended_specs = db.Column(db.JSON)
    
    # Pricing
    hourly_cost = db.Column(db.Numeric(10, 4))
    monthly_cost = db.Column(db.Numeric(10, 2))
    currency = db.Column(db.String(3), default='RUB')
    
    # Commitment pricing (future)
    yearly_cost = db.Column(db.Numeric(10, 2))
    three_year_cost = db.Column(db.Numeric(10, 2))
    commitment_discount_percent = db.Column(db.Numeric(5, 2))
    
    # Metadata
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    confidence_score = db.Column(db.Numeric(3, 2))  # 0.0 to 1.0 data quality
    source = db.Column(db.String(50))  # 'billing_api', 'official_price_list', 'scraped', 'manual'
    source_url = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    # Relationships
    price_history = db.relationship('PriceHistory', backref='price', lazy=True, cascade='all, delete-orphan')
    recommendations = db.relationship('PriceComparisonRecommendation', backref='recommended_price', lazy=True)
    
    # Indexes for efficient querying
    __table_args__ = (
        db.Index('idx_provider_prices_lookup', 'provider', 'resource_type', 'cpu_cores', 'ram_gb'),
        db.Index('idx_provider_prices_region', 'region', 'resource_type'),
        db.Index('idx_provider_prices_updated', 'last_updated'),
    )
    
    def __repr__(self):
        return f'<ProviderPrice {self.provider}:{self.resource_type}:{self.provider_sku}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'provider': self.provider,
            'resource_type': self.resource_type,
            'provider_sku': self.provider_sku,
            'region': self.region,
            'cpu_cores': self.cpu_cores,
            'ram_gb': self.ram_gb,
            'storage_gb': self.storage_gb,
            'storage_type': self.storage_type,
            'extended_specs': self.extended_specs,
            'hourly_cost': float(self.hourly_cost) if self.hourly_cost else None,
            'monthly_cost': float(self.monthly_cost) if self.monthly_cost else None,
            'currency': self.currency,
            'yearly_cost': float(self.yearly_cost) if self.yearly_cost else None,
            'three_year_cost': float(self.three_year_cost) if self.three_year_cost else None,
            'commitment_discount_percent': float(self.commitment_discount_percent) if self.commitment_discount_percent else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'confidence_score': float(self.confidence_score) if self.confidence_score else None,
            'source': self.source,
            'source_url': self.source_url,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def calculate_similarity_score(self, target_specs):
        """Calculate similarity score (0-100) with another resource specification"""
        score = 0
        
        # CPU similarity: 0-30 points
        if self.cpu_cores and target_specs.get('cpu_cores'):
            cpu_diff = abs(self.cpu_cores - target_specs['cpu_cores'])
            if cpu_diff == 0:
                score += 30
            elif cpu_diff == 1:
                score += 25
            elif cpu_diff == 2:
                score += 15
            elif cpu_diff <= 3:
                score += 10
        
        # RAM similarity: 0-30 points
        if self.ram_gb and target_specs.get('ram_gb'):
            ram_ratio = min(self.ram_gb, target_specs['ram_gb']) / max(self.ram_gb, target_specs['ram_gb'])
            if ram_ratio >= 1.0:
                score += 30  # Exact match
            elif ram_ratio >= 0.75:
                score += 20  # Within 25%
            elif ram_ratio >= 0.5:
                score += 10  # Within 50%
        
        # Storage similarity: 0-20 points
        if self.storage_gb and target_specs.get('storage_gb'):
            storage_ratio = min(self.storage_gb, target_specs['storage_gb']) / max(self.storage_gb, target_specs['storage_gb'])
            if storage_ratio >= 1.0:
                score += 20  # Exact match
            elif storage_ratio >= 0.6:
                score += 15  # Within 40%
        
        # Region match: 0-20 points
        if self.region and target_specs.get('region'):
            if self.region == target_specs['region']:
                score += 20  # Exact region
            elif self.region[:2] == target_specs['region'][:2]:  # Same country
                score += 10
        
        return min(score, 100)  # Cap at 100


class PriceHistory(BaseModel):
    """Track price changes over time for trend analysis"""
    
    __tablename__ = 'price_history'
    
    # Reference to the price record
    price_id = db.Column(db.Integer, db.ForeignKey('provider_prices.id'), nullable=False, index=True)
    
    # Price change details
    old_monthly_cost = db.Column(db.Numeric(10, 2))
    new_monthly_cost = db.Column(db.Numeric(10, 2))
    change_percent = db.Column(db.Numeric(6, 2))
    change_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    change_reason = db.Column(db.String(200))  # 'market_adjustment', 'promotion', 'hardware_upgrade'
    
    def __repr__(self):
        return f'<PriceHistory {self.price_id}: {self.change_percent}%>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'price_id': self.price_id,
            'old_monthly_cost': float(self.old_monthly_cost) if self.old_monthly_cost else None,
            'new_monthly_cost': float(self.new_monthly_cost) if self.new_monthly_cost else None,
            'change_percent': float(self.change_percent) if self.change_percent else None,
            'change_date': self.change_date.isoformat() if self.change_date else None,
            'change_reason': self.change_reason,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class PriceComparisonRecommendation(BaseModel):
    """Store price comparison optimization recommendations for users"""
    
    __tablename__ = 'price_comparison_recommendations'
    
    # User and resource references
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    current_resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False, index=True)
    recommended_price_id = db.Column(db.Integer, db.ForeignKey('provider_prices.id'), nullable=False, index=True)
    
    # Recommendation details
    similarity_score = db.Column(db.Numeric(5, 2))  # 0-100 match quality
    monthly_savings = db.Column(db.Numeric(10, 2))
    annual_savings = db.Column(db.Numeric(10, 2))
    savings_percent = db.Column(db.Numeric(6, 2))
    
    # Migration information
    migration_effort = db.Column(db.String(20))  # 'easy', 'medium', 'hard'
    migration_notes = db.Column(db.Text)
    
    # User interaction
    status = db.Column(db.String(20), default='pending', index=True)  # 'pending', 'accepted', 'rejected', 'completed'
    user_feedback = db.Column(db.Text)
    
    def __repr__(self):
        return f'<PriceComparisonRecommendation {self.current_resource_id}->{self.recommended_price_id}: {self.savings_percent}%>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'current_resource_id': self.current_resource_id,
            'recommended_price_id': self.recommended_price_id,
            'similarity_score': float(self.similarity_score) if self.similarity_score else None,
            'monthly_savings': float(self.monthly_savings) if self.monthly_savings else None,
            'annual_savings': float(self.annual_savings) if self.annual_savings else None,
            'savings_percent': float(self.savings_percent) if self.savings_percent else None,
            'migration_effort': self.migration_effort,
            'migration_notes': self.migration_notes,
            'status': self.status,
            'user_feedback': self.user_feedback,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
