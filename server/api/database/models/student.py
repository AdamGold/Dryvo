import itertools
from datetime import datetime
from typing import List, Set

from cloudinary.utils import cloudinary_url
from flask_login import current_user
from flask_sqlalchemy import BaseQuery
from sqlalchemy import and_, func, select, cast
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import backref
from sqlalchemy.sql.functions import coalesce

from server.api.database import db
from server.api.database.mixins import (
    Column,
    Model,
    SurrogatePK,
    reference_col,
    relationship,
)
from server.api.database.models import (
    Appointment,
    LessonCreator,
    LessonTopic,
    Payment,
    Place,
    PlaceType,
    Teacher,
    Topic,
)


class Student(SurrogatePK, LessonCreator):
    """A student of the app."""

    __tablename__ = "students"
    teacher_id = reference_col("teachers", nullable=False)
    teacher = relationship("Teacher", backref=backref("students", lazy="dynamic"))
    is_approved = Column(db.Boolean, default=False, nullable=False)
    is_active = Column(db.Boolean, default=True, nullable=False)
    creator_id = reference_col("users", nullable=False)
    creator = relationship("User", foreign_keys=[creator_id])
    created_at = Column(db.DateTime, nullable=False, default=datetime.utcnow)
    number_of_old_lessons = Column(db.Float, nullable=False, default=0)
    theory = Column(db.Boolean, nullable=False, default=False)
    doctor_check = Column(db.Boolean, nullable=False, default=False)
    eyes_check = Column(db.Boolean, nullable=False, default=False)
    green_form = Column(db.String(240), nullable=True)
    price = Column(db.Integer, nullable=True)

    ALLOWED_FILTERS = [
        "is_active",
        "is_approved",
        "theory",
        "doctor_check",
        "eyes_check",
        "green_form",
    ]

    def __init__(self, **kwargs):
        """Create instance."""
        if current_user and not kwargs.get("creator") and current_user.is_authenticated:
            self.creator = current_user
        db.Model.__init__(self, **kwargs)
        if not self.price:
            self.price = self.teacher.price

    def _lesson_topics(self, is_finished: bool):
        lesson_ids = [lesson.id for lesson in self.lessons]
        return LessonTopic.query.filter(
            and_(
                LessonTopic.lesson_id.in_(lesson_ids),
                LessonTopic.is_finished == is_finished,
            )
        ).order_by(LessonTopic.created_at.desc())

    def _topics_in_progress(self, lesson_topics: BaseQuery) -> Set[Topic]:
        """loop through given lesson topics, check for rows
        that do not have is_finished in other rows -
        these are the in progress topics.
        """
        topics = (lt.topic for lt in lesson_topics.all())
        in_progress_topics = itertools.filterfalse(
            lambda topic: (
                LessonTopic.query.filter_by(topic_id=topic.id)
                .filter_by(is_finished=True)
                .first()
            ),
            topics,
        )
        return set(list(in_progress_topics))

    def topics(self, is_finished: bool) -> Set[Topic]:
        """get topics for student. if status is finished,
        get all finished lesson_topics. if in progress, get lesson_topics
        that do not have finished status - get latest row of each one.
        return topic of lesson_topic"""
        lesson_topics = self._lesson_topics(is_finished)
        if is_finished:
            """if we check for is_finished,
            there should be one row with is_finished=True for each topic"""
            return {lt.topic for lt in lesson_topics.all()}

        return self._topics_in_progress(lesson_topics)

    @hybrid_property
    def common_meetup(self) -> Place:
        return (
            self.places.filter_by(used_as=PlaceType.meetup.value)
            .order_by(Place.times_used.desc())
            .first()
        )

    @hybrid_property
    def common_dropoff(self) -> Place:
        return (
            self.places.filter_by(used_as=PlaceType.dropoff.value)
            .order_by(Place.times_used.desc())
            .first()
        )

    @hybrid_property
    def lessons_done(self) -> int:
        """return the number of a new lesson:
        num of latest lesson+1"""
        latest_lesson = (
            self.lessons.filter(
                Appointment.approved_lessons_filter(
                    Appointment.date < datetime.utcnow()
                )
            )
            .order_by(Appointment.date.desc())
            .limit(1)
            .one_or_none()
        )
        starting_count = self.number_of_old_lessons
        if not latest_lesson:
            return starting_count
        return latest_lesson.lesson_number

    @lessons_done.expression
    def lessons_done(cls):
        q = select(
            [
                cast(func.sum(Appointment.duration), db.Float)
                / (func.count(Appointment.student_id) * Teacher.lesson_duration)
            ]
        ).where(
            Appointment.approved_lessons_filter(
                Appointment.date < datetime.utcnow(), Appointment.student_id == cls.id
            )
        )
        j = Student.__table__.join(Teacher.__table__)
        q = q.select_from(j).label("lessons_done")
        return q + cls.number_of_old_lessons

    @hybrid_property
    def balance(self):
        """calculate sum of payments minus
        number of lessons taken * price"""
        return self.total_paid - self.total_lessons_price

    @balance.expression
    def balance(cls):
        return cls.total_paid - cls.total_lessons_price

    @hybrid_property
    def total_lessons_price(self):
        return (
            sum(
                lesson.price
                for lesson in self.lessons.filter(
                    Appointment.approved_lessons_filter(
                        Appointment.date < datetime.utcnow()
                    )
                ).all()
            )
            + self.price * self.number_of_old_lessons
        )

    @total_lessons_price.expression
    def total_lessons_price(cls):
        q = (
            select([coalesce(func.sum(Appointment.price), 0)])
            .where(
                Appointment.approved_lessons_filter(
                    Appointment.date < datetime.utcnow(),
                    Appointment.student_id == cls.id,
                )
            )
            .label("total_lessons_price")
        )
        return q + cls.number_of_old_lessons * cls.price

    @hybrid_property
    def total_paid(self):
        return sum([payment.amount for payment in self.payments])

    @total_paid.expression
    def total_paid(cls):
        q = (
            select([coalesce(func.sum(Payment.amount), 0)])
            .where(Payment.student_id == cls.id)
            .label("total_paid")
        )
        return q

    def to_dict(self, with_user=True):
        green_form = ""
        if self.green_form:
            try:
                green_form = cloudinary_url(self.green_form)[0]
            except Exception:
                pass

        if with_user:
            return self.user.to_dict()  # returns user dict with student info
        return {
            "student_id": self.id,
            "my_teacher": self.teacher.to_dict(),
            "balance": self.balance,
            "lessons_done": self.lessons_done,
            "is_approved": self.is_approved,
            "is_active": self.is_active,
            "theory": self.theory,
            "eyes_check": self.eyes_check,
            "doctor_check": self.doctor_check,
            "number_of_old_lessons": self.number_of_old_lessons,
            "green_form": green_form,
            "price": self.price,
        }

    def __repr__(self):
        return (
            f"<Student id={self.id}, balance={self.balance}"
            f", total_lessons_price={self.total_lessons_price}"
            f", lessons_done={self.lessons_done}, teacher={self.teacher}"
            f", total_paid={self.total_paid}>"
        )
