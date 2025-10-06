"""
Admin API routes for user management and impersonation
"""
from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify, flash
from datetime import datetime
from app.core.database import db
from app.core.models.user import User

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
            user.is_active = data['is_active']
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
        
        # Set username from email
        user.username = user.email.split('@')[0]
        
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
