import datetime as dt

from server.api.database.mixins import (
    Column,
    Model,
    SurrogatePK,
    relationship,
    reference_col,
)
from server.api.database import db
from sqlalchemy.orm import backref


class Review(SurrogatePK, Model):
    """Review of a teacher"""

    __tablename__ = "reviews"
    teacher_id = reference_col("teachers", nullable=False)
    teacher = relationship("Teacher", backref=backref("reviews", lazy="dynamic"))
    student_id = reference_col("students", nullable=False)
    student = relationship("Student", backref=backref("reviews", lazy="dynamic"))
    content = Column(db.Text, nullable=True)
    price_rating = Column(db.Float, nullable=False)
    availability_rating = Column(db.Float, nullable=False)
    content_rating = Column(db.Float, nullable=False)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    def to_dict(self):
        return {
            "id": self.id,
            "teacher_id": self.teacher_id,
            "student_id": self.student_id,
            "content": self.content,
            "price_rating": self.price_rating,
            "availability_rating": self.availability_rating,
            "content_rating": self.content_rating,
            "created_at": self.created_at,
        }
