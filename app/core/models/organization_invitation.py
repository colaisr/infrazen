"""
OrganizationInvitation model for tracking invitation history
Supports both registered and unregistered users with invitation tokens
"""
from app.core.models import db
from .base import BaseModel
import secrets


class OrganizationInvitation(BaseModel):
    """Model for tracking organization invitations (audit trail)"""
    __tablename__ = 'organization_invitations'
    
    # Relationships
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False, default='viewer')  # viewer, editor
    
    # Invitation tracking
    invited_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Status tracking (for audit trail)
    status = db.Column(db.String(20), nullable=False, default='sent')  # sent, accepted, revoked, failed
    accepted_at = db.Column(db.DateTime, nullable=True)
    revoked_at = db.Column(db.DateTime, nullable=True)
    
    # Invitation token for unregistered users
    invitation_token = db.Column(db.String(255), nullable=True, unique=True, index=True)
    
    # Relationships
    organization = db.relationship('Organization', backref='invitations')
    invited_by = db.relationship('User', foreign_keys=[invited_by_user_id])
    
    def to_dict(self):
        """Convert invitation to dictionary"""
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'email': self.email,
            'role': self.role,
            'invited_by_user_id': self.invited_by_user_id,
            'status': self.status,
            'accepted_at': self.accepted_at.isoformat() if self.accepted_at else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def generate_invitation_token(self):
        """Generate a unique token for invitation (for unregistered users)"""
        self.invitation_token = secrets.token_urlsafe(32)
        db.session.commit()
        return self.invitation_token
    
    @classmethod
    def find_by_token(cls, token):
        """Find invitation by token"""
        return cls.query.filter_by(invitation_token=token, status='sent').first()
    
    @classmethod
    def find_pending_by_email(cls, email):
        """Find pending invitation by email"""
        return cls.query.filter_by(
            email=email.lower(),
            status='sent'
        ).order_by(cls.created_at.desc()).first()
    
    @classmethod
    def get_organization_invitations(cls, organization_id):
        """Get all invitations for an organization"""
        return cls.query.filter_by(organization_id=organization_id).order_by(cls.created_at.desc()).all()
    
    def __repr__(self):
        return f'<OrganizationInvitation org={self.organization_id} email={self.email} role={self.role}>'

