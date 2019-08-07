import datetime as dt
import uuid
from enum import Enum
from typing import List

from sqlalchemy import and_
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


class Kilometer(SurrogatePK, Model):
    """daily report of distances in km"""

    __tablename__ = "kilometers"
    start_of_day = Column(db.Float, nullable=False)
    end_of_day = Column(db.Float, nullable=False)
    personal = Column(db.Float, default=0, nullable=False)
    date = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    teacher_id = reference_col("teachers", nullable=False)
    teacher = relationship("Teacher", backref=backref("kilometers", lazy="dynamic"))
    car_id = reference_col("cars", nullable=False)
    car = relationship("Car", backref=backref("kilometers", lazy="dynamic"))

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    @hybrid_property
    def total_work_km(self) -> float:
        return self.end_of_day - self.start_of_day + self.personal

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "car": self.car.to_dict(),
            "total_work_km": self.total_work_km,
            "start_of_day": self.start_of_day,
            "end_of_day": self.end_of_day,
            "personal": self.personal,
        }
