"""
Resource tagging model
"""
from app.core.models import db
from .base import BaseModel

class ResourceTag(BaseModel):
    """Resource tags for categorization and cost allocation"""
    __tablename__ = 'resource_tags'
    
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False, index=True)
    tag_key = db.Column(db.String(100), nullable=False, index=True)
    tag_value = db.Column(db.String(255), nullable=False)
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('resource_id', 'tag_key', name='unique_resource_tag'),
    )
    
    def __repr__(self):
        return f'<ResourceTag {self.tag_key}:{self.tag_value}>'
