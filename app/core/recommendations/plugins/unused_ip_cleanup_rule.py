from __future__ import annotations

import logging
from typing import List
from datetime import datetime, timezone

from flask import current_app

from app.core.models.resource import Resource
from app.core.models.provider import CloudProvider
from app.core.recommendations.interfaces import BaseRule, RuleCategory, RuleScope, RecommendationOutput

logger = logging.getLogger(__name__)


class UnusedReservedIPCleanupRule(BaseRule):
    @property
    def id(self) -> str:
        return "cost.cleanup.unused_reserved_ips"

    @property
    def name(self) -> str:
        return "Удалить неиспользуемый зарезервированный IP"

    @property
    def description(self) -> str:
        from flask import current_app
        age_threshold_days = int(current_app.config.get('UNUSED_IP_CLEANUP_AGE_DAYS', 180))
        return (
            f"Рекомендует удалить зарезервированный IP-адрес, который не используется дольше заданного порога "
            f"(по умолчанию {age_threshold_days} дней). Неиспользуемые зарезервированные IP-адреса продолжают "
            f"потреблять средства, хотя не приносят пользы. Удаление таких адресов помогает снизить затраты."
        )

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COST

    @property
    def scope(self) -> RuleScope:
        return RuleScope.RESOURCE

    @property
    def resource_types(self):
        return {"reserved_ip", "static_ip", "elastic_ip"}

    def applies(self, resource: Resource, context) -> bool:
        """Applies only to reserved IP resources."""
        try:
            rtype = getattr(resource, 'resource_type', None) or getattr(resource, 'type', None)
        except Exception:
            return False
        
        return rtype in self.resource_types

    def evaluate(self, resource: Resource, context) -> List[RecommendationOutput]:
        # Get configurable age threshold (default: 180 days = 6 months)
        age_threshold_days = int(current_app.config.get('UNUSED_IP_CLEANUP_AGE_DAYS', 180))
        
        # Extract IP usage status and creation date from provider_config
        try:
            import json
            cfg = json.loads(resource.provider_config or '{}')
            
            # Check if IP is used (attached to a resource)
            address_data = cfg.get('address', {})
            is_used = address_data.get('used', True)
            
            # If IP is in use, skip recommendation
            if is_used:
                logger.debug(
                    "unused_ip_cleanup: skip (IP is in use) | res_id=%s name=%s",
                    getattr(resource, 'id', None),
                    getattr(resource, 'resource_name', 'unknown')
                )
                return []
            
            # Extract creation date
            created_at_str = cfg.get('created_at', address_data.get('createdAt', ''))
            
            if not created_at_str:
                logger.debug(
                    "unused_ip_cleanup: skip (no creation date) | res_id=%s name=%s",
                    getattr(resource, 'id', None),
                    getattr(resource, 'resource_name', 'unknown')
                )
                return []
            
            # Parse creation date
            try:
                # Handle ISO format with or without 'Z'
                created_date = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            except Exception as e:
                logger.warning(
                    "unused_ip_cleanup: skip (invalid date format '%s') | res_id=%s name=%s | error=%s",
                    created_at_str,
                    getattr(resource, 'id', None),
                    getattr(resource, 'resource_name', 'unknown'),
                    e
                )
                return []
            
            # Calculate age
            now = datetime.now(timezone.utc)
            if created_date.tzinfo is None:
                created_date = created_date.replace(tzinfo=timezone.utc)
            
            age_days = (now - created_date).days
            
            if age_days < age_threshold_days:
                logger.debug(
                    "unused_ip_cleanup: skip (age %d < threshold %d) | res_id=%s name=%s",
                    age_days,
                    age_threshold_days,
                    getattr(resource, 'id', None),
                    getattr(resource, 'resource_name', 'unknown')
                )
                return []
            
        except Exception as e:
            logger.error(
                "unused_ip_cleanup: skip (exception extracting data) | res_id=%s name=%s | error=%s",
                getattr(resource, 'id', None),
                getattr(resource, 'resource_name', 'unknown'),
                e
            )
            return []
        
        # Calculate potential savings (current monthly cost)
        current_monthly_cost = 0.0
        try:
            if getattr(resource, 'effective_cost', 0) and getattr(resource, 'billing_period', '') == 'monthly':
                current_monthly_cost = float(resource.effective_cost or 0.0)
            elif getattr(resource, 'daily_cost', 0):
                current_monthly_cost = float(resource.daily_cost or 0.0) * 30.0
            else:
                # fallback to provider_config monthly_cost if available
                try:
                    cfg = json.loads(resource.provider_config or '{}')
                    if cfg.get('monthly_cost'):
                        current_monthly_cost = float(cfg.get('monthly_cost') or 0.0)
                except Exception:
                    pass
        except Exception:
            current_monthly_cost = 0.0

        if current_monthly_cost <= 0:
            logger.info(
                "unused_ip_cleanup: skip (no cost) | res_id=%s name=%s age=%d days",
                getattr(resource, 'id', None),
                getattr(resource, 'resource_name', 'unknown'),
                age_days
            )
            return []

        # Extract IP address for context
        ip_address = resource.external_ip or cfg.get('actual_ip_address', 'N/A')

        title = "Удалить неиспользуемый зарезервированный IP"
        description = (
            f"Зарезервированный IP-адрес '{resource.resource_name}' ({ip_address}) не используется уже {age_days} дней "
            f"({age_days / 365:.1f} лет) и продолжает потреблять средства, "
            f"что стоит {current_monthly_cost:.2f} {resource.currency}/месяц. "
            f"Рассмотрите возможность освобождения этого IP-адреса, чтобы полностью исключить эти расходы."
        )

        return [
            RecommendationOutput(
                recommendation_type="cleanup_unused_ip",
                title=title,
                description=description,
                category=RuleCategory.COST,
                severity="medium",
                source=self.id,
                estimated_monthly_savings=current_monthly_cost,
                currency=resource.currency or 'RUB',
                confidence_score=1.0,
                metrics_snapshot={
                    "age_days": age_days,
                    "age_years": round(age_days / 365, 1),
                    "age_threshold_days": age_threshold_days,
                    "ip_address": ip_address,
                    "created_at": created_at_str,
                    "is_used": False,
                    "current_monthly_cost": current_monthly_cost
                },
                insights={
                    "action": "release_ip",
                    "age_days": age_days,
                    "ip_address": ip_address
                },
            )
        ]


RULES = [UnusedReservedIPCleanupRule]



