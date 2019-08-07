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


class ReportType(Enum):
    students = 1
    lessons = 2
    kilometers = 3


class Report(SurrogatePK, Model):
    """A test for a user"""

    __tablename__ = "reports"
    uuid = Column(db.String, default="", nullable=True)
    report_type = Column(ChoiceType(ReportType, impl=db.Integer()), nullable=False)
    since = Column(db.DateTime, nullable=True)
    until = Column(db.DateTime, nullable=True)
    teacher_id = reference_col("teachers", nullable=False)
    teacher = relationship("Teacher", backref=backref("reports", lazy="dynamic"))
    car_id = reference_col("cars", nullable=True)
    car = relationship("Car", backref=backref("reports", lazy="dynamic"))
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    DATES_REQUIRED = ["lessons", "kilometers"]  # list of types where dates are required

    def __init__(self, **kwargs):
        """Create instance."""
        self.uuid = str(uuid.uuid4())
        db.Model.__init__(self, **kwargs)

    def to_dict(self) -> dict:
        return {
            "uuid": self.uuid,
            "report_type": self.report_type.name,
            "created_at": self.created_at,
        }
