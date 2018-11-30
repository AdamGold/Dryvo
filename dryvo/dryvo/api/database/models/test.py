import datetime as dt

from api.database.mixins import Column, Model, SurrogatePK, db, relationship, reference_col

from sqlalchemy.orm import backref


class Test(SurrogatePK, Model):
    """A test for a user"""

    __tablename__ = 'tests'
    student_id = reference_col('students', nullable=False)
    student = relationship('Student', backref=backref('tests', lazy='dynamic'))
    result = Column(db.Boolean, default=False, nullable=False)
    content = Column(db.Text, nullable=True)
    time = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'result': self.result,
            'time': self.time,
            'content': self.content,
            'created_at': self.created_at,
        }
