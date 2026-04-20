"""
Recommendations API: list, detail, and actions
"""
import json
from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
from sqlalchemy import or_, and_, desc, asc, func

from app.core.database import db
from app.core.models.recommendations import OptimizationRecommendation
from app.core.models.resource import Resource
from app.core.models.provider import CloudProvider
from app.core.models.user import User
from app.core.models.complete_sync import CompleteSync
from app.core.organization_context import get_current_organization_id

recommendations_bp = Blueprint('recommendations', __name__)


def _parse_float(value, default=None):
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _serialize(rec: OptimizationRecommendation):
    provider_code = None
    connection_name = None
    if rec.provider_id:
        provider = CloudProvider.find_by_id(rec.provider_id)
        if provider:
            provider_code = provider.provider_type
            connection_name = provider.connection_name

    return {
        'id': rec.id,
        'title': rec.title,
        'description': rec.description,
        'recommendation_type': rec.recommendation_type,
        'category': rec.category,
        'severity': rec.severity,
        'status': rec.status,
        'resource_id': rec.resource_id,
        'resource_name': rec.resource_name,
        'resource_type': rec.resource_type,
        'provider_id': rec.provider_id,
        'provider_code': provider_code,
        'connection_name': connection_name,
        # Provider-specific tracking
        'target_provider': rec.target_provider,
        'target_sku': rec.target_sku,
        'target_region': rec.target_region,
        'estimated_monthly_savings': rec.estimated_monthly_savings or rec.potential_savings or 0.0,
        'estimated_one_time_savings': rec.estimated_one_time_savings or 0.0,
        'currency': rec.currency,
        'first_seen_at': rec.first_seen_at.isoformat() if rec.first_seen_at else None,
        'created_at': rec.created_at.isoformat() if rec.created_at else None,
        'seen_at': rec.seen_at.isoformat() if rec.seen_at else None,
        'snoozed_until': rec.snoozed_until.isoformat() if rec.snoozed_until else None,
        'applied_at': rec.applied_at.isoformat() if rec.applied_at else None,
        'dismissed_at': rec.dismissed_at.isoformat() if rec.dismissed_at else None,
        'dismissed_reason': rec.dismissed_reason,
        'metrics_snapshot': rec.metrics_snapshot,
        'insights': rec.insights,
        'source': rec.source,
        # AI-generated text
        'ai_short_description': rec.ai_short_description,
        'ai_detailed_description': rec.ai_detailed_description,
        'ai_generated_at': rec.ai_generated_at.isoformat() if rec.ai_generated_at else None,
        # Verification tracking
        'last_verified_at': rec.last_verified_at.isoformat() if rec.last_verified_at else None,
        'verification_fail_count': rec.verification_fail_count,
    }


