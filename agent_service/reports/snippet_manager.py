"""Utility for loading and rendering persona snippet variations."""

import json
import os
from typing import Any, Dict, List

from jinja2 import Template


def _format_currency(value: Any) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return "0"
    return f"{number:,.2f}".replace(",", " ").rstrip("0").rstrip(".")


def _format_percent(value: Any, digits: int = 1) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return "0"
    return f"{number:.{digits}f}".rstrip("0").rstrip(".")


class SnippetLibrary:
    """Load reusable narrative snippets and render them with snapshot data."""

    def __init__(self, root_dir: str | None = None):
        base_dir = root_dir or os.path.dirname(__file__)
        snippet_path = os.path.join(base_dir, "snippets.json")
        with open(snippet_path, "r", encoding="utf-8") as handle:
            self._snippets: Dict[str, Dict[str, List[str]]] = json.load(handle)

    def render_for_role(self, role: str, snapshot: Dict[str, Any]) -> Dict[str, List[str]]:
        """Return rendered snippet variations for a persona role."""
        role_snippets = self._snippets.get(role, {})
        if not role_snippets:
            return {}

        context = self._build_context(snapshot)
        rendered: Dict[str, List[str]] = {}

        for section, variants in role_snippets.items():
            rendered_variants: List[str] = []
            for variant in variants:
                template = Template(variant)
                rendered_variants.append(template.render(**context))
            rendered[section] = rendered_variants

        return rendered

    def build_context(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Expose raw templating context for downstream narrative generation."""
        return self._build_context(snapshot)

    def _build_context(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Compose templating context from structured snapshot data."""
        kpis = snapshot.get("kpis", {}) or {}
        analytics = snapshot.get("analytics", {}) or {}
        recommendations = snapshot.get("recommendations", {}) or {}

        pending: List[Dict[str, Any]] = recommendations.get("pending") or []
        providers: List[Dict[str, Any]] = (analytics.get("provider_breakdown") or {}).get("providers") or []
        services: List[Dict[str, Any]] = (analytics.get("service_breakdown") or {}).get("services") or []
        anomalies: List[Dict[str, Any]] = (analytics.get("anomalies") or {}).get("anomalies") or []

        context = {
            "total_monthly_cost": _format_currency(kpis.get("total_monthly_cost")),
            "pending_savings_total": _format_currency(kpis.get("pending_savings_total")),
            "recommendation_count": len(pending),
            "anomalies_summary": self._summarize_anomalies(anomalies),
            "top_services": self._summarize_services(services),
            "top_provider_share": self._summarize_providers(providers),
            "provider_success_rate": _format_percent(kpis.get("provider_success_rate")),
            "data_quality": _format_percent(kpis.get("provider_success_rate")),
            "top_savings_item": self._top_savings_item(pending),
        }
        return context

    @staticmethod
    def _summarize_anomalies(anomalies: List[Dict[str, Any]]) -> str:
        if not anomalies:
            return "не анализируется в оперативном снимке"
        chunks = []
        for anomaly in anomalies[:3]:
            date = anomaly.get("date", "—")
            change = _format_percent(anomaly.get("change_percent"))
            chunks.append(f"{date} ({change}%)")
        if len(anomalies) > 3:
            chunks.append("…")
        return ", ".join(chunks)

    @staticmethod
    def _summarize_services(services: List[Dict[str, Any]]) -> str:
        if not services:
            return "нет данных"
        lines = []
        for service in services[:3]:
            name = service.get("name") or "Сервис"
            cost = _format_currency(service.get("cost"))
            percentage = _format_percent(service.get("percentage"))
            lines.append(f"{name} — {cost} ₽ ({percentage}%)")
        if len(services) > 3:
            lines.append("…")
        return ", ".join(lines)

    @staticmethod
    def _summarize_providers(providers: List[Dict[str, Any]]) -> str:
        if not providers:
            return "нет данных"
        lines = []
        for provider in providers[:3]:
            name = provider.get("name") or "Провайдер"
            percentage = _format_percent(provider.get("percentage"))
            lines.append(f"{name} ({percentage}%)")
        if len(providers) > 3:
            lines.append("…")
        return ", ".join(lines)

    @staticmethod
    def _top_savings_item(recommendations: List[Dict[str, Any]]) -> str:
        if not recommendations:
            return "нет активных рекомендаций"
        top_item = max(
            recommendations,
            key=lambda item: float(item.get("potential_savings") or 0),
        )
        title = top_item.get("title") or "Рекомендация"
        savings = _format_currency(top_item.get("potential_savings"))
        return f"{title} — {savings} ₽/мес"


