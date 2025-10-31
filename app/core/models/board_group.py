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
        """Calculate total cost of resources in this group, accounting for clones"""
        from .board_resource import BoardResource
        
        resources_in_group = self.resources.all()
        
        total = 0.0
        processed_resource_ids = set()  # Track which resources we've already counted
        
        for board_resource in resources_in_group:
            if not board_resource.resource or not board_resource.resource.daily_cost:
                continue
            
            resource_id = board_resource.resource.id
            daily_cost = float(board_resource.resource.daily_cost)
            
            # Skip if we already processed this resource (multiple instances in same group)
            if resource_id in processed_resource_ids:
                continue
            
            processed_resource_ids.add(resource_id)
            
            # Find all clones of this resource on this board
            all_clones = BoardResource.query.filter_by(
                board_id=self.board_id,
                resource_id=resource_id
            ).all()
            
            # Count how many different groups have clones (excluding None/unassigned)
            groups_with_clones = set()
            for clone in all_clones:
                if clone.group_id is not None:
                    groups_with_clones.add(clone.group_id)
            
            # Calculate the split cost
            if len(groups_with_clones) == 0:
                # No clones in any group - no cost
                split_cost = 0.0
            elif len(groups_with_clones) == 1:
                # All clones in one group (or mix of one group + unassigned)
                split_cost = daily_cost
            else:
                # Clones in multiple groups - split the cost
                split_cost = daily_cost / len(groups_with_clones)
            
            total += split_cost
            
            print(f'   Resource "{board_resource.resource.resource_name}": {len(all_clones)} clones, {len(groups_with_clones)} groups → {split_cost}/day')
        
        self.calculated_cost = total
        db.session.commit()
        
        print(f'💰 Group "{self.name}" total cost: {total}/day ({len(resources_in_group)} board_resources, {len(processed_resource_ids)} unique resources)')
        
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