@recommendations_bp.route('/recommendations', methods=['GET'])
def list_recommendations():
    query = OptimizationRecommendation.query

    # Scope by current organization
    org_id = get_current_organization_id()
    if not org_id:
        return jsonify({'success': False, 'error': 'No active organization'}), 400
    
    # Filter by organization_id
    query = query.filter(OptimizationRecommendation.organization_id == org_id)

    # Filters
    provider = request.args.get('provider')
    status = request.args.get('status')
    severity = request.args.get('severity')
    rec_type = request.args.get('type')
    resource_type = request.args.get('resource_type')
    min_savings = _parse_float(request.args.get('min_savings'))
    max_savings = _parse_float(request.args.get('max_savings'))
    # confidence filter removed
    q = request.args.get('q')
    date_from = request.args.get('from')
    date_to = request.args.get('to')

    if provider:
        try:
            query = query.filter(OptimizationRecommendation.provider_id == int(provider))
        except ValueError:
            pass
    if status:
        query = query.filter(OptimizationRecommendation.status == status)
    if severity:
        query = query.filter(OptimizationRecommendation.severity == severity)
    if rec_type:
        # Map UI filter values to DB: use prefix match for category filters
        if rec_type == 'rightsizing':
            query = query.filter(OptimizationRecommendation.recommendation_type.startswith('rightsizing'))
        elif rec_type == 'cleanup':
            query = query.filter(
                OptimizationRecommendation.recommendation_type.startswith('cleanup')
            )
        elif rec_type == 'migrate':
            query = query.filter(
                OptimizationRecommendation.recommendation_type.in_(
                    ['migrate', 'price_compare_cross_provider']
                )
            )
        elif rec_type == 'shutdown':
            query = query.filter(
                OptimizationRecommendation.recommendation_type.in_(
                    ['shutdown', 'cleanup_stopped']
                )
            )
        else:
            query = query.filter(OptimizationRecommendation.recommendation_type == rec_type)
    if resource_type:
        # Map UI value "VM" to DB values server/vm
        if resource_type.upper() == 'VM':
            query = query.filter(
                OptimizationRecommendation.resource_type.in_(['server', 'vm'])
            )
        else:
            query = query.filter(OptimizationRecommendation.resource_type == resource_type)
    if min_savings is not None:
        query = query.filter((OptimizationRecommendation.estimated_monthly_savings >= min_savings) | (OptimizationRecommendation.potential_savings >= min_savings))
    if max_savings is not None:
        query = query.filter((OptimizationRecommendation.estimated_monthly_savings <= max_savings) | (OptimizationRecommendation.potential_savings <= max_savings))
    # confidence filter removed
    # Search will be handled on the client side for better Unicode support
    if date_from:
        try:
            df = datetime.fromisoformat(date_from)
            query = query.filter(OptimizationRecommendation.created_at >= df)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            query = query.filter(OptimizationRecommendation.created_at <= dt)
        except ValueError:
            pass

    tenant = request.args.get('tenant')
    enterprise_project = request.args.get('enterprise_project')
    if tenant or enterprise_project:
        query = query.join(Resource, OptimizationRecommendation.resource_id == Resource.id)
        query = query.filter(Resource.organization_id == org_id)
        if tenant:
            query = query.filter(Resource.tenant == tenant)
        if enterprise_project:
            bind = db.session.get_bind()
            dialect = (bind.dialect.name if bind else 'mysql')
            jx = func.json_extract(Resource.provider_config, '$.enterprise_project_name')
            if dialect == 'mysql':
                ep_expr = func.json_unquote(jx)
            else:
                ep_expr = jx
            query = query.filter(ep_expr == enterprise_project)

    # Sorting & pagination
    order_by = request.args.get('order_by', '-estimated_monthly_savings')
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 25)), 200)

    if order_by.startswith('-'):
        field = order_by[1:]
        direction = desc
    else:
        field = order_by
        direction = asc

    sortable = {
        'estimated_monthly_savings': OptimizationRecommendation.estimated_monthly_savings,
        'potential_savings': OptimizationRecommendation.potential_savings,
        'created_at': OptimizationRecommendation.created_at,
        'severity': OptimizationRecommendation.severity,
    }
    if field in sortable:
        query = query.order_by(direction(sortable[field]))
    else:
        query = query.order_by(desc(OptimizationRecommendation.created_at))

    items = query.paginate(page=page, per_page=page_size, error_out=False)
    return jsonify({
        'items': [_serialize(rec) for rec in items.items],
        'page': items.page,
        'page_size': items.per_page,
        'total': items.total
    })


@recommendations_bp.route('/recommendations/filter-options', methods=['GET'])
def recommendation_filter_options():
    """Distinct Tenant / Проект Enterprise values from resources that have recommendations."""
    org_id = get_current_organization_id()
    if not org_id:
        return jsonify({'success': False, 'error': 'No active organization'}), 400

    rows = (
        db.session.query(Resource.tenant, Resource.provider_config)
        .join(OptimizationRecommendation, OptimizationRecommendation.resource_id == Resource.id)
        .filter(
            OptimizationRecommendation.organization_id == org_id,
            Resource.organization_id == org_id,
        )
        .distinct()
        .all()
    )
    tenants = sorted({r[0] for r in rows if r[0]})
    enterprises = set()
    for row in rows:
        cfg_raw = row[1]
        if not cfg_raw:
            continue
        try:
            cfg = json.loads(cfg_raw) if isinstance(cfg_raw, str) else (cfg_raw or {})
            ep = (cfg.get('enterprise_project_name') or '').strip()
            if ep:
                enterprises.add(ep)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    return jsonify({
        'success': True,
        'tenants': tenants,
        'enterprise_projects': sorted(enterprises),
    })


@recommendations_bp.route('/recommendations/<int:rec_id>', methods=['GET'])
def get_recommendation(rec_id: int):
    rec = OptimizationRecommendation.find_by_id(rec_id)
    if not rec:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(_serialize(rec))


def _apply_action(rec: OptimizationRecommendation, action: str, payload: dict):
    now = datetime.utcnow()
    if action == 'seen':
        rec.status = 'seen'
        rec.seen_at = now
    elif action == 'implemented':
        rec.status = 'implemented'
        rec.applied_at = now
    elif action == 'dismiss':
        rec.status = 'dismissed'
        rec.dismissed_at = now
        rec.dismissed_reason = payload.get('reason')
    elif action == 'restore':
        rec.status = 'pending'
        rec.dismissed_at = None
        rec.dismissed_reason = None
    else:
        return False
    return True


