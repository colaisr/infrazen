"""Render HTML reports from structured snapshot data."""

import logging
import os
from datetime import datetime
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound

from agent_service.reports.snippet_manager import SnippetLibrary

logger = logging.getLogger(__name__)


class ReportRenderer:
    """Render persona-specific FinOps reports from data snapshots."""

    def __init__(self):
        templates_path = os.path.join(os.path.dirname(__file__), "templates")
        self.env = Environment(
            loader=FileSystemLoader(templates_path),
            autoescape=select_autoescape(['html', 'xml'])
        )
        self.env.filters['strftime'] = self._format_datetime
        self.env.globals['now'] = datetime.utcnow
        self.role_template_map = {
            'cfo': 'report_cfo.html',
            'cto': 'report_cto.html',
            'product': 'report_product.html',
            'finops': 'report_finops.html',
        }
        self.role_label_map = {
            'cfo': 'CFO / Finance',
            'cto': 'CTO / CIO',
            'product': 'Product / Business Owner',
            'finops': 'Head of FinOps'
        }
        self.snippet_library = SnippetLibrary()

    def render(self, snapshot: Dict[str, Any], role: str) -> str:
        """Render HTML for the given persona role."""

        template_name = self.role_template_map.get(role, 'report_cfo.html')
        try:
            template = self.env.get_template(template_name)
        except TemplateNotFound as exc:
            logger.warning("Report template not found for role %s, fallback to CFO: %s", role, exc)
            template = self.env.get_template('report_cfo.html')

        generated_at = snapshot.get('generated_at')
        user = snapshot.get('user', {})
        persona_snippets = snapshot.get('persona_snippets') or self.snippet_library.render_for_role(role, snapshot)
        snippet_context = snapshot.get('snippet_context') or self.snippet_library.build_context(snapshot)

        context = {
            'generated_at': generated_at,
            'time_range_days': snapshot.get('time_range_days', 30),
            'role': role,
            'role_label': self.role_label_map.get(role, 'CFO / Finance'),
            'user': user,
            'user_display': self._format_user(user),
            'kpis': snapshot.get('kpis', {}),
            'recommendations': snapshot.get('recommendations', {}),
            'analytics': snapshot.get('analytics', {}),
            'narrative': snapshot.get('narrative', {}),
            'persona_snippets': persona_snippets,
            'snippet_context': snippet_context,
        }
        html = template.render(**context)
        logger.info("Report rendered with template %s", template_name)
        return html

    @staticmethod
    def _format_user(user: Dict[str, Any]) -> str:
        first = user.get('first_name')
        last = user.get('last_name')
        if first or last:
            return " ".join(filter(None, [first, last]))
        return user.get('email', 'Пользователь')

    @staticmethod
    def _format_datetime(value: Any, fmt: str = '%d.%m.%Y %H:%M') -> str:
        if not value:
            return ''
        if isinstance(value, datetime):
            return value.strftime(fmt)
        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return parsed.strftime(fmt)
        except Exception:  # pylint: disable=broad-except
            return str(value)


_renderer = ReportRenderer()


def render_report_html(snapshot: Dict[str, Any], role: str) -> str:
    """Module-level helper for rendering."""

    return _renderer.render(snapshot, role)

