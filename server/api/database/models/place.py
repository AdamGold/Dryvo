from datetime import datetime

from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import backref

from server.api.database import db
from server.api.database.mixins import (Column, Model, SurrogatePK,
                                        reference_col, relationship)
from server.api.database.models import Lesson


class Place(SurrogatePK, Model):
    """A dropoff/meetup place"""

    __tablename__ = "places"
    student_id = reference_col("students", nullable=False)
    student = relationship(
        "Student", backref=backref("places", lazy="dynamic"))
    name = Column(db.String, nullable=False)
    used_as_meetup = Column(db.Integer, default=0)
    used_as_dropoff = Column(db.Integer, default=0)

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)
