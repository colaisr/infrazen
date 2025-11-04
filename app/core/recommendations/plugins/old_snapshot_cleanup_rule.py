from __future__ import annotations

import logging
from typing import List
from datetime import datetime, timezone

from flask import current_app

from app.core.models.resource import Resource
from app.core.models.provider import CloudProvider
from app.core.recommendations.interfaces import BaseRule, RuleCategory, RuleScope, RecommendationOutput

logger = logging.getLogger(__name__)


class OldSnapshotCleanupRule(BaseRule):
    @property
    def id(self) -> str:
        return "cost.cleanup.old_snapshots"

    @property
    def name(self) -> str:
        return "Удалить устаревший снимок диска"

    @property
    def description(self) -> str:
        from flask import current_app
        age_threshold_days = int(current_app.config.get('SNAPSHOT_CLEANUP_AGE_DAYS', 180))
        return (
            f"Рекомендует удалить снимок диска, который существует дольше заданного порога "
            f"(по умолчанию {age_threshold_days} дней). Старые снимки часто накапливаются и забываются, "
            f"продолжая потреблять ресурсы хранения. Удаление таких снимков помогает "
            f"снизить затраты и улучшить управление резервными копиями."
        )

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COST

    @property
    def scope(self) -> RuleScope:
        return RuleScope.RESOURCE

    @property
    def resource_types(self):
        return {"snapshot", "disk-snapshot", "volume-snapshot"}

    def applies(self, resource: Resource, context) -> bool:
        """Applies only to snapshot resources."""
        try:
            rtype = getattr(resource, 'resource_type', None) or getattr(resource, 'type', None)
        except Exception:
            return False
        
        return rtype in self.resource_types

    def evaluate(self, resource: Resource, context) -> List[RecommendationOutput]:
        # Get configurable age threshold (default: 365 days = 1 year)
        age_threshold_days = int(current_app.config.get('SNAPSHOT_CLEANUP_AGE_DAYS', 365))
        
        # Extract creation date from provider_config
        try:
            import json
            cfg = json.loads(resource.provider_config or '{}')
            created_at_str = cfg.get('created_at', '')
            
            if not created_at_str:
                logger.debug(
                    "old_snapshot_cleanup: skip (no creation date) | res_id=%s name=%s",
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
                    "old_snapshot_cleanup: skip (invalid date format '%s') | res_id=%s name=%s | error=%s",
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
                    "old_snapshot_cleanup: skip (age %d < threshold %d) | res_id=%s name=%s",
                    age_days,
                    age_threshold_days,
                    getattr(resource, 'id', None),
                    getattr(resource, 'resource_name', 'unknown')
                )
                return []
            
        except Exception as e:
            logger.error(
                "old_snapshot_cleanup: skip (exception extracting age) | res_id=%s name=%s | error=%s",
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
                "old_snapshot_cleanup: skip (no cost) | res_id=%s name=%s age=%d days",
                getattr(resource, 'id', None),
                getattr(resource, 'resource_name', 'unknown'),
                age_days
            )
            return []

        # Extract snapshot size for additional context
        size_gb = 0
        try:
            cfg = json.loads(resource.provider_config or '{}')
            size_gb = float(cfg.get('size_gb', 0))
        except Exception:
            pass

        title = "Удалить устаревший снимок диска"
        description = (
            f"Снимок диска '{resource.resource_name}' существует уже {age_days} дней "
            f"({age_days / 365:.1f} лет) и продолжает потреблять ресурсы хранения, "
            f"что стоит {current_monthly_cost:.2f} {resource.currency}/месяц. "
        )
        
        if size_gb > 0:
            description += f"Размер снимка: {size_gb:.1f} GB. "
        
        description += (
            f"Рассмотрите возможность удаления этого снимка, если он больше не нужен для восстановления, "
            f"чтобы полностью исключить эти расходы."
        )

        return [
            RecommendationOutput(
                recommendation_type="cleanup_old_snapshot",
                title=title,
                description=description,
                category=RuleCategory.COST,
                severity="medium",
                source=self.id,
                estimated_monthly_savings=current_monthly_cost,
                currency=resource.currency or 'RUB',
                confidence_score=0.9,
                metrics_snapshot={
                    "age_days": age_days,
                    "age_years": round(age_days / 365, 1),
                    "age_threshold_days": age_threshold_days,
                    "size_gb": size_gb,
                    "created_at": created_at_str,
                    "current_monthly_cost": current_monthly_cost
                },
                insights={
                    "action": "delete_snapshot",
                    "age_days": age_days,
                    "size_gb": size_gb
                },
            )
        ]


RULES = [OldSnapshotCleanupRule]

