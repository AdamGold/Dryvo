import datetime as dt

from api.database.mixins import Column, Model, SurrogatePK, db, relationship, reference_col

from sqlalchemy.orm import backref
from sqlalchemy_utils import ChoiceType
import enum


class Day(enum.Enum):
    sunday = 1
    monday = 2
    tuesday = 3
    wednesday = 4
    thursday = 5
    friday = 6
    saturday = 7


class WorkDay(SurrogatePK, Model):
    """A Work day"""

    __tablename__ = 'work_days'
    teacher_id = reference_col('teachers', nullable=False)
    teacher = relationship('Teacher', backref=backref('work_days', lazy='dynamic'))
    day = Column(ChoiceType(Day, impl=db.Integer()), nullable=False)
    from_hour = Column(db.String, nullable=False)
    to_hour = Column(db.String, nullable=False)

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'day': self.day.name,
            'from_hour': self.from_hour,
            'to_hour': self.to_hour,
        }
