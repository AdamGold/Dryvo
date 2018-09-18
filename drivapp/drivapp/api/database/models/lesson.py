import datetime as dt

from api.database.mixins import Column, Model, SurrogatePK, db, relationship, reference_col

from sqlalchemy.orm import backref


class Lesson(SurrogatePK, Model):
    """A user of the app."""

    __tablename__ = 'lessons'
    teacher_id = reference_col('teachers', nullable=False)
    teacher = relationship('Teacher', backref=backref('lessons', lazy='dynamic'))
    student_id = reference_col('students', nullable=False)
    student = relationship('Student', backref=backref('lessons', lazy='dynamic'))
    time = Column(db.DateTime, nullable=False)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    meetup = Column(db.String, nullable=True)
    is_approved = Column(db.Boolean, nullable=False, default=False)

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'student_id': self.student_id,
            'time': self.time,
            'meetup': self.meetup,
            'is_approved': self.is_approved,
            'created_at': self.created_at,
        }
