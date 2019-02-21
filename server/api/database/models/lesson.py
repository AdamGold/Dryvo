import datetime as dt

from flask_login import current_user
from sqlalchemy import and_
from sqlalchemy.orm import backref

from server.api.database import db
from server.api.database.mixins import (
    Column,
    Model,
    SurrogatePK,
    reference_col,
    relationship,
)
from server.api.database.models import Topic
from server.api.database.utils import QueryWithSoftDelete


class Lesson(SurrogatePK, Model):
    """A driving lesson"""

    __tablename__ = "lessons"
    query_class = QueryWithSoftDelete
    teacher_id = reference_col("teachers", nullable=False)
    teacher = relationship("Teacher", backref=backref("lessons", lazy="dynamic"))
    student_id = reference_col("students", nullable=True)
    student = relationship("Student", backref=backref("lessons", lazy="dynamic"))
    topics = relationship("LessonTopic", lazy="dynamic")
    duration = Column(db.Integer, nullable=False)
    date = Column(db.DateTime, nullable=False)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    meetup_place_id = reference_col("places", nullable=True)
    meetup_place = relationship("Place", foreign_keys=[meetup_place_id])
    dropoff_place_id = reference_col("places", nullable=True)
    dropoff_place = relationship("Place", foreign_keys=[dropoff_place_id])
    is_approved = Column(db.Boolean, nullable=False, default=True)
    comments = Column(db.Text, nullable=True)
    deleted = Column(db.Boolean, nullable=False, default=False)
    creator_id = reference_col("users", nullable=False)
    creator = relationship("User")
    lesson_number = Column(db.Integer, nullable=True)

    ALLOWED_FILTERS = ["deleted", "date", "student_id", "created_at", "lesson_number"]
    default_sort_column = "date"

    def __init__(self, **kwargs):
        """Create instance."""
        if not kwargs.get("creator") and current_user.is_authenticated:
            self.creator = current_user
        self.lesson_number = (
            kwargs["student"].new_lesson_number if kwargs.get("student") else None
        )
        db.Model.__init__(self, **kwargs)

    def update_only_changed_fields(self, **kwargs):
        args = {k: v for k, v in kwargs.items() if v or isinstance(v, bool)}
        self.update(**args)

    @staticmethod
    def topics_for_lesson(num: int):
        return Topic.query.filter(
            and_(Topic.min_lesson_number <= num, Topic.max_lesson_number >= num)
        ).all()

    def to_dict(self):
        return {
            "id": self.id,
            "teacher_id": self.teacher_id,
            "student_id": self.student_id,
            "date": self.date,
            "meetup_place": self.meetup_place.to_dict() if self.meetup_place else None,
            "dropoff_place": self.dropoff_place.to_dict()
            if self.dropoff_place
            else None,
            "is_approved": self.is_approved,
            "comments": self.comments,
            "topics": [topic.to_dict() for topic in self.topics.all()],
            "lesson_number": self.lesson_number,
            "created_at": self.created_at,
            "duration": self.duration,
        }

    def __repr__(self):
        return (
            f"<Lesson date={self.date}, created_at={self.created_at},"
            f"student={self.student}, teacher={self.teacher}"
            f",approved={self.is_approved}, number={self.lesson_number}>"
        )
