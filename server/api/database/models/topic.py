import datetime as dt

from server.api.database.mixins import (
    Column,
    Model,
    SurrogatePK,
    db,
    relationship,
    reference_col,
)
from server.api.database.models import Lesson

from sqlalchemy.orm import backref


class Topic(SurrogatePK, Model):
    """A test for a user"""

    __tablename__ = "topics"
    stage_id = reference_col("stages", nullable=False)
    stage = relationship("Stage", backref=backref("topics", lazy="dynamic"))
    title = Column(db.String, default=False, nullable=False)
    order = Column(db.Integer, nullable=True)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    def is_marked(self, student_id):
        if not student_id:
            return False
        lesson = (
            Lesson.query.filter_by(student_id=student_id)
            .filter_by(topic_id=self.id)
            .filter_by(mark_topic=True)
            .first()
        )
        if not lesson:
            return False
        return True

    def mark_for_student(self, student_id, mark=True):
        lesson = (
            Lesson.query.filter_by(student_id=student_id)
            .filter_by(topic_id=self.id)
            .first()
        )
        if not lesson:
            return False
        lesson.update(mark_topic=mark)
        return True

    def to_dict(self, student_id=None):
        return {
            "id": self.id,
            "title": self.title,
            "order": self.order,
            "created_at": self.created_at,
            "is_marked": self.is_marked(student_id),
        }
