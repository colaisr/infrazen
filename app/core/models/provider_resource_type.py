from __future__ import annotations

"""Provider resource type inventory

Tracks known unified resource types per provider and raw aliases used by the provider.
"""

from app.core.models import db
from .base import BaseModel


class ProviderResourceType(BaseModel):
    __tablename__ = 'provider_resource_types'

    provider_type = db.Column(db.String(50), nullable=False, index=True)
    unified_type = db.Column(db.String(50), nullable=False, index=True)
    display_name = db.Column(db.String(100))
    icon = db.Column(db.String(100))
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    raw_aliases = db.Column(db.Text)  # JSON array of raw type names

    __table_args__ = (
        db.UniqueConstraint('provider_type', 'unified_type', name='uq_provider_unified_type'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'provider_type': self.provider_type,
            'unified_type': self.unified_type,
            'display_name': self.display_name,
            'icon': self.icon,
            'enabled': bool(self.enabled),
            'raw_aliases': self.raw_aliases,
        }