@recommendations_bp.route('/recommendations/<int:rec_id>/action', methods=['POST'])
def recommendation_action(rec_id: int):
    # Allow demo users to interact with recommendations
    
    rec = OptimizationRecommendation.find_by_id(rec_id)
    if not rec:
        return jsonify({'error': 'Not found'}), 404
    payload = request.get_json(force=True) or {}
    action = (payload.get('action') or '').strip().lower()
    if not _apply_action(rec, action, payload):
        return jsonify({'error': 'Unsupported action'}), 400
    db.session.commit()
    return jsonify(_serialize(rec))


@recommendations_bp.route('/recommendations/bulk', methods=['POST'])
def bulk_action():
    # Allow demo users to interact with recommendations
    
    payload = request.get_json(force=True) or {}
    ids = payload.get('ids') or []
    action = (payload.get('action') or '').strip().lower()
    if not ids or not action:
        return jsonify({'error': 'ids and action are required'}), 400
    recs = OptimizationRecommendation.query.filter(OptimizationRecommendation.id.in_(ids)).all()
    for rec in recs:
        _apply_action(rec, action, payload)
    db.session.commit()
    return jsonify({'updated': len(recs)})


@recommendations_bp.route('/recommendations/<int:rec_id>', methods=['DELETE'])
def delete_recommendation(rec_id: int):
    # Check if demo user (read-only)
    from app.api.auth import check_demo_user_write_access
    demo_check = check_demo_user_write_access()
    if demo_check:
        return demo_check
    
    rec = OptimizationRecommendation.find_by_id(rec_id)
    if not rec:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(rec)
    db.session.commit()
    return jsonify({'status': 'deleted'})


@recommendations_bp.route('/recommendations/summary', methods=['GET'])
def recommendations_summary():
    """Return recommendations summary for the most recent successful/partial complete sync of current user."""
    # Resolve current user
    current_user_id = None
    try:
        user_data = session.get('user') or {}
        if user_data.get('email') == 'demo@infrazen.com':
            demo_user = User.find_by_email('demo@infrazen.com')
            if demo_user:
                current_user_id = demo_user.id
        else:
            current_user_id = user_data.get('db_id')
    except Exception:
        current_user_id = None

    if not current_user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    # Find last sync
    org_id = get_current_organization_id()
    if not org_id:
        return jsonify({'success': False, 'error': 'No active organization'}), 400
    
    cs = CompleteSync.query.filter_by(user_id=current_user_id, organization_id=org_id).order_by(CompleteSync.sync_started_at.desc()).first()
    if not cs:
        return jsonify({'error': 'No syncs found'}), 404

    cfg = cs.get_sync_config() or {}
    summary = cfg.get('recommendations_summary') or {}
    return jsonify({
        'complete_sync_id': cs.id,
        'sync_status': cs.sync_status,
        'recommendations_summary': summary,
    })


@recommendations_bp.route('/recommendations/clear-all', methods=['POST'])
def clear_all_recommendations():
    """Clear all recommendations for the current user. Next sync will start fresh."""
    # Check if demo user (read-only)
    from app.api.auth import check_demo_user_write_access
    demo_check = check_demo_user_write_access()
    if demo_check:
        return demo_check
    
    # Resolve current user
    current_user_id = None
    try:
        user_data = session.get('user') or {}
        if user_data.get('email') == 'demo@infrazen.com':
            demo_user = User.find_by_email('demo@infrazen.com')
            if demo_user:
                current_user_id = demo_user.id
        else:
            current_user_id = user_data.get('db_id')
    except Exception:
        current_user_id = None

    if not current_user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Find all recommendations for this user's providers
        # Note: Can't use delete() with join(), so we get IDs first
        rec_ids_query = db.session.query(OptimizationRecommendation.id).join(
            CloudProvider, 
            OptimizationRecommendation.provider_id == CloudProvider.id
        ).filter(CloudProvider.user_id == current_user_id)
        
        rec_ids = [r[0] for r in rec_ids_query.all()]
        count = len(rec_ids)
        
        if count == 0:
            return jsonify({
                'status': 'success',
                'deleted_count': 0,
                'message': 'Нет рекомендаций для удаления.'
            })
        
        # Delete recommendations by ID
        OptimizationRecommendation.query.filter(
            OptimizationRecommendation.id.in_(rec_ids)
        ).delete(synchronize_session=False)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'deleted_count': count,
            'message': f'Удалено {count} рекомендаций. При следующей синхронизации система создаст новые рекомендации.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Internal server error',
            'detail': str(e)
        }), 500


