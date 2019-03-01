import datetime as dt
from enum import Enum, auto
from typing import List

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


class Topic(SurrogatePK, Model):
    """A test for a user"""

    __tablename__ = "topics"
    title = Column(db.String, default=False, nullable=False)
    min_lesson_number = Column(db.Integer, nullable=False)
    max_lesson_number = Column(db.Integer, nullable=False)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    @staticmethod
    def for_lesson(num: int):
        return Topic.query.filter(
            and_(Topic.min_lesson_number <= num, Topic.max_lesson_number >= num)
        ).all()

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "created_at": self.created_at}
