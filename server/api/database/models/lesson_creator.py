import werkzeug
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.orm import backref

from server.api.database.mixins import (Column, Model, SurrogatePK,
                                        reference_col, relationship)
from server.api.database.models import Lesson, User


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
    def filter_lessons(self, args: werkzeug.datastructures.MultiDict):
        query = self.lessons
        if "deleted" not in args or self.__class__.__name__.lower() == "student":
            # default to non deleted items
            query = query.filter_by(deleted=False)
            try:
                args.pop("deleted")
            except KeyError:
                pass
        return Lesson.filter_and_sort(args, default_sort_column="date",
                                      query=query, with_pagination=True)
