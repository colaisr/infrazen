"""Report data builder for FinOps reports."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from agent_service.reports.snippet_manager import SnippetLibrary
from agent_service.tools.analytics_tools import AnalyticsTools
from agent_service.tools.recommendation_tools import RecommendationTools

logger = logging.getLogger(__name__)


class ReportDataBuilder:
    """Collect structured metrics for persona-specific FinOps reports."""

    def __init__(self, flask_app):
        self.flask_app = flask_app
        self.analytics_tools = AnalyticsTools(flask_app)
        self.recommendation_tools = RecommendationTools(flask_app)
        self.snippet_library = SnippetLibrary()

    def build_snapshot(
        self,
        user_id: int,
        role: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Return structured data for a report."""

        role = role or "cfo"
        context = context or {}
        time_range_days = context.get("time_range_days") or 30

        user_profile = self._get_user_profile(user_id)

        overview = self.analytics_tools.get_analytics_overview(
            user_id=user_id,
            time_range_days=time_range_days
        )

        cost_trends = self.analytics_tools.get_cost_trends(
            user_id=user_id,
            time_range_days=time_range_days,
            include_provider_breakdown=False
        )

        service_breakdown = self.analytics_tools.get_service_breakdown(
            user_id=user_id,
            top_n=10
        )

        provider_breakdown = self.analytics_tools.get_provider_breakdown(
            user_id=user_id
        )

        anomalies = self.analytics_tools.get_anomalies(
            user_id=user_id,
            time_range_days=time_range_days
        )

        recommendations_summary = self.analytics_tools.summarize_top_recommendations(
            user_id=user_id,
            limit=5
        )

        snapshot = {
            "generated_at": datetime.utcnow().isoformat(),
            "role": role,
            "time_range_days": time_range_days,
            "user": user_profile,
            "kpis": self._build_kpi_block(overview, recommendations_summary),
            "recommendations": recommendations_summary,
            "analytics": {
                "overview": overview,
                "cost_trends": cost_trends,
                "service_breakdown": service_breakdown,
                "provider_breakdown": provider_breakdown,
                "anomalies": anomalies
            }
        }
        snapshot["persona_snippets"] = self.snippet_library.render_for_role(role, snapshot)
        snapshot["snippet_context"] = self.snippet_library.build_context(snapshot)

        logger.info(
            "Report snapshot generated",
            extra={"user_id": user_id, "role": role, "time_range": time_range_days}
        )
        return snapshot

    def _build_kpi_block(
        self,
        overview: Dict[str, Any],
        recommendations_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        exec_summary = overview.get("executive_summary", {}) if overview else {}
        latest_cost = overview.get("latest_monthly_cost")
        change_percent = overview.get("latest_change_percent")

        return {
            "total_monthly_cost": exec_summary.get("total_monthly_cost"),
            "total_daily_cost": exec_summary.get("total_daily_cost"),
            "active_resources": exec_summary.get("active_resources"),
            "provider_success_rate": exec_summary.get("provider_success_rate"),
            "latest_monthly_cost": latest_cost,
            "latest_change_percent": change_percent,
            "pending_savings_total": recommendations_summary.get("total_potential_savings"),
            "pending_recommendations_count": len(recommendations_summary.get("pending", [])),
        }

    def _get_user_profile(self, user_id: int) -> Dict[str, Any]:
        with self.flask_app.app_context():
            from app.core.models import User

            user = User.query.filter_by(id=user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")

            return {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": getattr(user, "role", None)
            }


