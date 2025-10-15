"""
Admin API routes for user management and impersonation
"""
from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify, flash
from datetime import datetime
import logging
from app.core.database import db
from app.core.models.user import User
from app.core.models.unrecognized_resource import UnrecognizedResource
from app.core.models.provider_catalog import ProviderCatalog
from app.core.models.provider_admin_credentials import ProviderAdminCredentials
from app.api.auth import validate_session

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
        
        query = User.query
        
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

@admin_bp.route('/unrecognized-resources-page')
def unrecognized_resources_page():
    """Unrecognized resources management page"""
    admin_check = require_admin()
    if admin_check:
        return redirect(url_for('main.dashboard'))
    
    # Get current user from session
    user = session.get('user', {})
    return render_template('admin/unrecognized_resources.html', user=user)

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
        
        # TODO: Implement actual credential testing based on provider type
        # For now, just return success
        return jsonify({
            'success': True,
            'message': 'Credentials test successful (placeholder)',
            'tested_at': datetime.utcnow().isoformat()
        })
            
    except Exception as e:
        logger.error(f"Error testing provider credentials: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to test credentials: {str(e)}'
        })

@admin_bp.route('/reseed-demo-user', methods=['POST'])
def reseed_demo_user():
    """
    Reseed demo user with fresh mock data
    This endpoint deletes all demo user data and recreates it
    Admin only
    """
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    try:
        logger.info("Admin initiated demo user reseed")
        
        # Import the seeding function
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'scripts'))
        from seed_demo_user import seed_demo_user
        
        # Call the seeding function
        demo_user = seed_demo_user()
        
        return jsonify({
            'success': True,
            'message': 'Demo user successfully reseeded',
            'demo_user': {
                'id': demo_user.id,
                'email': demo_user.email,
                'providers': 2,
                'resources': 7
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
