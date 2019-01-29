import enum
from datetime import datetime

from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy import and_
from sqlalchemy.orm import backref
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy_utils import ChoiceType

from server.api.database import db
from server.api.database.mixins import (
    Column,
    Model,
    SurrogatePK,
    reference_col,
    relationship,
)
from server.api.database.models import Lesson


class PlaceType(enum.Enum):
    meetup = 1
    dropoff = 2


class Place(SurrogatePK, Model):
    """A dropoff/meetup place"""

    __tablename__ = "places"
    student_id = reference_col("students", nullable=False)
    student = relationship("Student", backref=backref("places", lazy="dynamic"))
    name = Column(db.String, nullable=False)
    used_as = Column(
        ChoiceType(PlaceType, impl=db.Integer()), default=1, nullable=False
    )
    times_used = Column(db.Integer, default=1)

    @staticmethod
    def create_or_find(name: str, used_as: PlaceType, student: "Student") -> "Place":
        if not name:
            return
        try:
            ret = Place.query.filter(
                and_(
                    Place.name.like(f"{name}%"),
                    Place.used_as == used_as.value,
                    Place.student == student,
                )
            ).one()
            ret.update(times_used=ret.times_used + 1)
        except NoResultFound:
            ret = Place.create(student=student, name=name, used_as=used_as.value)

        return ret

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    def to_dict(self):
        return {
            "name": self.name,
            "used_as": self.used_as.name,
            "times_used": self.times_used,
        }
