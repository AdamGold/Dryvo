from datetime import timedelta
from typing import Dict, Set

from sqlalchemy import and_

from server.api.rules.utils import register_rule
from server.api.rules.lesson_rule import LessonRule
from server.api.database.models import Appointment


@register_rule
class MoreThanLessonsWeek(LessonRule):
    """if a student has already scheduled 2 lessons this week, return hours >5 score (blacklisted)"""

    def filter_(self):
        weekday = ["NEVER USED", 1, 2, 3, 4, 5, 6, 0][
            self.date.isoweekday()
        ]  # convert sundays to 0
        start_of_week = self.date.replace(hour=00, minute=00) - timedelta(days=weekday)
        end_of_week = start_of_week.replace(hour=23, minute=59) + timedelta(days=6)
        return self.student.lessons.filter(
            and_(Appointment.date >= start_of_week, Appointment.date <= end_of_week)
        ).count()

    def start_hour_rule(self) -> Set[int]:
        if self.filter_() >= 2:
            return {hour.value for hour in self.hours if hour.score > 4}
        return set()
