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
from .recommendation_settings import RecommendationRuleSetting
from .sync import SyncSnapshot, ResourceState
from .complete_sync import CompleteSync, ProviderSyncReference
from .unrecognized_resource import UnrecognizedResource
from .provider_catalog import ProviderCatalog
from .pricing import ProviderPrice, PriceHistory, PriceComparisonRecommendation
from .provider_admin_credentials import ProviderAdminCredentials
from .provider_resource_type import ProviderResourceType
from .business_board import BusinessBoard
from .board_resource import BoardResource
from .board_group import BoardGroup

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
    'OptimizationRecommendation',
    'RecommendationRuleSetting',
    'SyncSnapshot',
    'ResourceState',
    'CompleteSync',
    'ProviderSyncReference',
    'UnrecognizedResource',
    'ProviderCatalog',
    'ProviderPrice',
    'PriceHistory',
    'PriceComparisonRecommendation',
    'ProviderAdminCredentials',
    'ProviderResourceType',
    'BusinessBoard',
    'BoardResource',
    'BoardGroup'
]