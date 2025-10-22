from __future__ import annotations

import importlib
import pkgutil
from typing import List, Optional, Sequence, Type

from .interfaces import BaseRule, RuleScope


class RuleRegistry:
    """Discovery and registry of recommendation rules.

    By default discovers rules in app.core.recommendations.plugins.*
    """

    def __init__(self) -> None:
        self._rules: List[BaseRule] = []

    def register(self, rule_cls: Type[BaseRule]) -> None:
        if not issubclass(rule_cls, BaseRule):
            return
        try:
            instance = rule_cls()
            self._rules.append(instance)
        except Exception:
            # Skip faulty rules to avoid blocking the entire pipeline
            pass

    def discover(self, package: str = "app.core.recommendations.plugins") -> None:
        try:
            pkg = importlib.import_module(package)
        except Exception:
            return

        for finder, name, ispkg in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
            try:
                module = importlib.import_module(name)
            except Exception:
                continue

            # Register any BaseRule subclasses exported as `RULES` list or top-level classes
            rules = getattr(module, "RULES", None)
            if isinstance(rules, list):
                for rule_cls in rules:
                    self.register(rule_cls)
                continue

            for attr_name in dir(module):
                obj = getattr(module, attr_name)
                if isinstance(obj, type) and issubclass(obj, BaseRule) and obj is not BaseRule:
                    self.register(obj)

    # ---- Query ----
    def all_rules(self) -> List[BaseRule]:
        return list(self._rules)

    def resource_rules(self) -> List[BaseRule]:
        return [r for r in self._rules if r.scope == RuleScope.RESOURCE]

    def global_rules(self) -> List[BaseRule]:
        return [r for r in self._rules if r.scope == RuleScope.GLOBAL]

    def rules_for_resource(self, resource_type: Optional[str], provider_type: Optional[str]) -> List[BaseRule]:
        results: List[BaseRule] = []
        for rule in self.resource_rules():
            if rule.resource_types and resource_type not in rule.resource_types:
                continue
            if rule.providers is not None and provider_type not in rule.providers:
                continue
            results.append(rule)
        return results







