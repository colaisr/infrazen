"""
Base model classes with common functionality
"""
from datetime import datetime
from app.core.models import db

class BaseModel(db.Model):
    """Abstract base model with common fields and methods"""
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def save(self):
        """Save model to database"""
        db.session.add(self)
        db.session.commit()
        return self
    
    def delete(self):
        """Delete model from database"""
        db.session.delete(self)
        db.session.commit()
        return True
    
    @classmethod
    def find_by_id(cls, id):
        """Find model by ID"""
        return cls.query.get(id)
    
    @classmethod
    def find_all(cls):
        """Find all models"""
        return cls.query.all()
    
    def __repr__(self):
        return f'<{self.__class__.__name__} {self.id}>'
