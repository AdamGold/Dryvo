import datetime as dt

from api.database.mixins import Column, Model, SurrogatePK, db, relationship, reference_col
from api.database.utils import QueryWithSoftDelete

from sqlalchemy.orm import backref


class Lesson(SurrogatePK, Model):
    """A driving lesson"""

    __tablename__ = 'lessons'
    query_class = QueryWithSoftDelete
    teacher_id = reference_col('teachers', nullable=False)
    teacher = relationship('Teacher', backref=backref('lessons', lazy='dynamic'))
    student_id = reference_col('students', nullable=True)
    student = relationship('Student', backref=backref('lessons', lazy='dynamic'))
    duration = Column(db.Integer, nullable=False)
    time = Column(db.Integer, nullable=False)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    meetup = Column(db.String, nullable=True)
    is_approved = Column(db.Boolean, nullable=False, default=True)
    content = Column(db.Text, nullable=True)
    deleted = Column(db.Boolean, nullable=False, default=False)
    
    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    def update_only_changed_fields(self, **kwargs):
        args = {k: v for k, v in kwargs.items() if v}
        self.update(**args)

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
