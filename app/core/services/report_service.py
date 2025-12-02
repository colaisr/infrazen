"""Service helpers for generated reports (mock scaffolding)."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from string import Template

import requests
from flask import current_app

from app.core.database import db
from app.core.models import GeneratedReport, ReportStatus


REPORT_ROLE_DEFINITIONS: Dict[str, Dict[str, str]] = {
    'cfo': {
        'key': 'cfo',
        'label': 'CFO',
        'description': 'Финансовый директор — бюджет, прогноз, unit-экономика.'
    },
    'cto': {
        'key': 'cto',
        'label': 'CTO / CIO',
        'description': 'Техническое руководство — эффективность, риски, архитектура.'
    },
    'product': {
        'key': 'product',
        'label': 'Product / Business Owner',
        'description': 'Продуктовая команда — unit-cost, маржинальность, клиенты.'
    },
    'finops': {
        'key': 'finops',
        'label': 'FinOps Lead',
        'description': 'Руководитель FinOps — данные, процессы, экономия.'
    },
}


def get_report_roles() -> List[Dict[str, str]]:
    """Return available report roles for UI rendering."""

    return list(REPORT_ROLE_DEFINITIONS.values())


def _build_mock_html(role_label: str) -> str:
    generated_at = datetime.utcnow().strftime('%d.%m.%Y %H:%M')
    template = Template(
        """<!DOCTYPE html>
<html lang="ru">
  <head>
    <meta charset="utf-8">
    <title>Отчет в подготовке</title>
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: #f9fafb;
        color: #111827;
        margin: 0;
        padding: 40px;
      }
      .card {
        max-width: 720px;
        margin: 60px auto;
        padding: 48px;
        border-radius: 16px;
        background: #ffffff;
        box-shadow: 0 20px 45px rgba(15, 23, 42, 0.12);
      }
      .title {
        font-size: 28px;
        font-weight: 700;
        color: #1e40af;
        margin-bottom: 16px;
      }
      .subtitle {
        font-size: 18px;
        color: #4b5563;
        margin-bottom: 32px;
        line-height: 1.6;
      }
      .pill {
        display: inline-flex;
        align-items: center;
        background: #e0e7ff;
        color: #1e3a8a;
        padding: 6px 14px;
        border-radius: 999px;
        font-weight: 600;
        margin-bottom: 24px;
      }
      .note {
        font-size: 16px;
        line-height: 1.6;
        color: #374151;
        margin-bottom: 12px;
      }
      .footer {
        margin-top: 40px;
        font-size: 14px;
        color: #6b7280;
      }
    </style>
  </head>
  <body>
    <div class="card">
      <div class="pill">$role</div>
      <div class="title">Отчет формируется</div>
      <div class="subtitle">
        Мы готовим персонализированный FinOps отчет. Как только генерация будет завершена,
        здесь появится версия для просмотра.
      </div>
      <div class="note">🕒 Сгенерировано: $generated</div>
      <div class="note">
        📌 Этот черновик создан для роли <strong>$role</strong>. После завершения реализации отчета раздел
        автоматически обновится.
      </div>
      <div class="footer">InfraZen FinOps Platform</div>
    </div>
  </body>
</html>"""
    )
    return template.substitute(role=role_label, generated=generated_at)


def _generate_report_payload(user_id: int, role_key: str, context: Optional[Dict] = None) -> Tuple[Optional[Dict], Optional[str]]:
    try:
        agent_url = current_app.config.get('AGENT_SERVICE_URL', 'http://127.0.0.1:8001')
        endpoint = f"{agent_url}/v1/reports/render"
        response = requests.post(
            endpoint,
            json={
                "user_id": user_id,
                "role": role_key,
                "context": context or {}
            },
            timeout=20
        )
        if not response.ok:
            current_app.logger.warning(
                "Agent report render request failed (%s): %s",
                response.status_code,
                response.text[:200]
            )
            return None, None
        payload = response.json()
        return payload.get('snapshot'), payload.get('html')
    except Exception as exc:  # pylint: disable=broad-except
        current_app.logger.warning("Failed to generate report payload: %s", exc)
        return None, None


def create_mock_report(user_id: int, role_key: str, organization_id: Optional[int] = None) -> GeneratedReport:
    """Create a placeholder report entry for the requested role."""

    if role_key not in REPORT_ROLE_DEFINITIONS:
        raise ValueError(f'Unsupported role: {role_key}')

    role_info = REPORT_ROLE_DEFINITIONS[role_key]
    title = f"Отчет ({role_info['label']})"
    
    # Pass organization_id in context so agent service can filter data correctly
    context = {}
    if organization_id:
        context['organization_id'] = organization_id
    
    snapshot, rendered_html = _generate_report_payload(user_id, role_key, context)

    report = GeneratedReport(
        user_id=user_id,
        organization_id=organization_id,
        title=title,
        role=role_key,
        status=ReportStatus.READY if rendered_html else ReportStatus.IN_PROGRESS,
        content_html=rendered_html or _build_mock_html(role_info['label']),
        context_json={
            'role_label': role_info['label'],
            'snapshot': snapshot
        }
    )
    db.session.add(report)
    db.session.commit()
    current_app.logger.info('Mock report created', extra={'user_id': user_id, 'organization_id': organization_id, 'role': role_key, 'report_id': report.id})
    return report


def list_reports_for_user(user_id: int, organization_id: Optional[int] = None) -> List[Dict]:
    """Return reports ordered by newest first for a given user/organization."""

    query = GeneratedReport.query
    if organization_id:
        # Filter by organization - viewers see all reports in the organization
        query = query.filter_by(organization_id=organization_id)
    else:
        # Fallback: filter by user_id if no org context
        query = query.filter_by(user_id=user_id)
    
    reports = query.order_by(GeneratedReport.created_at.desc()).all()
    
    results = []
    for report in reports:
        results.append({
            'id': report.id,
            'title': report.title,
            'role': report.role,
            'status': report.status.value if isinstance(report.status, ReportStatus) else report.status,
            'created_at': report.created_at.isoformat(),
            'updated_at': report.updated_at.isoformat() if report.updated_at else None,
        })
    return results


def get_report_for_user(report_id: int, user_id: int, organization_id: Optional[int] = None) -> GeneratedReport:
    """Fetch a report ensuring it belongs to the given user/organization."""

    query = GeneratedReport.query.filter_by(id=report_id)
    if organization_id:
        # Filter by organization - viewers can view all reports in the organization
        query = query.filter_by(organization_id=organization_id)
    else:
        # Fallback: filter by user_id if no org context
        query = query.filter_by(user_id=user_id)
    
    report = query.first()
    if not report:
        raise ValueError('Report not found')
    return report


def delete_report_for_user(report_id: int, user_id: int, organization_id: Optional[int] = None) -> None:
    """Delete a generated report belonging to the given user/organization."""

    query = GeneratedReport.query.filter_by(id=report_id)
    if organization_id:
        # Filter by organization
        query = query.filter_by(organization_id=organization_id)
    else:
        # Fallback: filter by user_id if no org context
        query = query.filter_by(user_id=user_id)
    
    report = query.first()
    if not report:
        raise ValueError('Report not found')
    db.session.delete(report)
    db.session.commit()


