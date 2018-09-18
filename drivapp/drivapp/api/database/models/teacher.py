from api.database.mixins import Column, Model, SurrogatePK, db, relationship, reference_col


class Teacher(SurrogatePK, Model):
    """A user of the app."""

    __tablename__ = 'teachers'
    user_id = reference_col('users', nullable=False)
    user = relationship('User', uselist=False)
    area = Column(db.String(80), nullable=False)
    price = Column(db.Integer, nullable=False)
    phone = Column(db.String, nullable=False)
    is_paying = Column(db.Boolean, default=True, nullable=False)
    price_rating = Column(db.Float, nullable=True)
    availabillity_rating = Column(db.Float, nullable=True)
    content_rating = Column(db.Float, nullable=True)

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'user_id': self.user_id,
            'area': self.area,
        }
