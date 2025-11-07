"""Service helpers for generated reports (mock scaffolding)."""

from datetime import datetime
from typing import Dict, List
from string import Template

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


def create_mock_report(user_id: int, role_key: str) -> GeneratedReport:
    """Create a placeholder report entry for the requested role."""

    if role_key not in REPORT_ROLE_DEFINITIONS:
        raise ValueError(f'Unsupported role: {role_key}')

    role_info = REPORT_ROLE_DEFINITIONS[role_key]
    title = f"Отчет ({role_info['label']})"

    report = GeneratedReport(
        user_id=user_id,
        title=title,
        role=role_key,
        status=ReportStatus.IN_PROGRESS,
        content_html=_build_mock_html(role_info['label']),
        context_json={'role_label': role_info['label']}
    )
    db.session.add(report)
    db.session.commit()
    current_app.logger.info('Mock report created', extra={'user_id': user_id, 'role': role_key, 'report_id': report.id})
    return report


def list_reports_for_user(user_id: int) -> List[Dict]:
    """Return reports ordered by newest first for a given user."""

    reports = (
        GeneratedReport.query
        .filter_by(user_id=user_id)
        .order_by(GeneratedReport.created_at.desc())
        .all()
    )
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


def get_report_for_user(report_id: int, user_id: int) -> GeneratedReport:
    """Fetch a report ensuring it belongs to the given user."""

    report = GeneratedReport.query.filter_by(id=report_id, user_id=user_id).first()
    if not report:
        raise ValueError('Report not found')
    return report


