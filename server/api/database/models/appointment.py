import datetime as dt
from enum import Enum, auto

from flask_login import current_user
from sqlalchemy import and_, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref
from sqlalchemy_utils import ChoiceType

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


class AppointmentType(Enum):
    LESSON = auto()
    TEST = auto()
    INNER_EXAM = auto()


class Appointment(SurrogatePK, Model):
    """A driving lesson/test/exam"""

    __tablename__ = "appointments"
    query_class = QueryWithSoftDelete
    teacher_id = reference_col("teachers", nullable=False)
    teacher = relationship("Teacher", backref=backref("appointments", lazy="dynamic"))
    student_id = reference_col("students", nullable=True)
    student = relationship("Student", backref=backref("appointments", lazy="dynamic"))
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
    price = Column(db.Integer, nullable=True)
    type = Column(
        ChoiceType(AppointmentType, impl=db.Integer()),
        default=AppointmentType.LESSON.value,
        nullable=False,
    )

    ALLOWED_FILTERS = [
        "deleted",
        "is_approved",
        "date",
        "student_id",
        "created_at",
        "creator_id",
    ]
    default_sort_column = "date"

    def __init__(self, **kwargs):
        """Create instance."""
        if current_user and not kwargs.get("creator") and current_user.is_authenticated:
            self.creator = current_user
        db.Model.__init__(self, **kwargs)
        if not self.price:
            if self.student:
                self.price = self.student.price
            else:
                self.price = self.teacher.price

    def update_only_changed_fields(self, **kwargs):
        args = {k: v for k, v in kwargs.items() if v or isinstance(v, bool)}
        self.update(**args)

    @staticmethod
    def approved_filter(*args):
        return and_(
            Appointment.is_approved == True, Appointment.deleted == False, *args
        )

    @staticmethod
    def approved_lessons_filter(*args):
        return Appointment.approved_filter(
            Appointment.type == AppointmentType.LESSON.value, *args
        )

    @hybrid_property
    def lesson_number(self):
        return (
            (
                db.session.query(func.count(Appointment.id))
                .select_from(Appointment)
                .filter(
                    self.approved_lessons_filter(
                        Appointment.date < self.date,
                        Appointment.student == self.student,
                    )
                )
                .scalar()
            )
            + self.student.number_of_old_lessons
            + 1
        )

    def to_dict(self):
        return {
            "id": self.id,
            "student": self.student.user.to_dict() if self.student else None,
            "date": self.date,
            "meetup_place": self.meetup_place.description
            if self.meetup_place
            else None,
            "dropoff_place": self.dropoff_place.description
            if self.dropoff_place
            else None,
            "is_approved": self.is_approved,
            "comments": self.comments,
            "lesson_number": self.lesson_number,
            "created_at": self.created_at,
            "duration": self.duration,
            "price": self.price,
            "creator_id": self.creator_id,
        }

    def __repr__(self):
        return (
            f"<Appointment date={self.date}, created_at={self.created_at},"
            f"student={self.student}, teacher={self.teacher}"
            f",approved={self.is_approved}, number={self.lesson_number}, duration={self.duration}>"
        )
