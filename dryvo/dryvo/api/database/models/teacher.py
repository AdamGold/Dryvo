from api.database.mixins import Column, Model, SurrogatePK, db, relationship, reference_col
from sqlalchemy.orm import backref
from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_method

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
        work_hours = self.work_days.filter_by(on_date=requested_date).all()
        if not work_hours:
            work_hours = self.work_days.filter_by(day=weekday).all()
        existing_lessons = self.lessons.filter(func.extract('day', Lesson.date) == requested_date.day). \
            filter(func.extract('month', Lesson.date) == requested_date.month)
        taken_lessons = [(lesson.date, lesson.date + timedelta(minutes=lesson.duration)) \
                         for lesson in existing_lessons.filter(Lesson.student_id != None).all()]
        available = []
        work_hours.sort(key=lambda x: x.from_hour) # sort from early to late
        for day in work_hours:
            hours = (requested_date.replace(hour=day.from_hour, minute=day.from_minutes),
                     requested_date.replace(hour=day.to_hour, minute=day.to_minutes))
            available.extend(get_slots(hours, taken_lessons, timedelta(minutes=self.lesson_duration)))

        for lesson in existing_lessons.filter_by(student_id=None).all():
            available.append((lesson.date, lesson.date + timedelta(minutes=lesson.duration)))

        return sorted(available)

    @hybrid_method
    def filter_lessons(self, filter_args):
        """
        Future: more teacher filter to come.
        """
        lessons_query = self.lessons
        deleted = False
        if 'deleted' in filter_args:
            deleted = True
        if filter_args.get('show') == 'history':
            lessons_query = lessons_query.filter(Lesson.date < datetime.today())
        else:
            lessons_query = lessons_query.filter(Lesson.date > datetime.today())

        order_by_args = filter_args.get('order_by', 'date desc').split()
        order_by = getattr(Lesson, order_by_args[0])
        order_by = getattr(order_by, order_by_args[1])()
        return lessons_query.filter_by(deleted=deleted).order_by(order_by)

    def to_dict(self):
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'user_id': self.user_id,
        }
