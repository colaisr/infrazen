"""Analytics-focused tools for the agent."""
import logging
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class AnalyticsTools:
    """Read-only analytics tools exposed to the LLM."""

    def __init__(self, flask_app):
        self.flask_app = flask_app

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------
    def _detect_anomalies(
        self,
        trends: List[Dict[str, Any]],
        sensitivity: float = 0.15,
        max_items: int = 3
    ) -> List[Dict[str, Any]]:
        """Simple anomaly detector based on day-to-day deltas."""
        if len(trends) < 3:
            return []

        deltas = []
        for idx in range(1, len(trends)):
            prev = float(trends[idx - 1].get('total_cost', 0) or 0)
            current = float(trends[idx].get('total_cost', 0) or 0)
            if prev <= 0:
                continue
            pct_change = (current - prev) / prev
            deltas.append({
                'date': trends[idx]['date'],
                'change_percent': round(pct_change * 100, 2),
                'current_cost': round(current, 2),
                'previous_cost': round(prev, 2)
            })

        significant = [d for d in deltas if abs(d['change_percent']) >= sensitivity * 100]
        significant.sort(key=lambda item: abs(item['change_percent']), reverse=True)
        return significant[:max_items]

    # ------------------------------------------------------------------
    # Context snapshot for system prompt
    # ------------------------------------------------------------------
    def build_context_snapshot(
        self,
        user_id: int,
        time_range_days: int = 30,
        top_items: int = 5
    ) -> Dict[str, Any]:
        if user_id is None:
            raise ValueError("user_id is required for analytics context snapshot")
        """Aggregate snapshot for analytics system prompt."""
        with self.flask_app.app_context():
            from app.core.services.analytics_service import AnalyticsService

            service = AnalyticsService(user_id)

            summary = service.get_executive_summary()
            trends = service.get_main_spending_trends(days=time_range_days)
            services = service.get_service_analysis().get('services', [])
            providers = service.get_provider_breakdown().get('providers', [])

            # Pending recommendations (sorted by potential savings)
            pending = self.get_pending_recommendations(user_id=user_id, limit=top_items)

            top_services = sorted(
                services,
                key=lambda item: item.get('cost', 0) or 0,
                reverse=True
            )[:top_items]

            anomalies = self._detect_anomalies(trends)

            latest_cost = None
            cost_change_percent = None
            if trends:
                latest_cost = float(trends[-1].get('total_cost', 0) or 0)
                if len(trends) >= 2:
                    prev_cost = float(trends[-2].get('total_cost', 0) or 0)
                    if prev_cost > 0:
                        cost_change_percent = round(((latest_cost - prev_cost) / prev_cost) * 100, 2)

            provider_share = [
                {
                    'name': item.get('name') or item.get('provider_name'),
                    'percentage': round(float(item.get('percentage', 0) or 0), 2),
                    'monthly_cost': round(float(item.get('cost', 0) or 0), 2)
                }
                for item in sorted(
                    providers,
                    key=lambda entry: entry.get('cost', 0) or 0,
                    reverse=True
                )[:top_items]
            ]

            return {
                'time_range_days': time_range_days,
                'summary': summary,
                'latest_monthly_cost': latest_cost,
                'latest_change_percent': cost_change_percent,
                'top_services': top_services,
                'provider_breakdown': provider_share,
                'pending_recommendations': pending,
                'anomalies': anomalies,
                'trend_points': trends[-top_items:]
            }

    # ------------------------------------------------------------------
    # Tool-facing helpers
    # ------------------------------------------------------------------
    def get_analytics_overview(
        self,
        time_range_days: int = 30,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        if user_id is None:
            raise ValueError("user_id is required for analytics overview")
        with self.flask_app.app_context():
            from app.core.services.analytics_service import AnalyticsService

            service = AnalyticsService(user_id)
            summary = service.get_executive_summary()
            trends = service.get_main_spending_trends(days=time_range_days)

            latest_cost = None
            if trends:
                latest_cost = round(float(trends[-1].get('total_cost', 0) or 0), 2)

            return {
                'time_range_days': time_range_days,
                'executive_summary': summary,
                'latest_monthly_cost': latest_cost,
                'points_available': len(trends)
            }

    def get_cost_trends(
        self,
        time_range_days: int = 30,
        include_provider_breakdown: bool = False,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        if user_id is None:
            raise ValueError("user_id is required for cost trends")
        with self.flask_app.app_context():
            from app.core.services.analytics_service import AnalyticsService

            service = AnalyticsService(user_id)
            trends = service.get_main_spending_trends(days=time_range_days)

            if not include_provider_breakdown:
                for point in trends:
                    point.pop('cost_by_provider', None)

            change = None
            if len(trends) >= 2:
                prev = float(trends[-2].get('total_cost', 0) or 0)
                current = float(trends[-1].get('total_cost', 0) or 0)
                if prev > 0:
                    change = round(((current - prev) / prev) * 100, 2)

            return {
                'time_range_days': time_range_days,
                'points': trends,
                'day_over_day_change_percent': change
            }

    def get_service_breakdown(
        self,
        top_n: int = 10,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        if user_id is None:
            raise ValueError("user_id is required for service breakdown")
        with self.flask_app.app_context():
            from app.core.services.analytics_service import AnalyticsService

            service = AnalyticsService(user_id)
            breakdown = service.get_service_analysis()
            services = sorted(
                breakdown.get('services', []),
                key=lambda item: item.get('cost', 0) or 0,
                reverse=True
            )[:top_n]

            return {
                'total_cost': round(float(breakdown.get('total_cost', 0) or 0), 2),
                'total_resources': breakdown.get('total_resources', 0),
                'services': services
            }

    def get_provider_breakdown(
        self,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        if user_id is None:
            raise ValueError("user_id is required for provider breakdown")
        with self.flask_app.app_context():
            from app.core.services.analytics_service import AnalyticsService

            service = AnalyticsService(user_id)
            breakdown = service.get_provider_breakdown()
            providers = breakdown.get('providers', [])

            total_cost = sum(float(item.get('cost', 0) or 0) for item in providers)
            for item in providers:
                cost = float(item.get('cost', 0) or 0)
                item['cost'] = round(cost, 2)
                if total_cost > 0:
                    item['percentage'] = round((cost / total_cost) * 100, 2)

            return {
                'total_cost': round(total_cost, 2),
                'providers': providers
            }

    def get_anomalies(
        self,
        time_range_days: int = 30,
        sensitivity: float = 0.15,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        if user_id is None:
            raise ValueError("user_id is required for anomalies analysis")
        with self.flask_app.app_context():
            from app.core.services.analytics_service import AnalyticsService

            service = AnalyticsService(user_id)
            trends = service.get_main_spending_trends(days=time_range_days)
            anomalies = self._detect_anomalies(trends, sensitivity=sensitivity)

            return {
                'time_range_days': time_range_days,
                'sensitivity_percent': round(sensitivity * 100, 2),
                'anomalies': anomalies
            }

    def get_pending_recommendations(
        self,
        user_id: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        with self.flask_app.app_context():
            from app.core.models import OptimizationRecommendation, CloudProvider, Resource

            recommendations = OptimizationRecommendation.query.filter_by(status='pending').all()

            filtered: List[Dict[str, Any]] = []
            provider_cache: Dict[int, Optional[CloudProvider]] = {}
            resource_cache: Dict[int, Optional[Resource]] = {}

            for rec in recommendations:
                owner_id = None
                if getattr(rec, 'cloud_provider', None):
                    owner_id = rec.cloud_provider.user_id
                elif getattr(rec, 'resource', None) and getattr(rec.resource, 'provider', None):
                    owner_id = rec.resource.provider.user_id
                elif rec.provider_id:
                    if rec.provider_id not in provider_cache:
                        provider_cache[rec.provider_id] = CloudProvider.query.get(rec.provider_id)
                    provider = provider_cache.get(rec.provider_id)
                    owner_id = provider.user_id if provider else None
                elif rec.resource_id:
                    if rec.resource_id not in resource_cache:
                        resource_cache[rec.resource_id] = Resource.query.get(rec.resource_id)
                    resource = resource_cache.get(rec.resource_id)
                    if resource and getattr(resource, 'provider', None):
                        owner_id = resource.provider.user_id

                if owner_id != user_id:
                    continue

                filtered.append({
                    'id': rec.id,
                    'title': rec.title,
                    'recommendation_type': rec.recommendation_type,
                    'potential_savings': float(rec.estimated_monthly_savings or rec.potential_savings or 0),
                    'severity': rec.severity,
                    'status': rec.status,
                    'resource_name': rec.resource_name,
                    'resource_type': rec.resource_type
                })

            filtered.sort(key=lambda item: item['potential_savings'], reverse=True)
            return filtered[:limit]

    def summarize_top_recommendations(
        self,
        limit: int = 5,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        if user_id is None:
            raise ValueError("user_id is required for recommendation summary")
        pending = self.get_pending_recommendations(user_id=user_id, limit=limit)
        total_savings = sum(item['potential_savings'] for item in pending)

        return {
            'limit': limit,
            'total_potential_savings': round(total_savings, 2),
            'pending': pending
        }

