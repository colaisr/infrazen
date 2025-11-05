"""
Tools for agent to access InfraZen data
Each tool is a callable with schema, auth scope, and optional prompt
"""

from .data_access import get_recommendation_data
from .recommendation_tools import RecommendationTools

__all__ = ['get_recommendation_data', 'RecommendationTools']
