from api.database.mixins import Column, Model, SurrogatePK, db, relationship, reference_col
from sqlalchemy.orm import backref
from sqlalchemy import func

from api.database.models.lesson import Lesson
from api.database.utils import get_slots

from datetime import datetime, timedelta


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
    lesson_duration = Column(db.Integer, default=40, nullable=False)

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    def available_hours(self, requested_date):
        """
        1. calculate available hours - decrease existing lessons times from work hours
        2. calculate lesson hours from available hours by default lesson duration
        MUST BE 24-hour format. 09:00, not 9:00
        """
        weekday = requested_date.isoweekday()
        work_days = self.work_days.filter_by(day=weekday).all()
        existing_lessons = self.lessons.filter(func.extract('day', Lesson.date) == requested_date.day). \
            filter(func.extract('month', Lesson.date) == requested_date.month)
        taken_lessons = [(lesson.date, lesson.date + timedelta(minutes=lesson.duration)) \
                         for lesson in existing_lessons.filter(Lesson.student_id != None).all()]
        available = []
        work_days.sort(key=lambda x: x.from_hour) # sort from early to late
        for day in work_days:
            hours = (requested_date.replace(hour=day.from_hour, minute=day.from_minutes),
                     requested_date.replace(hour=day.to_hour, minute=day.to_minutes))
            available.extend(get_slots(hours, taken_lessons, timedelta(minutes=self.lesson_duration)))

        for lesson in existing_lessons.filter_by(student_id=None).all():
            available.append((lesson.date, lesson.date + timedelta(minutes=lesson.duration)))

        return sorted(available)

    def to_dict(self):
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'user_id': self.user_id,
        }
