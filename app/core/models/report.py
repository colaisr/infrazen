"""Models for generated FinOps reports."""

import enum

from app.core.database import db
from .base import BaseModel


class ReportStatus(enum.Enum):
    """Status values for generated reports."""

    IN_PROGRESS = 'in_progress'
    READY = 'ready'
    FAILED = 'failed'


class GeneratedReport(BaseModel):
    """Generated report metadata and content storage."""

    __tablename__ = 'generated_reports'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, index=True)
    status = db.Column(
        db.Enum(ReportStatus, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=ReportStatus.IN_PROGRESS,
        nullable=False,
        index=True
    )
    content_html = db.Column(db.Text, nullable=True)
    context_json = db.Column(db.JSON, nullable=True)

    user = db.relationship('User', backref='generated_reports')

    def to_dict(self):
        base = super().to_dict()
        base.update({
            'status': self.status.value if isinstance(self.status, ReportStatus) else self.status,
        })
        return base


