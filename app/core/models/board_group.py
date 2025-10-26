"""
Board Group model - business context frames on boards
"""
from app.core.models import db
from .base import BaseModel

class BoardGroup(BaseModel):
    """Group/Frame for business context (customers, departments, features)"""
    __tablename__ = 'board_groups'
    __table_args__ = (
        db.UniqueConstraint('board_id', 'fabric_id', name='unique_fabric_id_per_board'),
        {'extend_existing': True}
    )
    
    # Board relationship
    board_id = db.Column(db.Integer, db.ForeignKey('business_boards.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Group properties
    name = db.Column(db.String(255), nullable=False)
    fabric_id = db.Column(db.String(100), nullable=False)  # Fabric.js object ID for synchronization
    
    # Position and size on canvas
    position_x = db.Column(db.Float, nullable=False)
    position_y = db.Column(db.Float, nullable=False)
    width = db.Column(db.Float, nullable=False)
    height = db.Column(db.Float, nullable=False)
    
    # Visual properties
    color = db.Column(db.String(20), default='#3B82F6', nullable=False)  # Default to InfraZen Secondary Blue
    
    # Cost tracking
    calculated_cost = db.Column(db.Float, default=0.0, nullable=False)
    
    def to_dict(self, include_resources=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'board_id': self.board_id,
            'name': self.name,
            'fabric_id': self.fabric_id,
            'position': {
                'x': self.position_x,
                'y': self.position_y
            },
            'size': {
                'width': self.width,
                'height': self.height
            },
            'color': self.color,
            'calculated_cost': float(self.calculated_cost) if self.calculated_cost else 0.0,
            'resource_count': self.resources.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_resources:
            data['resources'] = [r.to_dict(include_resource=True) for r in self.resources.all()]
            
        return data
    
    def calculate_cost(self):
        """Calculate total cost of resources in this group"""
        from .board_resource import BoardResource
        
        total = 0.0
        for board_resource in self.resources.all():
            if board_resource.resource and board_resource.resource.daily_cost:
                total += float(board_resource.resource.daily_cost)
        
        self.calculated_cost = total
        db.session.commit()
        return total
    
    @classmethod
    def get_board_groups(cls, board_id):
        """Get all groups on a board"""
        return cls.query.filter_by(board_id=board_id).all()
    
    @classmethod
    def find_by_fabric_id(cls, board_id, fabric_id):
        """Find group by Fabric.js object ID"""
        return cls.query.filter_by(board_id=board_id, fabric_id=fabric_id).first()
    
    def __repr__(self):
        return f'<BoardGroup {self.id}: {self.name} (Cost: {self.calculated_cost})>'

