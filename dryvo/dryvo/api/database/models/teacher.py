from api.database.mixins import Column, Model, SurrogatePK, db, relationship, reference_col
from sqlalchemy.orm import backref


class Teacher(SurrogatePK, Model):
    """A teacher of the app."""

    __tablename__ = 'teachers'
    user_id = reference_col('users', nullable=False)
    user = relationship('User', backref=backref('teacher', uselist=False), uselist=False)
    price = Column(db.Integer, nullable=False)
    phone = Column(db.String, nullable=False)
    price_rating = Column(db.Float, nullable=True)
    availabillity_rating = Column(db.Float, nullable=True)
    content_rating = Column(db.Float, nullable=True)

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    def free_lessons(self):
        pass

    def to_dict(self):
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'user_id': self.user_id,
        }
