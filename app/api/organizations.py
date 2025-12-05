"""
Organization API endpoints for multi-tenant support
"""
from flask import Blueprint, request, jsonify, session
from flask_login import login_required
from sqlalchemy import func
from app.core.models import db
from app.core.models.user import User
from app.core.models.organization import Organization
from app.core.models.organization_member import OrganizationMember
from app.core.models.organization_invitation import OrganizationInvitation
from app.core.organization_context import (
    get_current_organization_id,
    set_current_organization_id,
    require_organization_access,
    get_user_organizations,
    get_user_role_in_organization,
    can_user_access_organization
)
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

organizations_bp = Blueprint('organizations', __name__)


def get_current_user_id():
    """Get current user ID from session"""
    user_data = session.get('user', {})
    user_id = user_data.get('db_id') or user_data.get('id')
    # Convert to int if it's a string or float
    if user_id:
        try:
            return int(user_id) if isinstance(user_id, (str, float)) else user_id
        except (ValueError, TypeError):
            return None
    return None


def require_owner(organization_id, user_id=None):
    """Require user to be owner of organization"""
    if user_id is None:
        user_id = get_current_user_id()
    
    member = require_organization_access(organization_id, user_id)
    if member.role != 'owner':
        raise PermissionError("Only organization owners can perform this action")
    return member


def require_owner_or_editor(organization_id, user_id=None):
    """Require user to be owner or editor of organization"""
    if user_id is None:
        user_id = get_current_user_id()
    
    member = require_organization_access(organization_id, user_id)
    if member.role not in ['owner', 'editor']:
        raise PermissionError("Only organization owners and editors can perform this action")
    return member


