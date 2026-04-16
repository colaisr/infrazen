"""
Forecast / manual resource placements on business boards (not tied to catalog Resource sync).
"""
from app.core.models import db
from .base import BaseModel


class BoardForecastResource(BaseModel):
    """User-defined cost forecast chip on a board — survives catalog sync."""
    __tablename__ = 'board_forecast_resources'
    __table_args__ = {'extend_existing': True}

    board_id = db.Column(db.Integer, db.ForeignKey('business_boards.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    monthly_cost = db.Column(db.Float, default=0.0, nullable=False)

    position_x = db.Column(db.Float, nullable=False)
    position_y = db.Column(db.Float, nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('board_groups.id', ondelete='SET NULL'), nullable=True, index=True)

    board = db.relationship(
        'BusinessBoard',
        backref=db.backref('forecast_resources', lazy='dynamic', cascade='all, delete-orphan'),
    )
    group = db.relationship(
        'BoardGroup',
        backref=db.backref('forecast_resources', lazy='dynamic'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'board_id': self.board_id,
            'name': self.name,
            'monthly_cost': float(self.monthly_cost) if self.monthly_cost is not None else 0.0,
            'position': {'x': self.position_x, 'y': self.position_y},
            'group_id': self.group_id,
        }

    def __repr__(self):
        return f'<BoardForecastResource {self.id}: {self.name!r} {self.monthly_cost}/mo>'
