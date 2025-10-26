"""
Business Board model for visual resource mapping
"""
from app.core.models import db
from .base import BaseModel

class BusinessBoard(BaseModel):
    """Board for visual business context mapping"""
    __tablename__ = 'business_boards'
    
    # Owner relationship
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Board properties
    name = db.Column(db.String(255), nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    
    # Canvas state (Fabric.js serialization)
    canvas_state = db.Column(db.JSON, nullable=True)  # Full Fabric.js canvas JSON
    
    # Viewport settings
    viewport = db.Column(db.JSON, nullable=True)  # {zoom, pan_x, pan_y}
    
    # Relationships
    user = db.relationship('User', backref=db.backref('business_boards', lazy='dynamic', cascade='all, delete-orphan'))
    resources = db.relationship('BoardResource', backref='board', lazy='dynamic', cascade='all, delete-orphan')
    groups = db.relationship('BoardGroup', backref='board', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self, include_canvas=False):
        """Convert board to dictionary"""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'resource_count': self.resources.count(),
            'group_count': self.groups.count()
        }
        
        if include_canvas:
            data['canvas_state'] = self.canvas_state
            data['viewport'] = self.viewport
            
        return data
    
    @classmethod
    def get_user_boards(cls, user_id):
        """Get all boards for a user"""
        return cls.query.filter_by(user_id=user_id).order_by(cls.updated_at.desc()).all()
    
    @classmethod
    def get_default_board(cls, user_id):
        """Get user's default board"""
        return cls.query.filter_by(user_id=user_id, is_default=True).first()
    
    @classmethod
    def set_default_board(cls, user_id, board_id):
        """Set a board as default (unset others)"""
        # Unset all defaults for this user
        cls.query.filter_by(user_id=user_id).update({'is_default': False})
        # Set the new default
        board = cls.query.filter_by(id=board_id, user_id=user_id).first()
        if board:
            board.is_default = True
            db.session.commit()
        return board
    
    def __repr__(self):
        return f'<BusinessBoard {self.id}: {self.name}>'