@organizations_bp.route('/organizations', methods=['GET'])
@login_required
def list_organizations():
    """List all organizations the current user belongs to"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        orgs = get_user_organizations(user_id)
        current_org_id = get_current_organization_id()
        
        organizations_data = []
        for org in orgs:
            role = get_user_role_in_organization(user_id, org.id)
            organizations_data.append({
                'id': org.id,
                'name': org.name,
                'role': role,
                'member_count': org.members.filter_by(is_active=True).count(),
                'is_personal': org.get_user_role(user_id) == 'owner' and org.members.filter_by(is_active=True).count() == 1,
                'is_current': org.id == current_org_id,
                'created_at': org.created_at.isoformat() if org.created_at else None
            })
        
        return jsonify({
            'success': True,
            'organizations': organizations_data,
            'current_organization_id': current_org_id
        })
    
    except Exception as e:
        logger.error(f"Error listing organizations: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Note: Organization creation is disabled - users get one personal organization automatically
# Organizations can only be created by inviting users (which creates the org for the inviter if needed)
@organizations_bp.route('/organizations', methods=['POST'])
@login_required
def create_organization():
    """Create a new organization - DISABLED: Users can only have one personal organization"""
    return jsonify({
        'success': False,
        'error': 'Organization creation is not available. Each user has one personal organization that is created automatically.'
    }), 403


@organizations_bp.route('/organizations/<int:org_id>', methods=['GET'])
@login_required
def get_organization(org_id):
    """Get organization details"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        # Check access
        member = require_organization_access(org_id, user_id)
        org = Organization.query.get(org_id)
        
        if not org:
            return jsonify({'success': False, 'error': 'Organization not found'}), 404
        
        # Get members
        members = OrganizationMember.query.filter_by(
            organization_id=org_id,
            is_active=True
        ).all()
        members_data = []
        for m in members:
            members_data.append({
                'id': m.id,
                'user_id': m.user_id,
                'email': m.user.email if m.user else None,
                'name': f"{m.user.first_name or ''} {m.user.last_name or ''}".strip() if m.user else None,
                'picture': m.user.google_picture if m.user else None,
                'role': m.role,
                'joined_at': m.joined_at.isoformat() if m.joined_at else None,
                'is_owner': m.role == 'owner'
            })
        
        return jsonify({
            'success': True,
            'organization': {
                'id': org.id,
                'name': org.name,
                'role': member.role,
                'members': members_data,
                'member_count': len(members_data),
                'created_at': org.created_at.isoformat() if org.created_at else None
            }
        })
    
    except PermissionError as e:
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        logger.error(f"Error getting organization: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@organizations_bp.route('/organizations/<int:org_id>', methods=['PUT'])
@login_required
def update_organization(org_id):
    """Update organization (only owner can update)"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        # Require owner
        require_owner(org_id, user_id)
        
        org = Organization.query.get(org_id)
        if not org:
            return jsonify({'success': False, 'error': 'Organization not found'}), 404
        
        data = request.get_json()
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'success': False, 'error': 'Organization name is required'}), 400
        
        org.name = name
        db.session.commit()
        
        return jsonify({
            'success': True,
            'organization': {
                'id': org.id,
                'name': org.name,
                'updated_at': org.updated_at.isoformat() if org.updated_at else None
            }
        })
    
    except PermissionError as e:
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating organization: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@organizations_bp.route('/organizations/<int:org_id>/switch', methods=['POST'])
@login_required
def switch_organization(org_id):
    """Switch active organization"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        # Check access
        require_organization_access(org_id, user_id)
        
        # Switch organization
        set_current_organization_id(org_id, user_id)
        
        # Ensure session is saved (Flask sessions are saved automatically, but mark as modified to be safe)
        session.permanent = True
        session.modified = True
        
        # Force session save by accessing it
        _ = session.get('user')
        
        org = Organization.query.get(org_id)
        role = get_user_role_in_organization(user_id, org_id)
        
        return jsonify({
            'success': True,
            'organization': {
                'id': org.id,
                'name': org.name,
                'role': role
            },
            'message': 'Organization switched successfully',
            'current_organization_id': org_id
        })
    
    except PermissionError as e:
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        logger.error(f"Error switching organization: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@organizations_bp.route('/organizations/current', methods=['GET'])
@login_required
def get_current_organization():
    """Get current active organization"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        org_id = get_current_organization_id()
        if not org_id:
            return jsonify({'success': False, 'error': 'No active organization'}), 404
        
        org = Organization.query.get(org_id)
        if not org:
            return jsonify({'success': False, 'error': 'Organization not found'}), 404
        
        role = get_user_role_in_organization(user_id, org_id)
        
        return jsonify({
            'success': True,
            'organization': {
                'id': org.id,
                'name': org.name,
                'role': role
            }
        })
    
    except Exception as e:
        logger.error(f"Error getting current organization: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@organizations_bp.route('/organizations/<int:org_id>/members', methods=['GET'])
@login_required
def list_members(org_id):
    """List organization members"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        # Check access
        require_organization_access(org_id, user_id)
        
        members = OrganizationMember.get_organization_members(org_id)
        members_data = []
        for m in members:
            members_data.append({
                'id': m.id,
                'user_id': m.user_id,
                'email': m.user.email if m.user else None,
                'name': f"{m.user.first_name or ''} {m.user.last_name or ''}".strip() if m.user else None,
                'picture': m.user.google_picture if m.user else None,
                'role': m.role,
                'joined_at': m.joined_at.isoformat() if m.joined_at else None,
                'invited_by': m.inviter.email if m.inviter else None,
                'is_owner': m.role == 'owner',
                'is_current_user': m.user_id == user_id
            })
        
        return jsonify({
            'success': True,
            'members': members_data
        })
    
    except PermissionError as e:
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        logger.error(f"Error listing members: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@organizations_bp.route('/organizations/<int:org_id>/members', methods=['POST'])
@login_required
def invite_member(org_id):
    """Invite a user to the organization (supports both registered and unregistered users)"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        # Only owner can invite
        require_owner(org_id, user_id)
        
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        role = data.get('role', 'viewer')
        
        if not email:
            return jsonify({'success': False, 'error': 'Email is required'}), 400
        
        if role not in ['viewer', 'editor']:
            return jsonify({'success': False, 'error': 'Invalid role. Must be viewer or editor'}), 400
        
        # Get organization
        organization = Organization.query.get(org_id)
        if not organization:
            return jsonify({'success': False, 'error': 'Organization not found'}), 404
        
        # Find user by email (case-insensitive)
        user = User.query.filter(func.lower(User.email) == email.lower()).first()
        
        if user:
            # User exists - add them immediately
            # Check if user is already a member
            existing_member = OrganizationMember.query.filter_by(
                organization_id=org_id,
                user_id=user.id,
                is_active=True
            ).first()
            
            if existing_member:
                # Idempotent - silently ignore if already a member
                return jsonify({
                    'success': True,
                    'message': 'User is already a member',
                    'member': {
                        'id': existing_member.id,
                        'user_id': user.id,
                        'email': user.email,
                        'role': existing_member.role
                    }
                })
            
            # Add user to organization automatically
            member = OrganizationMember(
                organization_id=org_id,
                user_id=user.id,
                role=role,
                invited_by_user_id=user_id,
                invited_at=datetime.utcnow(),
                joined_at=datetime.utcnow(),
                is_active=True
            )
            db.session.add(member)
            
            # Create invitation record for audit trail
            invitation = OrganizationInvitation(
                organization_id=org_id,
                email=email,
                role=role,
                invited_by_user_id=user_id,
                status='accepted',
                accepted_at=datetime.utcnow()
            )
            db.session.add(invitation)
            
            db.session.commit()
            
            # Send email notification to existing user
            try:
                from app.core.services.email_service import EmailService
                inviter = User.query.get(user_id)
                inviter_name = f"{inviter.first_name or ''} {inviter.last_name or ''}".strip() or inviter.email.split('@')[0]
                EmailService.send_organization_invitation_accepted(
                    to_email=email,
                    username=f"{user.first_name or ''} {user.last_name or ''}".strip() or email.split('@')[0],
                    organization_name=organization.name,
                    inviter_name=inviter_name,
                    role=role
                )
            except Exception as e:
                logger.warning(f"Failed to send invitation email to existing user: {str(e)}")
            
            return jsonify({
                'success': True,
                'message': f'User {email} has been added to the organization',
                'member': {
                    'id': member.id,
                    'user_id': user.id,
                    'email': user.email,
                    'name': f"{user.first_name or ''} {user.last_name or ''}".strip(),
                    'role': role,
                    'joined_at': member.joined_at.isoformat() if member.joined_at else None
                }
            }), 201
        else:
            # User doesn't exist - create pending invitation
            # Check if there's already a pending invitation for this email
            existing_invitation = OrganizationInvitation.find_pending_by_email(email)
            if existing_invitation and existing_invitation.organization_id == org_id:
                return jsonify({
                    'success': True,
                    'message': f'Invitation already sent to {email}',
                    'pending': True
                })
            
            # Create pending invitation with token
            invitation = OrganizationInvitation(
                organization_id=org_id,
                email=email,
                role=role,
                invited_by_user_id=user_id,
                status='sent'
            )
            db.session.add(invitation)
            db.session.flush()  # Flush to get invitation ID
            
            # Generate invitation token
            token = invitation.generate_invitation_token()
            
            db.session.commit()
            
            # Send invitation email with registration link
            try:
                from app.core.services.email_service import EmailService
                inviter = User.query.get(user_id)
                inviter_name = f"{inviter.first_name or ''} {inviter.last_name or ''}".strip() or inviter.email.split('@')[0]
                registration_link = f"{request.url_root}register?invitation={token}"
                EmailService.send_organization_invitation(
                    to_email=email,
                    organization_name=organization.name,
                    inviter_name=inviter_name,
                    role=role,
                    registration_link=registration_link
                )
            except Exception as e:
                logger.error(f"Failed to send invitation email: {str(e)}")
                # Don't fail the invitation if email fails
            
            return jsonify({
                'success': True,
                'message': f'Invitation sent to {email}. They will be added to the organization when they register.',
                'pending': True
            }), 201
    
    except PermissionError as e:
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error inviting member: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@organizations_bp.route('/organizations/<int:org_id>/members/<int:member_user_id>', methods=['PUT'])
@login_required
def update_member_role(org_id, member_user_id):
    """Update member role (only owner can change roles)"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        # Only owner can change roles
        require_owner(org_id, user_id)
        
        data = request.get_json()
        new_role = data.get('role', '').strip()
        
        if new_role not in ['viewer', 'editor']:
            return jsonify({'success': False, 'error': 'Invalid role. Must be viewer or editor'}), 400
        
        # Cannot change owner role
        if member_user_id == user_id:
            return jsonify({'success': False, 'error': 'Cannot change your own role'}), 400
        
        member = OrganizationMember.query.filter_by(
            organization_id=org_id,
            user_id=member_user_id,
            is_active=True
        ).first()
        
        if not member:
            return jsonify({'success': False, 'error': 'Member not found'}), 404
        
        # Cannot change owner's role
        if member.role == 'owner':
            return jsonify({'success': False, 'error': 'Cannot change owner role'}), 400
        
        member.role = new_role
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Member role updated to {new_role}',
            'member': {
                'id': member.id,
                'user_id': member.user_id,
                'role': member.role
            }
        })
    
    except PermissionError as e:
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating member role: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@organizations_bp.route('/organizations/<int:org_id>/members/<int:member_user_id>', methods=['DELETE'])
@login_required
def remove_member(org_id, member_user_id):
    """Remove member from organization (owner can remove anyone, editor can remove non-owners)"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        # Check current user's role
        current_member = require_organization_access(org_id, user_id)
        
        # Get member to remove
        member = OrganizationMember.query.filter_by(
            organization_id=org_id,
            user_id=member_user_id,
            is_active=True
        ).first()
        
        if not member:
            return jsonify({'success': False, 'error': 'Member not found'}), 404
        
        # Owner cannot be removed
        if member.role == 'owner':
            return jsonify({'success': False, 'error': 'Cannot remove organization owner'}), 400
        
        # Only owner can remove members (editors cannot remove)
        if current_member.role != 'owner':
            return jsonify({'success': False, 'error': 'Only organization owners can remove members'}), 403
        
        # Soft delete (set is_active=False)
        member.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Member removed from organization'
        })
    
    except PermissionError as e:
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing member: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@organizations_bp.route('/organizations/<int:org_id>/invitations', methods=['GET'])
@login_required
def list_invitations(org_id):
    """List invitation history for organization"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        # Only owner can view invitations
        require_owner(org_id, user_id)
        
        invitations = OrganizationInvitation.query.filter_by(organization_id=org_id).order_by(OrganizationInvitation.created_at.desc()).all()
        invitations_data = []
        for inv in invitations:
            invitations_data.append({
                'id': inv.id,
                'email': inv.email,
                'role': inv.role,
                'status': inv.status,
                'invited_by': inv.invited_by.email if inv.invited_by else None,
                'created_at': inv.created_at.isoformat() if inv.created_at else None,
                'accepted_at': inv.accepted_at.isoformat() if inv.accepted_at else None,
                'revoked_at': inv.revoked_at.isoformat() if inv.revoked_at else None
            })
        
        return jsonify({
            'success': True,
            'invitations': invitations_data
        })
    
    except PermissionError as e:
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        logger.error(f"Error listing invitations: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@organizations_bp.route('/organizations/<int:org_id>/invitations/<int:invitation_id>/revoke', methods=['POST'])
@login_required
def revoke_invitation(org_id, invitation_id):
    """Revoke an invitation (only owner can revoke)"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        # Only owner can revoke invitations
        require_owner(org_id, user_id)
        
        invitation = OrganizationInvitation.query.filter_by(
            id=invitation_id,
            organization_id=org_id
        ).first()
        
        if not invitation:
            return jsonify({'success': False, 'error': 'Invitation not found'}), 404
        
        if invitation.status != 'sent':
            return jsonify({'success': False, 'error': 'Can only revoke pending invitations'}), 400
        
        invitation.status = 'revoked'
        invitation.revoked_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Invitation revoked successfully'
        })
    
    except PermissionError as e:
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error revoking invitation: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

