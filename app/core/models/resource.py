"""
Resource model for universal resource tracking
"""
import json
from app.core.models import db
from .base import BaseModel

class Resource(BaseModel):
    """Universal resource registry with core properties"""
    __tablename__ = 'resources'
    
    # Provider relationship
    provider_id = db.Column(db.Integer, db.ForeignKey('cloud_providers.id'), nullable=False, index=True)
    
    # Resource identification
    resource_id = db.Column(db.String(100), nullable=False)  # Provider's resource ID
    resource_name = db.Column(db.String(255), nullable=False)
    region = db.Column(db.String(100), nullable=False)
    
    # Classification
    service_name = db.Column(db.String(100), nullable=False)  # e.g., 'Compute', 'Storage', 'Database'
    resource_type = db.Column(db.String(100), nullable=False)  # e.g., 'VM', 'Bucket', 'MySQL'
    status = db.Column(db.String(50), default='active', index=True)  # active, stopped, deleted
    
    # Financial information
    pricing_model = db.Column(db.String(50))  # on-demand, reserved, spot
    list_price = db.Column(db.Float, default=0.0)
    effective_cost = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='RUB')
    billing_period = db.Column(db.String(20))  # monthly, hourly
    
    # Daily cost baseline for FinOps
    daily_cost = db.Column(db.Float, default=0.0)  # Normalized daily cost
    original_cost = db.Column(db.Float, default=0.0)  # Original provider cost
    cost_period = db.Column(db.String(20))  # daily, monthly, yearly, hourly
    cost_frequency = db.Column(db.String(20))  # recurring, usage-based, one-time
    
    # Business context
    business_unit = db.Column(db.String(100))
    project_id = db.Column(db.String(100))
    feature_tag = db.Column(db.String(100))
    cost_center = db.Column(db.String(100))
    environment = db.Column(db.String(50))  # production, development, staging
    
    # Metadata
    last_sync = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True, index=True)
    provider_config = db.Column(db.Text)  # Provider-specific configuration as JSON
    
    # Relationships
    tags = db.relationship('ResourceTag', backref='resource', lazy=True, cascade='all, delete-orphan')
    metrics = db.relationship('ResourceMetric', backref='resource', lazy=True, cascade='all, delete-orphan')
    usage_summary = db.relationship('ResourceUsageSummary', backref='resource', lazy=True, cascade='all, delete-orphan')
    logs = db.relationship('ResourceLog', backref='resource', lazy=True, cascade='all, delete-orphan')
    components = db.relationship('ResourceComponent', backref='resource', lazy=True, cascade='all, delete-orphan')
    cost_allocations = db.relationship('CostAllocation', backref='resource', lazy=True, cascade='all, delete-orphan')
    cost_trends = db.relationship('CostTrend', backref='resource', lazy=True, cascade='all, delete-orphan')
    recommendations = db.relationship('OptimizationRecommendation', backref='resource', lazy=True, cascade='all, delete-orphan')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('provider_id', 'resource_id', 'resource_type', name='unique_provider_resource'),
    )
    
    def get_provider_config(self):
        """Get parsed provider configuration"""
        try:
            return json.loads(self.provider_config) if self.provider_config else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_provider_config(self, config_dict):
        """Set provider configuration from dictionary"""
        self.provider_config = json.dumps(config_dict)
    
    @staticmethod
    def normalize_to_daily_cost(original_cost, period, frequency='recurring'):
        """
        Normalize cost to daily baseline for FinOps analysis
        
        Args:
            original_cost: Original cost from provider
            period: Cost period (daily, monthly, yearly, hourly)
            frequency: Cost frequency (recurring, usage-based, one-time)
        
        Returns:
            float: Normalized daily cost
        """
        if not original_cost or original_cost <= 0:
            return 0.0
        
        # For one-time costs, spread over 30 days for comparison
        if frequency == 'one-time':
            return original_cost / 30
        
        # For usage-based costs, assume daily usage
        if frequency == 'usage-based':
            return original_cost
        
        # Normalize based on period
        if period == 'daily':
            return original_cost
        elif period == 'monthly':
            return original_cost / 30
        elif period == 'yearly':
            return original_cost / 365
        elif period == 'hourly':
            return original_cost * 24
        else:
            # Default to monthly if period unknown
            return original_cost / 30
    
    def set_daily_cost_baseline(self, original_cost, period, frequency='recurring'):
        """
        Set daily cost baseline for FinOps analysis
        
        Args:
            original_cost: Original cost from provider
            period: Cost period (daily, monthly, yearly, hourly)
            frequency: Cost frequency (recurring, usage-based, one-time)
        """
        self.original_cost = original_cost
        self.cost_period = period
        self.cost_frequency = frequency
        self.daily_cost = self.normalize_to_daily_cost(original_cost, period, frequency)
    
    def to_dict(self):
        """Convert resource to dictionary"""
        return {
            'id': self.id,
            'provider_id': self.provider_id,
            'resource_id': self.resource_id,
            'resource_name': self.resource_name,
            'region': self.region,
            'service_name': self.service_name,
            'resource_type': self.resource_type,
            'status': self.status,
            'pricing_model': self.pricing_model,
            'list_price': self.list_price,
            'effective_cost': self.effective_cost,
            'currency': self.currency,
            'billing_period': self.billing_period,
            'business_unit': self.business_unit,
            'project_id': self.project_id,
            'feature_tag': self.feature_tag,
            'cost_center': self.cost_center,
            'environment': self.environment,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'is_active': self.is_active,
            'provider_config': self.get_provider_config(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Resource {self.resource_type}:{self.resource_name}>'
