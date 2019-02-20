import itertools
from datetime import datetime
from typing import List

from sqlalchemy import and_
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import backref

from server.api.database import db
from server.api.database.mixins import (
    Column,
    Model,
    SurrogatePK,
    reference_col,
    relationship,
)
from server.api.database.models import (
    Lesson,
    LessonTopic,
    Place,
    PlaceType,
    Topic,
    LessonCreator,
)


class Student(SurrogatePK, LessonCreator):
    """A student of the app."""

    __tablename__ = "students"
    teacher_id = reference_col("teachers", nullable=False)
    teacher = relationship("Teacher", backref=backref("students", lazy="dynamic"))

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    @hybrid_property
    def new_lesson_number(self) -> int:
        """return the number of a new lesson:
        all lessons+1"""
        return len(self.lessons.all()) + 1

    def _lesson_topics(self, is_finished: bool):
        lesson_ids = [lesson.id for lesson in self.lessons]
        return LessonTopic.query.filter(
            and_(
                LessonTopic.lesson_id.in_(lesson_ids),
                LessonTopic.is_finished == is_finished,
            )
        ).order_by(LessonTopic.created_at.desc())

    def _topics_in_progress(self, lesson_topics: list) -> List[LessonTopic]:
        """loop through given lesson topics, check for rows
        that do not have is_finished in other rows -
        these are the in progress topics.
        """
        topics = (Topic.get_by_id(lt.topic_id) for lt in lesson_topics.all())
        in_progress_topics = itertools.dropwhile(
            lambda topic: (
                LessonTopic.query.filter_by(topic_id=topic.id)
                .filter_by(is_finished=True)
                .first()
            ),
            topics,
        )
        return list(set(in_progress_topics))

    def filter_topics(self, is_finished: bool) -> List[LessonTopic]:
        """get topics for student. if status is finished,
        get all finished lesson_topics. if in progress, get lesson_topics
        that do not have finished status - get latest row of each one.
        return topic of lesson_topic"""
        lesson_topics = self._lesson_topics(is_finished)
        if is_finished:
            """if we check for is_finished,
            there should be one row with is_finished=True for each topic"""
            return [
                Topic.query.filter_by(id=lt.topic_id).first()
                for lt in lesson_topics.all()
            ]
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
    def balance(self):
        """calculate sum of payments minus
        number of lessons taken * price"""
        lessons_price = (self.new_lesson_number - 1) * self.teacher.price
        return sum([payment.amount for payment in self.payments]) - lessons_price

    def to_dict(self):
        return {"student_id": self.id, "my_teacher": self.teacher.to_dict()}
