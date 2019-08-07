import datetime as dt
import uuid
from enum import Enum
from typing import List

from sqlalchemy import and_
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


class CarType(Enum):
    manual = 1
    auto = 2


class Car(SurrogatePK, Model):
    """Teacher's car"""

    __tablename__ = "cars"
    name = Column(db.String, nullable=True)
    type = Column(ChoiceType(CarType, impl=db.Integer()), default=1, nullable=False)
    number = Column(db.Integer, nullable=False)
    teacher_id = reference_col("teachers", nullable=False)
    teacher = relationship("Teacher", backref=backref("cars", lazy="dynamic"))
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type.name,
            "number": self.numbere,
            "created_at": self.created_at,
        }
