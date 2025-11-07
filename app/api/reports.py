"""API endpoints for generated reports scaffolding."""

from flask import Blueprint, jsonify, request, session
from flask_login import login_required, current_user

from app.core.services import report_service


reports_bp = Blueprint('reports_api', __name__)


def _get_effective_user_id() -> int:
    user_data = session.get('user', {})
    return user_data.get('db_id') or current_user.id


@reports_bp.route('/reports/roles', methods=['GET'])
@login_required
def list_roles():
    roles = report_service.get_report_roles()
    return jsonify({'success': True, 'roles': roles})


@reports_bp.route('/reports', methods=['GET'])
@login_required
def list_reports():
    user_id = _get_effective_user_id()
    reports = report_service.list_reports_for_user(user_id)
    return jsonify({'success': True, 'reports': reports})


@reports_bp.route('/reports', methods=['POST'])
@login_required
def create_report():
    payload = request.get_json() or {}
    role_key = payload.get('role')
    if not role_key:
        return jsonify({'success': False, 'error': 'role is required'}), 400

    try:
        report = report_service.create_mock_report(_get_effective_user_id(), role_key)
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400

    return jsonify({
        'success': True,
        'report': {
            'id': report.id,
            'title': report.title,
            'role': report.role,
            'status': report.status.value,
            'created_at': report.created_at.isoformat(),
            'updated_at': report.updated_at.isoformat() if report.updated_at else None,
        }
    }), 201


@reports_bp.route('/reports/<int:report_id>', methods=['GET'])
@login_required
def get_report(report_id: int):
    try:
        report = report_service.get_report_for_user(report_id, _get_effective_user_id())
    except ValueError:
        return jsonify({'success': False, 'error': 'Report not found'}), 404

    return jsonify({
        'success': True,
        'report': {
            'id': report.id,
            'title': report.title,
            'role': report.role,
            'status': report.status.value,
            'created_at': report.created_at.isoformat(),
            'updated_at': report.updated_at.isoformat() if report.updated_at else None,
            'content_html': report.content_html,
        }
    })


