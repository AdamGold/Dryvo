from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.orm import backref
from sqlalchemy.ext.declarative import declared_attr

from server.api.database.mixins import (Column, Model, SurrogatePK,
                                        reference_col, relationship)
from server.api.database.models import Lesson


class LessonCreator(Model):
    @declared_attr
    def user_id(self):
        return reference_col("users", nullable=False)

    @declared_attr
    def user(self):
        return relationship(
            "User", backref=backref(self.__tablename__[:-1], uselist=False), uselist=False
        )
    __abstract__ = True

    @hybrid_method
    def filter_lessons(self, filter_args):
        """allow filtering by student, date, lesson_number
        eg. ?limit=20&page=2&student=1&date=lt:2019-01-20T13:20Z&lesson_number=lte:5"""
        filters = {k: v for k, v in filter_args.items()
                   if k in Lesson.ALLOWED_FILTERS}
        lessons_query = self.lessons
        for column, filter_ in filters.items():
            lessons_query = lessons_query.filter(
                Model._filter_data(Lesson, column, filter_))
        order_by = Model._sort_data(
            Lesson, filter_args, default_column="date")
        lessons_query = lessons_query.filter_by(
            deleted=False).order_by(order_by)
        if "limit" in filter_args:
            return lessons_query.paginate(
                filter_args.get("page", 1, type=int), filter_args.get(
                    "limit", 20, type=int)
            )
        return lessons_query.all()
