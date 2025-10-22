from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Set


class RuleScope(str, Enum):
    RESOURCE = "resource"
    GLOBAL = "global"


class RuleCategory(str, Enum):
    COST = "cost"
    SECURITY = "security"
    RELIABILITY = "reliability"
    OPERATIONS = "operations"
    COMPLIANCE = "compliance"


@dataclass
class RecommendationOutput:
    recommendation_type: str
    title: str
    description: str

    # Classification
    category: RuleCategory = RuleCategory.COST
    severity: str = "medium"  # info, low, medium, high, critical
    source: Optional[str] = None  # rule identifier

    # Savings and confidence
    potential_savings: float = 0.0
    estimated_monthly_savings: float = 0.0
    estimated_one_time_savings: float = 0.0
    currency: str = "RUB"
    confidence_score: float = 0.0

    # Additional context for display/debugging
    metrics_snapshot: Dict[str, Any] = field(default_factory=dict)
    insights: Dict[str, Any] = field(default_factory=dict)

    # Targeting
    resource_id: Optional[int] = None
    provider_id: Optional[int] = None
    resource_type: Optional[str] = None
    resource_name: Optional[str] = None


class BaseRule:
    """Base class for recommendation rules.

    Subclasses should define metadata via properties and implement one of the
    evaluation methods depending on scope.
    """

    # ---- Metadata (override in subclasses) ----
    @property
    def id(self) -> str:
        raise NotImplementedError

    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COST

    @property
    def scope(self) -> RuleScope:
        return RuleScope.RESOURCE

    @property
    def resource_types(self) -> Set[str]:
        return set()

    @property
    def providers(self) -> Optional[Set[str]]:
        return None  # None => any provider

    # ---- Resource-scoped API ----
    def applies(self, resource: Any, context: Any) -> bool:
        """Return True if this rule should run for the given resource.

        Default: match by resource type and (optional) providers.
        """
        try:
            resource_type = getattr(resource, "resource_type", None) or getattr(resource, "type", None)
            provider_type = getattr(resource, "provider_type", None)
        except Exception:
            resource_type = None
            provider_type = None

        if self.resource_types and resource_type not in self.resource_types:
            return False
        if self.providers is not None and provider_type not in self.providers:
            return False
        return True

    def evaluate(self, resource: Any, context: Any) -> List[RecommendationOutput]:
        """Produce recommendations for a resource.

        Default: no recommendations.
        """
        return []

    # ---- Global API ----
    def evaluate_global(self, inventory: Sequence[Any], context: Any) -> List[RecommendationOutput]:
        """Produce recommendations using full inventory view.

        Default: no recommendations.
        """
        return []







