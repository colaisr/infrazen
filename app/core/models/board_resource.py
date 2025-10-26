"""
Board Resource model - tracks resource placement on boards
"""
from app.core.models import db
from .base import BaseModel

class BoardResource(BaseModel):
    """Resource placement on business context boards"""
    __tablename__ = 'board_resources'
    __table_args__ = (
        db.UniqueConstraint('board_id', 'resource_id', name='unique_resource_per_board'),
        {'extend_existing': True}
    )
    
    # Board and resource relationships
    board_id = db.Column(db.Integer, db.ForeignKey('business_boards.id', ondelete='CASCADE'), nullable=False, index=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Position on canvas
    position_x = db.Column(db.Float, nullable=False)
    position_y = db.Column(db.Float, nullable=False)
    
    # Group assignment
    group_id = db.Column(db.Integer, db.ForeignKey('board_groups.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # User notes about this resource
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    resource = db.relationship('Resource', backref=db.backref('board_placements', lazy='dynamic'))
    group = db.relationship('BoardGroup', backref=db.backref('resources', lazy='dynamic'))
    
    def to_dict(self, include_resource=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'board_id': self.board_id,
            'resource_id': self.resource_id,
            'position': {
                'x': self.position_x,
                'y': self.position_y
            },
            'group_id': self.group_id,
            'notes': self.notes,
            'has_notes': bool(self.notes),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_resource and self.resource:
            data['resource'] = {
                'id': self.resource.id,
                'name': self.resource.resource_name,
                'type': self.resource.resource_type,
                'service': self.resource.service_name,
                'ip': self.resource.external_ip,
                'status': self.resource.status,
                'provider_id': self.resource.provider_id,
                'daily_cost': float(self.resource.daily_cost) if self.resource.daily_cost else 0.0,
                'currency': self.resource.currency,
                'notes': self.resource.notes,
                'has_notes': bool(self.resource.notes)
            }
            
        return data
    
    @classmethod
    def is_resource_placed(cls, board_id, resource_id):
        """Check if resource is already placed on board"""
        return cls.query.filter_by(board_id=board_id, resource_id=resource_id).first() is not None
    
    @classmethod
    def get_board_resources(cls, board_id):
        """Get all resources placed on a board"""
        return cls.query.filter_by(board_id=board_id).all()
    
    @classmethod
    def get_unplaced_resources(cls, user_id):
        """Get resources not placed on any board for a user"""
        from .resource import Resource
        from .business_board import BusinessBoard
        
        # Get all board IDs for this user
        board_ids = db.session.query(BusinessBoard.id).filter_by(user_id=user_id).subquery()
        
        # Get all resource IDs already placed
        placed_resource_ids = db.session.query(cls.resource_id).filter(
            cls.board_id.in_(board_ids)
        ).distinct().subquery()
        
        # Get resources for this user's providers that are not placed
        unplaced = Resource.query.join(
            Resource.provider
        ).filter(
            Resource.provider.has(user_id=user_id),
            ~Resource.id.in_(placed_resource_ids)
        ).all()
        
        return unplaced
    
    def __repr__(self):
        return f'<BoardResource {self.id}: Resource {self.resource_id} on Board {self.board_id}>'

