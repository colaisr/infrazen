"""
Base provider system for extensible cloud provider support
"""
from .provider_base import BaseProvider
from .resource_mapper import ResourceMapper

__all__ = ['BaseProvider', 'ResourceMapper']
