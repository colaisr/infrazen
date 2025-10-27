"""
Admin API routes for user management and impersonation
"""
from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify, flash
from datetime import datetime
import logging
from app.core.database import db
from app.core.models.user import User
from app.core.models.provider import CloudProvider
from app.core.models.resource import Resource
from app.core.models.unrecognized_resource import UnrecognizedResource
from app.core.models.provider_catalog import ProviderCatalog
from app.core.models.provider_admin_credentials import ProviderAdminCredentials
from app.core.models.recommendation_settings import RecommendationRuleSetting
from app.api.auth import validate_session
from app.providers.resource_registry import resource_registry
from app.core.models.provider_resource_type import ProviderResourceType

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

def require_admin():
    """Check if current user is admin"""
    user = session.get('user')
    if not user or not user.get('is_admin'):
        return jsonify({'success': False, 'error': 'Admin access required'})
    return None

@admin_bp.route('/users')
def list_users():
    """List all users (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        role_filter = request.args.get('role', '')
        include_demo = request.args.get('include_demo', 'false').lower() == 'true'
        
        query = User.query
        
        # Exclude demo users by default
        if not include_demo:
            query = query.filter(User.role != 'demouser')
        
        # Apply search filter
        if search:
            query = query.filter(
                db.or_(
                    User.email.contains(search),
                    User.first_name.contains(search),
                    User.last_name.contains(search),
                    User.company.contains(search)
                )
            )
        
        # Apply role filter
        if role_filter:
            query = query.filter(User.role == role_filter)
        
        # Order by creation date
        query = query.order_by(User.created_at.desc())
        
        # Paginate results
        users = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'success': True,
            'users': [user.to_dict() for user in users.items],
            'pagination': {
                'page': users.page,
                'pages': users.pages,
                'per_page': users.per_page,
                'total': users.total,
                'has_next': users.has_next,
                'has_prev': users.has_prev
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/users/<int:user_id>')
def get_user(user_id):
    """Get user details (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        user = User.find_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'})
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update user (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        user = User.find_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'})
        
        # Prevent modifying demo user role
        if user.is_demo_user():
            return jsonify({'success': False, 'error': 'Cannot modify demo user. Demo users are read-only.'})
        
        data = request.get_json()
        
        # Update allowed fields
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'company' in data:
            user.company = data['company']
        if 'role' in data:
            user.role = data['role']
        if 'is_active' in data:
            # Convert string to boolean
            user.is_active = data['is_active'] in [True, 'true', 'True', '1', 1]
        if 'admin_notes' in data:
            user.admin_notes = data['admin_notes']
        if 'permissions' in data:
            user.set_permissions(data['permissions'])
        
        user.updated_at = datetime.now()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete user (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        user = User.find_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'})
        
        # Don't allow deleting super admins
        if user.is_super_admin():
            return jsonify({'success': False, 'error': 'Cannot delete super admin'})
        
        # Don't allow deleting demo users
        if user.is_demo_user():
            return jsonify({'success': False, 'error': 'Cannot delete demo user'})
        
        # Don't allow self-deletion
        current_user_id = session.get('user', {}).get('db_id')
        if user.id == current_user_id:
            return jsonify({'success': False, 'error': 'Cannot delete your own account'})
        
        user.delete()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/users', methods=['POST'])
def create_user():
    """Create new user (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('email'):
            return jsonify({'success': False, 'error': 'Email is required'})
        
        # Check if user already exists
        existing_user = User.find_by_email(data['email'])
        if existing_user:
            return jsonify({'success': False, 'error': 'User with this email already exists'})
        
        # Create new user
        user = User(
            email=data['email'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            company=data.get('company', ''),
            role=data.get('role', 'user'),
            is_active=data.get('is_active', True),
            created_by_admin=True,
            admin_notes=data.get('admin_notes', '')
        )
        
        # No username needed - email is the primary identifier
        
        # Set permissions if provided
        if 'permissions' in data:
            user.set_permissions(data['permissions'])
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/impersonate/<int:user_id>')
def impersonate_user(user_id):
    """Impersonate another user (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        # Check if current user can impersonate
        current_user_data = session.get('user', {})
        if not current_user_data.get('permissions', {}).get('impersonate_users'):
            return jsonify({'success': False, 'error': 'Impersonation permission required'})
        
        # Get target user
        target_user = User.find_by_id(user_id)
        if not target_user:
            return jsonify({'success': False, 'error': 'User not found'})
        
        # Store original user info for restoration
        session['original_user'] = current_user_data
        
        # Switch to target user
        session['user'] = {
            'id': str(target_user.id),
            'db_id': target_user.id,
            'google_id': target_user.google_id,
            'email': target_user.email,
            'name': f"{target_user.first_name} {target_user.last_name}".strip() or target_user.email.split('@')[0],
            'picture': target_user.google_picture or '',
            'role': target_user.role,
            'is_admin': target_user.is_admin(),
            'permissions': target_user.get_permissions(),
            'impersonated': True,
            'impersonated_by': current_user_data.get('email')
        }
        
        return jsonify({
            'success': True,
            'message': f'Now impersonating {target_user.email}',
            'redirect': url_for('main.dashboard')
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/stop-impersonating')
def stop_impersonating():
    """Stop impersonating and return to original user"""
    try:
        if 'original_user' not in session:
            return jsonify({'success': False, 'error': 'Not currently impersonating'})
        
        # Restore original user
        session['user'] = session.pop('original_user')
        
        return jsonify({
            'success': True,
            'message': 'Stopped impersonating',
            'redirect': url_for('main.dashboard')
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/dashboard')
def dashboard():
    """Admin dashboard page"""
    admin_check = require_admin()
    if admin_check:
        return redirect(url_for('main.dashboard'))
    
    # Get current user from session
    user = session.get('user', {})
    return render_template('admin/dashboard.html', user=user)

@admin_bp.route('/users-page')
def users_page():
    """Users management page"""
    admin_check = require_admin()
    if admin_check:
        return redirect(url_for('main.dashboard'))
    
    # Get current user from session
    user = session.get('user', {})
    return render_template('admin/users.html', user=user)

# Unrecognized Resources Management

@admin_bp.route('/unrecognized-resources')
def list_unrecognized_resources():
    """List all unrecognized resources (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        provider_filter = request.args.get('provider', '')
        resource_type_filter = request.args.get('resource_type', '')
        resolved_filter = request.args.get('resolved', '')
        
        query = UnrecognizedResource.query
        
        # Apply search filter
        if search:
            query = query.filter(
                db.or_(
                    UnrecognizedResource.resource_name.contains(search),
                    UnrecognizedResource.resource_id.contains(search)
                )
            )
        
        # Apply provider filter
        if provider_filter:
            query = query.filter(UnrecognizedResource.provider_id == provider_filter)
        
        # Apply resource type filter
        if resource_type_filter:
            query = query.filter(UnrecognizedResource.resource_type == resource_type_filter)
        
        # Apply resolved filter
        if resolved_filter == 'true':
            query = query.filter(UnrecognizedResource.is_resolved == True)
        elif resolved_filter == 'false':
            query = query.filter(UnrecognizedResource.is_resolved == False)
        
        # Order by discovery date (newest first)
        query = query.order_by(UnrecognizedResource.discovered_at.desc())
        
        # Paginate
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # Convert to dict format
        resources = []
        for resource in pagination.items:
            resources.append(resource.to_dict())
        
        return jsonify({
            'success': True,
            'data': resources,
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch unrecognized resources: {str(e)}'
        })

@admin_bp.route('/unrecognized-resources/<int:resource_id>', methods=['GET'])
def get_unrecognized_resource(resource_id: int):
    """Return a single unrecognized resource including billing_data (admin only)."""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    try:
        item = UnrecognizedResource.query.get_or_404(resource_id)
        data = item.to_dict()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/unrecognized-resources/<int:resource_id>', methods=['DELETE'])
def delete_unrecognized_resource(resource_id):
    """Delete an unrecognized resource (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        resource = UnrecognizedResource.query.get_or_404(resource_id)
        
        db.session.delete(resource)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Unrecognized resource deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to delete unrecognized resource: {str(e)}'
        })

@admin_bp.route('/unrecognized-resources/<int:resource_id>/resolve', methods=['POST'])
def resolve_unrecognized_resource(resource_id):
    """Mark an unrecognized resource as resolved (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        data = request.get_json()
        resolution_notes = data.get('resolution_notes', '') if data else ''
        
        resource = UnrecognizedResource.query.get_or_404(resource_id)
        
        resource.is_resolved = True
        resource.resolved_at = datetime.utcnow()
        resource.resolved_by = session.get('user', {}).get('id')
        resource.resolution_notes = resolution_notes
        resource.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Unrecognized resource marked as resolved'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to resolve unrecognized resource: {str(e)}'
        })

@admin_bp.route('/unrecognized-resources/<int:resource_id>/promote', methods=['POST'])
def promote_unrecognized_resource(resource_id: int):
    """Promote an unrecognized resource to known provider type inventory.

    Body: { unified_type: 'managed_db', display_name?, icon?, raw_alias? }
    """
    admin_check = require_admin()
    if admin_check:
        return admin_check
    try:
        data = request.get_json(force=True) or {}
        unified_type = (data.get('unified_type') or '').strip()
        if not unified_type:
            return jsonify({'success': False, 'error': 'unified_type is required'}), 400

        item = UnrecognizedResource.query.get_or_404(resource_id)
        provider = CloudProvider.query.get(item.provider_id)
        if not provider:
            return jsonify({'success': False, 'error': 'Provider not found'}), 404

        # Upsert provider resource type
        prt = ProviderResourceType.query.filter_by(provider_type=provider.provider_type, unified_type=unified_type).first()
        if prt is None:
            prt = ProviderResourceType(
                provider_type=provider.provider_type,
                unified_type=unified_type,
                display_name=data.get('display_name'),
                icon=data.get('icon'),
                enabled=True,
                raw_aliases=None
            )
            db.session.add(prt)
        # Merge observed raw type into alias list automatically (ignore client alias input)
        import json
        aliases = []
        if prt.raw_aliases:
            try:
                aliases = json.loads(prt.raw_aliases)
            except Exception:
                aliases = []
        observed_alias = (item.resource_type or '').strip()
        if observed_alias and observed_alias not in aliases:
            aliases.append(observed_alias)
        if aliases:
            prt.raw_aliases = json.dumps(aliases, ensure_ascii=False)

        # Mark unrecognized as resolved with note
        item.is_resolved = True
        item.resolved_at = datetime.utcnow()
        item.resolved_by = session.get('user', {}).get('id')
        item.resolution_notes = (item.resolution_notes or '') + f"\nPromoted as {unified_type}"

        db.session.commit()
        return jsonify({'success': True, 'provider_type': provider.provider_type, 'unified_type': unified_type, 'alias_added': observed_alias})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/unrecognized-resources-page')
def unrecognized_resources_page():
    """Unrecognized resources management page"""
    admin_check = require_admin()
    if admin_check:
        return redirect(url_for('main.dashboard'))
    
    # Get current user from session
    user = session.get('user', {})
    return render_template('admin/unrecognized_resources.html', user=user)

# Recommendations Settings (blank scaffold)
@admin_bp.route('/recommendations-settings-page')
def recommendations_settings_page():
    """Recommendations settings page (admin only)."""
    admin_check = require_admin()
    if admin_check:
        return redirect(url_for('main.dashboard'))
    user = session.get('user', {})
    # Build bootstrap payload to avoid empty page if fetch fails
    rules_payload = _build_reco_rules_payload()
    return render_template('admin/recommendations_settings.html', user=user, rules_bootstrap=rules_payload)

def _build_reco_rules_payload():
    try:
        from app.core.recommendations.registry import RuleRegistry
        reg = RuleRegistry(); reg.discover()
        global_rules = [r for r in reg.global_rules() if not getattr(r, 'id', '').startswith('debug.')]
        resource_rules = [r for r in reg.resource_rules() if not getattr(r, 'id', '').startswith('debug.')]
        settings_index = {}
        try:
            settings = RecommendationRuleSetting.query.all()
            for s in settings:
                settings_index[(s.rule_id, s.scope, s.provider_type or '', s.resource_type or '')] = s
        except Exception:
            # Table may not exist yet; treat as all enabled by default
            settings_index = {}

        def rule_dict(rule, scope, provider_type=None, resource_type=None):
            rid = getattr(rule, 'id') if isinstance(getattr(rule, 'id', None), str) else rule.id
            key = (rid, scope, provider_type or '', resource_type or '')
            s = settings_index.get(key)
            return {
                'rule_id': rid,
                'name': getattr(rule, 'name', rid),
                'scope': scope,
                'provider_type': provider_type,
                'resource_type': resource_type,
                'enabled': True if s is None else bool(s.enabled),
                'description': getattr(rule, 'description', None) or (s.description if s else None),
            }

        global_payload = [rule_dict(r, 'global') for r in global_rules]
        resource_payload = []
        # Expand resource rules by enabled providers and known provider types (registry/DB)
        enabled_providers = ProviderCatalog.query.filter_by(is_enabled=True).all()
        enabled_types = [p.provider_type for p in enabled_providers]
        # Known types from provider_resource_types
        known_map = {}
        rows = ProviderResourceType.query.filter(ProviderResourceType.enabled == True).all()
        for row in rows:
            known_map.setdefault(row.provider_type, set()).add(row.unified_type)

        for r in resource_rules:
            rule_rtypes = list(getattr(r, 'resource_types', []) or [])
            declared_providers = list(getattr(r, 'providers', None) or [])
            provider_list = declared_providers or enabled_types
            for p in provider_list:
                allowed_types = list(known_map.get(p, set()))
                rtypes = [rt for rt in rule_rtypes if (not allowed_types or rt in allowed_types)]
                for rt in rtypes:
                    resource_payload.append(rule_dict(r, 'resource', provider_type=p, resource_type=rt))
        return {'success': True, 'global': global_payload, 'resource': resource_payload}
    except Exception as e:
        return {'success': False, 'error': str(e)}

@admin_bp.route('/recommendations/rules', methods=['GET'])
def list_recommendation_rules():
    """List rule settings grouped for admin UI.

    Returns discovered rules and current enablement from DB. Missing rows are implied enabled=True by default.
    """
    admin_check = require_admin()
    if admin_check:
        return admin_check
    try:
        payload = _build_reco_rules_payload()
        return jsonify(payload)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# CRUD for Provider Resource Types
@admin_bp.route('/provider-types/<string:provider_type>/resource-types', methods=['GET'])
def list_provider_resource_types(provider_type: str):
    admin_check = require_admin()
    if admin_check:
        return admin_check
    rows = ProviderResourceType.query.filter_by(provider_type=provider_type).order_by(ProviderResourceType.unified_type.asc()).all()
    return jsonify({'success': True, 'items': [r.to_dict() for r in rows]})

@admin_bp.route('/provider-types/<string:provider_type>/resource-types', methods=['POST'])
def create_provider_resource_type(provider_type: str):
    admin_check = require_admin()
    if admin_check:
        return admin_check
    data = request.get_json(force=True) or {}
    item = ProviderResourceType(
        provider_type=provider_type,
        unified_type=(data.get('unified_type') or '').strip(),
        display_name=data.get('display_name'),
        icon=data.get('icon'),
        enabled=bool(data.get('enabled', True)),
        raw_aliases=data.get('raw_aliases')
    )
    db.session.add(item); db.session.commit()
    return jsonify({'success': True, 'item': item.to_dict()})

@admin_bp.route('/provider-types/resource-types/<int:item_id>', methods=['PUT'])
def update_provider_resource_type(item_id: int):
    admin_check = require_admin()
    if admin_check:
        return admin_check
    data = request.get_json(force=True) or {}
    item = ProviderResourceType.query.get_or_404(item_id)
    for f in ['unified_type','display_name','icon','raw_aliases']:
        if f in data:
            setattr(item, f, data[f])
    if 'enabled' in data:
        item.enabled = bool(data['enabled'])
    db.session.commit()
    return jsonify({'success': True, 'item': item.to_dict()})

@admin_bp.route('/provider-types/resource-types/<int:item_id>', methods=['DELETE'])
def delete_provider_resource_type(item_id: int):
    admin_check = require_admin()
    if admin_check:
        return admin_check
    item = ProviderResourceType.query.get_or_404(item_id)
    db.session.delete(item); db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/recommendations/rules', methods=['POST'])
def upsert_recommendation_rule():
    """Create/update a rule setting (enable/disable, description)."""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    try:
        data = request.get_json(force=True) or {}
        rule_id = (data.get('rule_id') or '').strip()
        scope = (data.get('scope') or '').strip()
        provider_type = (data.get('provider_type') or None)
        resource_type = (data.get('resource_type') or None)
        enabled = bool(data.get('enabled', True))
        description = data.get('description')

        if not rule_id or scope not in ('global', 'resource'):
            return jsonify({'success': False, 'error': 'rule_id and scope are required'}), 400

        existing = RecommendationRuleSetting.query.filter_by(
            rule_id=rule_id, scope=scope, provider_type=provider_type, resource_type=resource_type
        ).first()
        if existing is None:
            existing = RecommendationRuleSetting(
                rule_id=rule_id, scope=scope, provider_type=provider_type, resource_type=resource_type
            )
            db.session.add(existing)
        existing.enabled = enabled
        if description is not None:
            existing.description = description
        db.session.commit()
        return jsonify({'success': True, 'setting': existing.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/recommendations/providers/<string:provider_type>/resource-types', methods=['GET'])
def provider_resource_types(provider_type: str):
    """Return known (configured) and observed resource types for a provider.

    - known: from resource registry mappings (unified types)
    - observed: from current inventory (resources table) with counts
    """
    admin_check = require_admin()
    if admin_check:
        return admin_check
    try:
        # Known from curated DB inventory (provider_resource_types)
        rows = (
            ProviderResourceType.query
            .filter_by(provider_type=provider_type)
            .filter(ProviderResourceType.enabled == True)
            .order_by(ProviderResourceType.unified_type.asc())
            .all()
        )
        known = [r.unified_type for r in rows]

        # Observed from inventory
        rows = (
            db.session.query(Resource.resource_type, db.func.count(Resource.id))
            .join(CloudProvider, Resource.provider_id == CloudProvider.id)
            .filter(CloudProvider.provider_type == provider_type)
            .group_by(Resource.resource_type)
            .all()
        )
        observed = { rtype: int(count) for (rtype, count) in rows }

        effective = sorted(set(known) | set(observed.keys()))
        return jsonify({ 'success': True, 'provider': provider_type, 'known': known, 'observed': observed, 'effective': effective })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Provider Catalog Management

@admin_bp.route('/providers-page')
def providers_page():
    """Provider catalog management page"""
    admin_check = require_admin()
    if admin_check:
        return redirect(url_for('main.dashboard'))
    
    # Get current user from session
    user = session.get('user', {})
    return render_template('admin/providers.html', user=user)

@admin_bp.route('/providers')
def list_providers():
    """List all providers in catalog (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        providers = ProviderCatalog.query.order_by(ProviderCatalog.display_name).all()
        
        return jsonify({
            'success': True,
            'providers': [provider.to_dict() for provider in providers]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch providers: {str(e)}'
        })

@admin_bp.route('/providers/<int:provider_id>', methods=['PUT'])
def update_provider(provider_id):
    """Update provider settings (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        provider = ProviderCatalog.query.get_or_404(provider_id)
        data = request.get_json()
        
        # Update allowed fields
        if 'is_enabled' in data:
            provider.is_enabled = bool(data['is_enabled'])
        
        provider.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'provider': provider.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to update provider: {str(e)}'
        })

@admin_bp.route('/providers/<int:provider_id>/sync-prices', methods=['POST'])
def sync_provider_prices(provider_id):
    """Trigger price sync for a provider (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        provider = ProviderCatalog.query.get_or_404(provider_id)
        
        # Import price update service
        from app.core.services.price_update_service import PriceUpdateService
        price_update_service = PriceUpdateService()
        
        # Sync prices for this provider
        result = price_update_service.sync_provider_prices(provider.provider_type)
        
        if result['success']:
            # Refresh provider data from database
            db.session.refresh(provider)
            return jsonify({
                'success': True,
                'message': result['message'],
                'provider': provider.to_dict(),
                'records_synced': result.get('records_synced', 0)
            })
        else:
            # Refresh provider data to get updated sync status
            db.session.refresh(provider)
            return jsonify({
                'success': False,
                'error': result['error'],
                'provider': provider.to_dict()
            })
            
    except Exception as e:
        logger.error(f"Error in sync_provider_prices: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to sync prices: {str(e)}'
        })

@admin_bp.route('/providers/sync-all-prices', methods=['POST'])
def sync_all_provider_prices():
    """Trigger price sync for all enabled providers (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        # Import price update service
        from app.core.services.price_update_service import PriceUpdateService
        price_update_service = PriceUpdateService()
        
        # Sync prices for all enabled providers
        result = price_update_service.sync_all_enabled_providers()
        
        return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error in sync_all_provider_prices: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to sync all prices: {str(e)}'
        })

@admin_bp.route('/pricing/statistics', methods=['GET'])
def get_pricing_statistics():
    """Get pricing system statistics (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        from app.core.services.price_update_service import PriceUpdateService
        price_update_service = PriceUpdateService()
        
        statistics = price_update_service.get_pricing_statistics()
        
        return jsonify({
            'success': True,
            'statistics': statistics
        })
            
    except Exception as e:
        logger.error(f"Error getting pricing statistics: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get pricing statistics: {str(e)}'
        })

@admin_bp.route('/providers/<int:provider_id>/pricing', methods=['GET'])
def get_provider_pricing(provider_id):
    """Get pricing data for a specific provider (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        provider = ProviderCatalog.query.get_or_404(provider_id)
        
        # Import pricing service
        from app.core.services.pricing_service import PricingService
        pricing_service = PricingService()
        
        # Get pricing data for this provider
        pricing_data = pricing_service.get_prices_by_provider(provider.provider_type)
        
        # Convert to dict format for JSON response
        pricing_list = [price.to_dict() for price in pricing_data]
        
        return jsonify({
            'success': True,
            'pricing': pricing_list,
            'provider': provider.to_dict(),
            'total_records': len(pricing_list)
        })
            
    except Exception as e:
        logger.error(f"Error getting provider pricing: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get pricing data: {str(e)}'
        })

# ==========================================
# Provider Admin Credentials Management
# ==========================================

@admin_bp.route('/providers/<string:provider_type>/credentials', methods=['GET'])
def get_provider_credentials(provider_type):
    """Get admin credentials for a provider (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        credentials = ProviderAdminCredentials.query.filter_by(provider_type=provider_type).first()
        
        if not credentials:
            return jsonify({
                'success': True,
                'credentials': None,
                'message': 'No credentials configured for this provider'
            })
        
        return jsonify({
            'success': True,
            'credentials': credentials.to_dict(include_credentials=True)
        })
            
    except Exception as e:
        logger.error(f"Error getting provider credentials: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get credentials: {str(e)}'
        })

@admin_bp.route('/providers/<string:provider_type>/credentials', methods=['POST'])
def create_provider_credentials(provider_type):
    """Create or update admin credentials for a provider (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})
        
        # Check if credentials already exist
        credentials = ProviderAdminCredentials.query.filter_by(provider_type=provider_type).first()
        
        if credentials:
            # Update existing credentials
            credentials.credential_type = data.get('credential_type', credentials.credential_type)
            credentials.description = data.get('description', credentials.description)
            credentials.is_active = data.get('is_active', credentials.is_active)
            credentials.config_data = data.get('config_data', credentials.config_data)
            
            # Update credentials if provided
            if 'credentials' in data:
                credentials.set_credentials(data['credentials'])
            
            # Update expiration if provided
            if 'expires_at' in data and data['expires_at']:
                credentials.expires_at = datetime.fromisoformat(data['expires_at'])
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Credentials updated successfully',
                'credentials': credentials.to_dict(include_credentials=False)
            })
        else:
            # Create new credentials
            if 'credential_type' not in data or 'credentials' not in data:
                return jsonify({
                    'success': False,
                    'error': 'credential_type and credentials are required'
                })
            
            credentials = ProviderAdminCredentials(
                provider_type=provider_type,
                credential_type=data['credential_type'],
                description=data.get('description', ''),
                is_active=data.get('is_active', True),
                config_data=data.get('config_data', {})
            )
            
            # Set encrypted credentials
            credentials.set_credentials(data['credentials'])
            
            # Set expiration if provided
            if 'expires_at' in data and data['expires_at']:
                credentials.expires_at = datetime.fromisoformat(data['expires_at'])
            
            db.session.add(credentials)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Credentials created successfully',
                'credentials': credentials.to_dict(include_credentials=False)
            })
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating provider credentials: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to create credentials: {str(e)}'
        })

@admin_bp.route('/providers/<string:provider_type>/credentials', methods=['DELETE'])
def delete_provider_credentials(provider_type):
    """Delete admin credentials for a provider (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        credentials = ProviderAdminCredentials.query.filter_by(provider_type=provider_type).first()
        
        if not credentials:
            return jsonify({
                'success': False,
                'error': 'No credentials found for this provider'
            })
        
        db.session.delete(credentials)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Credentials deleted successfully'
        })
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting provider credentials: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to delete credentials: {str(e)}'
        })

@admin_bp.route('/providers/<string:provider_type>/credentials/test', methods=['POST'])
def test_provider_credentials(provider_type):
    """Test admin credentials for a provider (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        credentials = ProviderAdminCredentials.query.filter_by(provider_type=provider_type).first()
        
        if not credentials:
            return jsonify({
                'success': False,
                'error': 'No credentials found for this provider'
            })
        
        # Mark as used
        credentials.mark_used()
        db.session.commit()
        
        # Test credentials based on provider type
        test_result = _test_credentials_by_provider(provider_type, credentials.get_credentials())
        
        return jsonify(test_result)
            
    except Exception as e:
        logger.error(f"Error testing provider credentials: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to test credentials: {str(e)}'
        })

@admin_bp.route('/providers/<string:provider_type>/credentials/test-raw', methods=['POST'])
def test_provider_credentials_raw(provider_type):
    """Test raw credentials without saving them (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No credentials provided'})
        
        # Extract credentials from request
        if provider_type == 'yandex':
            service_account_key = data.get('service_account_key')
            if not service_account_key:
                return jsonify({'success': False, 'error': 'Service Account JSON is required'})
            
            # Parse JSON to validate format
            try:
                import json
                parsed_key = json.loads(service_account_key)
                credentials = {'service_account_key': parsed_key}
            except json.JSONDecodeError as e:
                return jsonify({'success': False, 'error': f'Invalid JSON format: {str(e)}'})
        
        elif provider_type == 'selectel':
            api_key = data.get('api_key')
            service_username = data.get('service_username')
            service_password = data.get('service_password')
            
            if not all([api_key, service_username, service_password]):
                return jsonify({'success': False, 'error': 'API Key, Service Username, and Service Password are required'})
            
            credentials = {
                'api_key': api_key,
                'service_username': service_username,
                'service_password': service_password
            }
        
        elif provider_type == 'beget':
            username = data.get('username')
            password = data.get('password')
            
            if not all([username, password]):
                return jsonify({'success': False, 'error': 'Username and password are required'})
            
            credentials = {
                'username': username,
                'password': password
            }
        
        else:
            return jsonify({'success': False, 'error': f'Unsupported provider type: {provider_type}'})
        
        # Test credentials based on provider type
        test_result = _test_credentials_by_provider(provider_type, credentials)
        
        return jsonify(test_result)
            
    except Exception as e:
        logger.error(f"Error testing raw credentials: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to test credentials: {str(e)}'
        })

def _test_credentials_by_provider(provider_type: str, creds: dict) -> dict:
    """Test credentials by provider type"""
    try:
        if provider_type == 'yandex':
            from app.providers.yandex.client import YandexClient
            
            # Test if we can create client and fetch SKUs
            client = YandexClient(creds)
            result = client.list_skus(page_size=1)
            
            if result and 'skus' in result:
                return {
                    'success': True,
                    'message': 'Успешно! Доступ к Yandex Cloud Billing API подтверждён',
                    'tested_at': datetime.utcnow().isoformat(),
                    'details': f'Доступ к SKU каталогу: {len(result.get("skus", []))} SKU получено'
                }
            else:
                return {
                    'success': False,
                    'error': 'Не удалось получить доступ к SKU каталогу. Проверьте права Service Account.'
                }
        
        elif provider_type == 'selectel':
            from app.providers.selectel.client import SelectelClient
            
            client = SelectelClient(creds)
            test_result = client.test_connection()
            
            if test_result.get('success'):
                return {
                    'success': True,
                    'message': 'Успешно! Подключение к Selectel подтверждено',
                    'tested_at': datetime.utcnow().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': test_result.get('message', 'Ошибка подключения к Selectel')
                }
        
        elif provider_type == 'beget':
            from app.providers.beget.client import BegetAPIClient
            
            username = creds.get('username')
            password = creds.get('password')
            
            if not username or not password:
                return {
                    'success': False,
                    'error': 'Отсутствуют username или password'
                }
            
            client = BegetAPIClient(username, password)
            if client.authenticate():
                return {
                    'success': True,
                    'message': 'Успешно! Аутентификация Beget прошла успешно',
                    'tested_at': datetime.utcnow().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': 'Неверные учетные данные Beget'
                }
        
        else:
            return {
                'success': False,
                'error': f'Тестирование для провайдера {provider_type} еще не реализовано'
            }
    
    except Exception as e:
        logger.error(f"Error testing {provider_type} credentials: {str(e)}")
        return {
            'success': False,
            'error': f'Ошибка тестирования: {str(e)}'
        }

@admin_bp.route('/reseed-demo-user', methods=['POST'])
def reseed_demo_user():
    """
    Reseed demo user with fresh mock data including 3-month historical data
    This endpoint deletes all demo user data and recreates it with comprehensive history
    Admin only
    """
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        logger.info("Admin initiated demo user reseed with historical data")
        
        # Import the seeding functions
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'scripts'))
        from seed_demo_user import seed_demo_user, seed_historical_complete_syncs, seed_usage_data_tags, seed_business_context
        
        # Call the comprehensive seeding function (base data + historical data)
        demo_user, providers_dict = seed_demo_user()
        
        # Generate 90 days of historical complete sync data
        seed_historical_complete_syncs(demo_user, providers_dict)
        
        # Generate usage data tags for all server resources
        seed_usage_data_tags(demo_user, providers_dict)
        
        # Create business context boards
        try:
            seed_business_context(demo_user, providers_dict)
        except Exception as bc_error:
            logger.warning(f"Business Context seeding failed: {bc_error}", exc_info=True)

        # Compute fresh counts for response
        provider_count = CloudProvider.query.filter_by(user_id=demo_user.id).count()
        resource_count = (
            Resource.query.join(CloudProvider, Resource.provider_id == CloudProvider.id)
            .filter(CloudProvider.user_id == demo_user.id)
            .count()
        )
        
        # Get complete sync count
        from app.core.models.complete_sync import CompleteSync
        complete_sync_count = CompleteSync.query.filter_by(user_id=demo_user.id).count()
        
        # Get business context counts
        from app.core.models.business_board import BusinessBoard
        from app.core.models.board_group import BoardGroup
        from app.core.models.board_resource import BoardResource
        
        boards_count = BusinessBoard.query.filter_by(user_id=demo_user.id).count()
        groups_count = BoardGroup.query.join(BusinessBoard).filter(BusinessBoard.user_id == demo_user.id).count()
        board_resources_count = BoardResource.query.join(BusinessBoard).filter(BusinessBoard.user_id == demo_user.id).count()
        
        return jsonify({
            'success': True,
            'message': 'Demo user successfully reseeded with 3-month historical data, usage analytics, and business context boards',
            'demo_user': {
                'id': demo_user.id,
                'email': demo_user.email,
                'providers': provider_count,
                'resources': resource_count,
                'complete_syncs': complete_sync_count,
                'boards': boards_count,
                'groups': groups_count,
                'board_resources': board_resources_count
            }
        })
        
    except Exception as e:
        logger.error(f"Error reseeding demo user: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Failed to reseed demo user: {str(e)}'
        }), 500

@admin_bp.route('/bulk-sync-all-users', methods=['POST'])
def bulk_sync_all_users():
    """Trigger bulk sync for all active users (admin only)"""
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        from app.core.services.bulk_sync_service import BulkSyncService
        
        # Get sync type from request (default: manual when triggered from admin)
        sync_type = request.json.get('sync_type', 'manual') if request.is_json else 'manual'
        
        logger.info(f"Admin initiated bulk sync for all users (sync_type: {sync_type})")
        
        # Create bulk sync service
        bulk_sync_service = BulkSyncService()
        
        # Execute bulk sync
        result = bulk_sync_service.sync_all_users(sync_type=sync_type)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': result.get('message'),
                'total_users': result.get('total_users'),
                'successful_users': result.get('successful_users'),
                'failed_users': result.get('failed_users'),
                'skipped_users': result.get('skipped_users'),
                'duration_seconds': result.get('duration_seconds'),
                'user_results': result.get('user_results', [])
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error'),
                'message': result.get('message', 'Bulk sync failed')
            }), 500
        
    except Exception as e:
        logger.error(f"Error during bulk sync: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Failed to execute bulk sync: {str(e)}'
        }), 500
