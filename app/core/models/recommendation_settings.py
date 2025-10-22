from __future__ import annotations

"""
System-wide recommendation rule settings

Allows enabling/disabling rules globally and per-provider for resource-scoped rules.
"""

from app.core.models import db
from .base import BaseModel


class RecommendationRuleSetting(BaseModel):
    __tablename__ = 'recommendation_rule_settings'

    # Rule identity
    rule_id = db.Column(db.String(100), nullable=False, index=True)
    scope = db.Column(db.String(20), nullable=False, index=True)  # 'global' | 'resource'

    # Optional scoping for resource rules
    provider_type = db.Column(db.String(50), index=True)  # beget, selectel, etc.; NULL => any
    resource_type = db.Column(db.String(50), index=True)  # server, vm, etc.; NULL => any

    # State
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    description = db.Column(db.Text)

    __table_args__ = (
        db.UniqueConstraint('rule_id', 'scope', 'provider_type', 'resource_type', name='uq_reco_rule_scopes'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'scope': self.scope,
            'provider_type': self.provider_type,
            'resource_type': self.resource_type,
            'enabled': bool(self.enabled),
            'description': self.description,
        }


