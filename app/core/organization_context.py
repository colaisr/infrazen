"""
Organization context helper for managing current organization in session
"""
from flask import session
from app.core.models import db
from app.core.models.organization import Organization
from app.core.models.organization_member import OrganizationMember
from app.core.models.user import User


def get_current_organization_id():
    """
    Get the current active organization ID from session.
    Returns None if not set.
    """
    user_data = session.get('user', {})
    return user_data.get('current_organization_id')


def set_current_organization_id(organization_id, user_id=None):
    """
    Set the current active organization ID in session.
    Also updates user's last_active_organization_id in database.
    
    Args:
        organization_id: The organization ID to set as current
        user_id: Optional user ID (will be extracted from session if not provided)
    """
    user_data = session.get('user', {})
    user_data['current_organization_id'] = organization_id
    session['user'] = user_data
    session.permanent = True  # Make session permanent
    session.modified = True  # Mark session as modified to ensure it's saved
    
    # Force session to be saved immediately
    try:
        from flask import current_app
        current_app.logger.debug(f"Set current_organization_id to {organization_id} for user {user_id}")
    except:
        pass
    
    # Update user's last_active_organization_id in database
    if user_id is None:
        user_id = user_data.get('db_id') or user_data.get('id')
    
    if user_id:
        try:
            # Convert user_id to int if needed
            try:
                user_id = int(user_id) if isinstance(user_id, (str, float)) else user_id
            except (ValueError, TypeError):
                pass
            
            user = User.query.get(user_id)
            if user:
                user.last_active_organization_id = organization_id
                db.session.commit()
        except Exception:
            # Don't fail if database update fails
            db.session.rollback()
            pass


def get_current_organization():
    """
    Get the current active Organization object.
    Returns None if not set or organization doesn't exist.
    """
    org_id = get_current_organization_id()
    if not org_id:
        return None
    
    try:
        return Organization.query.get(org_id)
    except Exception:
        return None


def require_organization_access(organization_id, user_id=None):
    """
    Check if user has access to an organization.
    Raises PermissionError if user doesn't have access.
    
    Args:
        organization_id: The organization ID to check access for
        user_id: Optional user ID (will be extracted from session if not provided)
    
    Returns:
        OrganizationMember object if user has access
    
    Raises:
        PermissionError: If user doesn't have access to the organization
    """
    if user_id is None:
        user_data = session.get('user', {})
        user_id = user_data.get('db_id') or user_data.get('id')
    
    if not user_id:
        raise PermissionError("User not authenticated")
    
    # Convert user_id to int if it's a string
    try:
        user_id = int(user_id) if isinstance(user_id, (str, float)) else user_id
    except (ValueError, TypeError):
        raise PermissionError("Invalid user ID")
    
    member = OrganizationMember.query.filter_by(
        organization_id=organization_id,
        user_id=user_id,
        is_active=True
    ).first()
    
    if not member:
        raise PermissionError(f"User {user_id} does not have access to organization {organization_id}")
    
    return member


def filter_by_organization(query, organization_id=None):
    """
    Filter a query by organization_id.
    If organization_id is None, uses current organization from session.
    
    Args:
        query: SQLAlchemy query object
        organization_id: Optional organization ID (uses current if not provided)
    
    Returns:
        Filtered query
    """
    if organization_id is None:
        organization_id = get_current_organization_id()
    
    if organization_id is None:
        # If no organization context, return empty query
        # This prevents data leakage
        return query.filter(False)
    
    # Get the model class from the query
    model_class = query.column_descriptions[0]['entity'] if query.column_descriptions else None
    
    if model_class and hasattr(model_class, 'organization_id'):
        return query.filter(model_class.organization_id == organization_id)
    
    return query


def get_user_organizations(user_id=None):
    """
    Get all organizations a user belongs to.
    
    Args:
        user_id: Optional user ID (will be extracted from session if not provided)
    
    Returns:
        List of Organization objects
    """
    if user_id is None:
        user_data = session.get('user', {})
        user_id = user_data.get('db_id') or user_data.get('id')
    
    if not user_id:
        return []
    
    return Organization.get_user_organizations(user_id)


def initialize_user_organization_context(user_id):
    """
    Initialize organization context for a user on login.
    Sets current_organization_id to user's last_active_organization_id
    or their personal organization if no last_active is set.
    Creates personal organization if user doesn't have one.
    
    Args:
        user_id: User ID to initialize context for
    
    Returns:
        The organization ID that was set
    """
    user = User.query.get(user_id)
    if not user:
        return None
    
    # Try to use last_active_organization_id
    org_id = user.last_active_organization_id
    
    # If no last_active, use personal organization
    if not org_id:
        personal_org = user.get_personal_organization()
        if personal_org:
            org_id = personal_org.id
    
    # If still no org, create personal organization for user
    if not org_id:
        from datetime import datetime
        org_name = f"{user.first_name or 'User'} {user.last_name or ''}".strip() or f"Personal ({user.email})"
        personal_org = Organization(name=org_name)
        db.session.add(personal_org)
        db.session.flush()
        
        # Create organization member (user as owner)
        member = OrganizationMember(
            organization_id=personal_org.id,
            user_id=user.id,
            role='owner',
            joined_at=datetime.utcnow(),
            is_active=True
        )
        db.session.add(member)
        
        # Set as default organization
        user.default_organization_id = personal_org.id
        user.last_active_organization_id = personal_org.id
        
        db.session.commit()
        org_id = personal_org.id
    
    if org_id:
        set_current_organization_id(org_id, user_id)
        
        # Update session with organization list
        user_data = session.get('user', {})
        orgs = get_user_organizations(user_id)
        user_data['organizations'] = [
            {
                'id': org.id,
                'name': org.name,
                'role': org.get_user_role(user_id) or 'viewer'
            }
            for org in orgs
        ]
        session['user'] = user_data
    
    return org_id


def can_user_access_organization(user_id, organization_id):
    """
    Check if a user can access an organization.
    
    Args:
        user_id: User ID
        organization_id: Organization ID
    
    Returns:
        True if user has access, False otherwise
    """
    try:
        require_organization_access(organization_id, user_id)
        return True
    except PermissionError:
        return False


def get_user_role_in_organization(user_id, organization_id):
    """
    Get user's role in an organization.
    
    Args:
        user_id: User ID
        organization_id: Organization ID
    
    Returns:
        Role string ('owner', 'editor', 'viewer') or None if not a member
    """
    member = OrganizationMember.query.filter_by(
        organization_id=organization_id,
        user_id=user_id,
        is_active=True
    ).first()
    
    return member.role if member else None

