"""
Organization model for multi-tenant support
"""
from app.core.models import db
from .base import BaseModel


class Organization(BaseModel):
    """Organization model for multi-tenant data isolation"""
    __tablename__ = 'organizations'
    
    # Organization properties
    name = db.Column(db.String(255), nullable=False, index=True)
    
    # Relationships
    members = db.relationship('OrganizationMember', backref='organization', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self, include_members=False):
        """Convert organization to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_members:
            data['member_count'] = self.members.filter_by(is_active=True).count()
            data['members'] = [member.to_dict() for member in self.members.filter_by(is_active=True).all()]
        
        return data
    
    def get_owner(self):
        """Get the owner of this organization"""
        return self.members.filter_by(role='owner', is_active=True).first()
    
    def get_user_role(self, user_id):
        """Get the role of a user in this organization"""
        member = self.members.filter_by(user_id=user_id, is_active=True).first()
        return member.role if member else None
    
    def is_user_member(self, user_id):
        """Check if a user is a member of this organization"""
        return self.members.filter_by(user_id=user_id, is_active=True).first() is not None
    
    def is_user_owner(self, user_id):
        """Check if a user is the owner of this organization"""
        member = self.members.filter_by(user_id=user_id, role='owner', is_active=True).first()
        return member is not None
    
    @classmethod
    def get_user_organizations(cls, user_id):
        """Get all organizations a user belongs to"""
        # Import here to avoid circular import
        from .organization_member import OrganizationMember
        return cls.query.join(OrganizationMember).filter(
            OrganizationMember.user_id == user_id,
            OrganizationMember.is_active == True
        ).all()
    
    @classmethod
    def get_user_personal_organization(cls, user_id):
        """Get user's personal organization (where they are owner)"""
        # Import here to avoid circular import
        from .organization_member import OrganizationMember
        return cls.query.join(OrganizationMember).filter(
            OrganizationMember.user_id == user_id,
            OrganizationMember.role == 'owner',
            OrganizationMember.is_active == True
        ).first()
    
    def __repr__(self):
        return f'<Organization {self.name}>'

