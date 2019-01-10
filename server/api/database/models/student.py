import os
from datetime import datetime

from server.api.database.mixins import (
    Column,
    Model,
    SurrogatePK,
    relationship,
    reference_col,
)
from server.api.database import db
from server.api.database.models import Lesson

from sqlalchemy.orm import backref
from sqlalchemy.ext.hybrid import hybrid_method


class Student(SurrogatePK, Model):
    """A student of the app."""

    __tablename__ = "students"
    teacher_id = reference_col("teachers", nullable=False)
    teacher = relationship("Teacher", backref=backref("students", lazy="dynamic"))
    user_id = reference_col("users", nullable=False)
    user = relationship(
        "User", backref=backref("student", uselist=False), uselist=False
    )

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    @hybrid_method
    def filter_lessons(self, filter_args):
        lessons_query = self.lessons
        if filter_args.get("show") == "history":
            lessons_query = lessons_query.filter(Lesson.date < datetime.today())
        else:
            lessons_query = lessons_query.filter(Lesson.date > datetime.today())

        order_by_args = filter_args.get("order_by", "date desc").split()
        order_by = getattr(Lesson, order_by_args[0])
        order_by = getattr(order_by, order_by_args[1])()
        return lessons_query.filter_by(deleted=False).order_by(order_by)

    def to_dict(self):
        return {"id": self.id, "teacher_id": self.teacher_id, "user_id": self.user_id}
