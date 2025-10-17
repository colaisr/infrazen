"""
Recommendations API: list, detail, and actions
"""
from flask import Blueprint, request, jsonify, session
from datetime import datetime
from sqlalchemy import or_, and_, desc, asc

from app.core.database import db
from app.core.models.recommendations import OptimizationRecommendation
from app.core.models.resource import Resource
from app.core.models.provider import CloudProvider
from app.core.models.user import User

recommendations_bp = Blueprint('recommendations', __name__)


def _parse_float(value, default=None):
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _serialize(rec: OptimizationRecommendation):
    provider_code = None
    if rec.provider_id:
        provider = CloudProvider.find_by_id(rec.provider_id)
        provider_code = provider.provider_type if provider else None

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
    }


@recommendations_bp.route('/recommendations', methods=['GET'])
def list_recommendations():
    query = OptimizationRecommendation.query

    # Scope by current user (including demo session mapped to seeded demo user)
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

    if current_user_id:
        query = query.join(CloudProvider, OptimizationRecommendation.provider_id == CloudProvider.id)
        query = query.filter(CloudProvider.user_id == current_user_id)

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
        query = query.filter(OptimizationRecommendation.recommendation_type == rec_type)
    if resource_type:
        query = query.filter(OptimizationRecommendation.resource_type == resource_type)
    if min_savings is not None:
        query = query.filter((OptimizationRecommendation.estimated_monthly_savings >= min_savings) | (OptimizationRecommendation.potential_savings >= min_savings))
    if max_savings is not None:
        query = query.filter((OptimizationRecommendation.estimated_monthly_savings <= max_savings) | (OptimizationRecommendation.potential_savings <= max_savings))
    # confidence filter removed
    if q:
        # Use Python-level filtering for Unicode/Cyrillic character support
        # Database LIKE queries don't handle Cyrillic properly, so we filter in Python
        all_recommendations = query.all()
        filtered_recommendations = []
        search_lower = q.lower()
        
        for rec in all_recommendations:
            if (search_lower in (rec.title or "").lower() or 
                search_lower in (rec.description or "").lower() or 
                search_lower in (rec.resource_name or "").lower()):
                filtered_recommendations.append(rec)
        
        # Create a new query with the filtered IDs
        if filtered_recommendations:
            rec_ids = [rec.id for rec in filtered_recommendations]
            query = query.filter(OptimizationRecommendation.id.in_(rec_ids))
        else:
            # Return empty result if no matches
            query = query.filter(OptimizationRecommendation.id == -1)
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
        rec.snoozed_until = None
    elif action == 'snooze':
        rec.status = 'snoozed'
        until = payload.get('until')
        try:
            rec.snoozed_until = datetime.fromisoformat(until) if until else None
        except Exception:
            rec.snoozed_until = None
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


