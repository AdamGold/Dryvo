import datetime as dt
import enum

from sqlalchemy.ext.hybrid import hybrid_method
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


class Day(enum.Enum):
    sunday = 0
    monday = 1
    tuesday = 2
    wednesday = 3
    thursday = 4
    friday = 5
    saturday = 6


class WorkDay(SurrogatePK, Model):
    """A Work day"""

    __tablename__ = "work_days"
    teacher_id = reference_col("teachers", nullable=False)
    teacher = relationship("Teacher", backref=backref("work_days", lazy="dynamic"))
    day = Column(ChoiceType(Day, impl=db.Integer()), nullable=False)
    from_hour = Column(db.Integer, nullable=False)
    from_minutes = Column(db.Integer, nullable=False, default=0)
    to_hour = Column(db.Integer, nullable=False)
    to_minutes = Column(db.Integer, nullable=False, default=0)
    on_date = Column(db.Date, nullable=True)

    ALLOWED_FILTERS = ["day", "on_date"]
    default_sort_column = "day"

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    def to_dict(self):
        return {
            "id": self.id,
            "teacher_id": self.teacher_id,
            "day": self.day.name,
            "from_hour": self.from_hour,
            "to_hour": self.to_hour,
            "on_date": self.on_date,
        }

    def __repr__(self):
        return f"<WorkDay {self.day}, {self.from_hour}:{self.from_minutes}-{self.to_hour}-{self.to_minutes}, {self.on_date}>"
