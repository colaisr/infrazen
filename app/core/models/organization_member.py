"""
OrganizationMember model for user-organization relationships
"""
from app.core.models import db
from .base import BaseModel


class OrganizationMember(BaseModel):
    """Model for user-organization membership with roles"""
    __tablename__ = 'organization_members'
    
    # Valid roles
    VALID_ROLES = ['viewer', 'editor', 'owner']
    
    # Relationships
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Role and membership
    role = db.Column(db.String(20), nullable=False, default='viewer', index=True)  # viewer, editor, owner
    
    # Invitation tracking
    invited_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    invited_at = db.Column(db.DateTime, nullable=True)
    joined_at = db.Column(db.DateTime, nullable=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='organization_memberships')
    inviter = db.relationship('User', foreign_keys=[invited_by_user_id])
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('organization_id', 'user_id', name='unique_org_user'),
    )
    
    def to_dict(self, include_user=False):
        """Convert member to dictionary"""
        data = {
            'id': self.id,
            'organization_id': self.organization_id,
            'user_id': self.user_id,
            'role': self.role,
            'is_active': self.is_active,
            'invited_at': self.invited_at.isoformat() if self.invited_at else None,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_user and self.user:
            data['user'] = {
                'id': self.user.id,
                'email': self.user.email,
                'first_name': self.user.first_name,
                'last_name': self.user.last_name,
                'google_picture': self.user.google_picture,
            }
        
        return data
    
    def is_owner(self):
        """Check if member is owner"""
        return self.role == 'owner'
    
    def is_editor(self):
        """Check if member is editor"""
        return self.role == 'editor'
    
    def is_viewer(self):
        """Check if member is viewer"""
        return self.role == 'viewer'
    
    def can_invite_users(self):
        """Check if member can invite users"""
        return self.role == 'owner'
    
    def can_manage_organization(self):
        """Check if member can manage organization settings"""
        return self.role == 'owner'
    
    def can_manage_members(self):
        """Check if member can manage other members"""
        return self.role == 'owner'
    
    def can_modify_content(self):
        """Check if member can modify content (connections, boards, etc.)"""
        return self.role in ['owner', 'editor']
    
    @classmethod
    def get_user_role_in_organization(cls, user_id, organization_id):
        """Get user's role in a specific organization"""
        member = cls.query.filter_by(
            user_id=user_id,
            organization_id=organization_id,
            is_active=True
        ).first()
        return member.role if member else None
    
    @classmethod
    def get_organization_members(cls, organization_id, active_only=True):
        """Get all members of an organization"""
        query = cls.query.filter_by(organization_id=organization_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.all()
    
    def __repr__(self):
        return f'<OrganizationMember org={self.organization_id} user={self.user_id} role={self.role}>'

