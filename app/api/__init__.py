"""
API blueprints
"""
from .recommendations import recommendations_bp
from .reports import reports_bp

__all__ = [
    'recommendations_bp',
    'reports_bp',
]
