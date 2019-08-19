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
    type = Column(
        ChoiceType(CarType, impl=db.Integer()), default=CarType.manual, nullable=False
    )
    number = Column(db.String, nullable=False)
    teacher_id = reference_col("teachers", nullable=False)
    teacher = relationship(
        "Teacher",
        backref=backref("cars", lazy="dynamic", order_by="Car.created_at.asc()"),
    )
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    color = Column(db.String, nullable=True)

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.name,
            "number": self.number,
            "color": self.color,
            "created_at": self.created_at,
        }
