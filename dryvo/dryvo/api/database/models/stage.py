import datetime as dt

from api.database.mixins import Column, Model, SurrogatePK, db, relationship, reference_col
from api.database.models.topic import Topic

from sqlalchemy.orm import backref


class Stage(SurrogatePK, Model):
    """A test for a user"""

    __tablename__ = 'stages'
    title = Column(db.String, nullable=False)
    order = Column(db.Integer, nullable=False)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    def to_dict(self, student_id=None):
        return {
            'id': self.id,
            'title': self.title,
            'order': self.order,
            'topics': [t.to_dict(student_id) for t in self.topics.order_by(Topic.order).all()]
        }
