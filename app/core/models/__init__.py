"""
Core database models for InfraZen
"""
# Import the shared database instance
from app.core.database import db

# Import all models to ensure they are registered
from .base import BaseModel
from .user import User
from .provider import CloudProvider
from .resource import Resource
from .metrics import ResourceMetric, ResourceUsageSummary
from .tags import ResourceTag
from .logs import ResourceLog, ResourceComponent
from .costs import CostAllocation, CostTrend
from .recommendations import OptimizationRecommendation

__all__ = [
    'db',
    'BaseModel',
    'User',
    'CloudProvider', 
    'Resource',
    'ResourceMetric',
    'ResourceUsageSummary',
    'ResourceTag',
    'ResourceLog',
    'ResourceComponent',
    'CostAllocation',
    'CostTrend',
    'OptimizationRecommendation'
]