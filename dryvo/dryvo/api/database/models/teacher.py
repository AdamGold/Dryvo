from api.database.mixins import Column, Model, SurrogatePK, db, relationship, reference_col
from sqlalchemy.orm import backref
from sqlalchemy import func

from api.database.models.lesson import Lesson
from api.utils import get_hour_string_from_date

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
        weekday = requested_date.isoweekday()
        work_days = self.work_days.filter_by(day=weekday).all()
        existing_lessons = self.lessons.filter(func.extract('day', Lesson.date) == requested_date.day). \
            filter(func.extract('month', Lesson.date) == requested_date.month)
        taken_lessons = existing_lessons.filter(Lesson.student_id != None).all()
        available = []
        for day in work_days:
            hours = [
                get_hour_string_from_date((
                    datetime.strptime(day.from_hour, '%H:%M')-timedelta(minutes=self.lesson_duration)
                )),
                day.to_hour]
            for lesson in taken_lessons:
                hour_string = get_hour_string_from_date(lesson.date)
                if hour_string >= day.from_hour and hour_string <= day.to_hour:
                    hours.append(hour_string)

            hours.sort()
            i = 0
            while i < len(hours)-1:
                lesson_start = hours[i]
                hour_datetime = datetime.strptime(lesson_start, '%H:%M')
                if get_hour_string_from_date(
                   hour_datetime + timedelta(minutes=2*self.lesson_duration)) <= hours[i+1]:
                        hour = get_hour_string_from_date(hour_datetime + timedelta(minutes=self.lesson_duration))
                        hours.insert(i+1, hour)
                        available.append(hour)
                i += 1

        for lesson in existing_lessons.filter_by(student_id=None).all():
            available.append(get_hour_string_from_date(lesson.date))
        return available
"""
        weekday = requested_date.isoweekday()
        work_days = self.work_days.filter_by(day=weekday).all()
        existing_lessons = self.lessons.filter(func.extract('day', Lesson.date) == requested_date.day). \
            filter(func.extract('month', Lesson.date) == requested_date.month)
        taken_lessons = [(lesson.date, lesson.date + timedelta(minutes=self.lesson_duration)) \
                         for lesson in existing_lessons.filter(Lesson.student_id != None).all()]
        for day in work_days:
            hours = (requested_date.replace(hour=int(day.from_hour[0:2]), minute=int(day.from_hour[3:5])),
                     requested_date.replace(hour=int(day.to_hour[0:2]), minute=int(day.to_hour[3:5])))
            self.get_slots(hours, taken_lessons)

    def get_slots(self, hours, appointments):
        duration = timedelta(minutes=self.lesson_duration)
        minimum = (hours[0], hours[0])
        maximum = (hours[1], hours[1])
        slots = [max(min(v, maximum), minimum) for v in sorted([minimum] + appointments + [maximum])]
        for start, end in((slots[i][1], slots[i+1][0]) for i in range(len(slots)-1)):
            while start + duration <= end:
                print("{:%H:%M} - {:%H:%M}".format(start, start + duration))
                start += duration

    def to_dict(self):
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'user_id': self.user_id,
        }
