import os
from datetime import datetime

from api.database.mixins import Column, Model, SurrogatePK, db, relationship, reference_col

from sqlalchemy.orm import backref


class Student(SurrogatePK, Model):
    """A student of the app."""

    __tablename__ = 'students'
    teacher_id = reference_col('teachers', nullable=False)
    teacher = relationship('Teacher', backref=backref('students', lazy='dynamic'))
    user_id = reference_col('users', nullable=False)
    user = relationship('User', backref='student', uselist=False)

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'user_id': self.user_id,
        }
