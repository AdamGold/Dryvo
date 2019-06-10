import enum
from datetime import datetime
from typing import Dict, Optional, Tuple

from sqlalchemy import and_
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
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
    description = Column(db.String, nullable=False)
    google_id = Column(db.String, nullable=True)
    used_as = Column(
        ChoiceType(PlaceType, impl=db.Integer()), default=1, nullable=False
    )
    times_used = Column(db.Integer, default=1)

    @classmethod
    def create_or_find(
        cls, place_dict: Optional[Dict], used_as: PlaceType, student: "Student"
    ) -> Optional["Place"]:
        try:
            description = place_dict["description"]
        except (KeyError, TypeError):
            return None
        if not description:
            return None
        try:
            ret = cls.query.filter(
                and_(
                    cls.description == description,
                    cls.used_as == used_as.value,
                    cls.student == student,
                )
            ).one()
            ret.update(times_used=ret.times_used + 1)
        except NoResultFound:
            ret = cls.create(
                student=student,
                description=description,
                google_id=place_dict.get("google_id"),
                used_as=used_as.value,
            )

        return ret

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    def to_dict(self):
        return {
            "description": self.description,
            "google_id": self.google_id,
            "used_as": self.used_as.name,
            "times_used": self.times_used,
        }
