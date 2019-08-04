import datetime as dt
from enum import Enum, auto

from flask_login import current_user
from sqlalchemy import and_, func, or_
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref
from sqlalchemy.sql import expression
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
                self.price = self.student.price * self.lesson_length
            else:
                self.price = self.teacher.price * self.lesson_length

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

    @staticmethod
    def appointments_between(start_date, end_date):
        appointment_end_date = addinterval(Appointment.date, Appointment.duration)
        query = Appointment.approved_filter(
            or_(
                and_(start_date <= Appointment.date, Appointment.date < end_date),
                and_(
                    start_date < appointment_end_date, appointment_end_date <= end_date
                ),
            )
        )
        return Appointment.query.filter(query)

    @hybrid_property
    def lesson_length(self) -> float:
        return self.duration / self.teacher.lesson_duration

    @hybrid_property
    def lesson_number(self) -> float:
        lessons = Appointment.query.filter(
            self.approved_lessons_filter(
                Appointment.date < self.date, Appointment.student == self.student
            )
        ).all()

        return (
            sum(lesson.lesson_length for lesson in lessons)
            + self.student.number_of_old_lessons
            + self.lesson_length
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
            "type": self.type.name.lower(),
        }

    def __repr__(self):
        return (
            f"<Appointment date={self.date}, created_at={self.created_at},"
            f"student={self.student}, teacher={self.teacher}"
            f",approved={self.is_approved}, number={self.lesson_number}, duration={self.duration}>"
        )


class addinterval(expression.FunctionElement):
    type = db.DateTime()
    name = "addinterval"


@compiles(addinterval, "sqlite")
def sl_addinterval(element, compiler, **kw):
    dt1, dt2 = list(element.clauses)
    return compiler.process(
        func.datetime(func.strftime("%s", dt1) + dt2 * 60, "unixepoch")
    )


@compiles(addinterval)
def default_addinterval(element, compiler, **kw):
    dt1, dt2 = list(element.clauses)
    return compiler.process(dt1 + func.make_interval(0, 0, 0, 0, 0, dt2))
