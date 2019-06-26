from datetime import timedelta
from typing import Dict, List

from sqlalchemy import and_

from server.api.rules.utils import register_rule
from server.api.rules.lesson_rule import LessonRule
from server.api.database.models import Lesson


@register_rule
class ColdIfMoreThan3Lessons(LessonRule):
    """if a student has already scheduled 2 lessons this week, return hours >5 score (blacklisted)"""

    def filter_(self):
        start_of_week = self.date.replace(hour=00, minute=00) - timedelta(
            days=self.date.weekday() + 1
        )  # the 1 because monday is 0, we need sunday to be 0
        end_of_week = start_of_week + timedelta(days=6)
        return self.student.lessons.filter(
            and_(Lesson.date >= start_of_week, Lesson.date <= end_of_week)
        ).count()

    def blacklisted(self) -> Dict[str, List[int]]:
        if self.filter_() >= 2:
            self.default_dict.update(
                dict(start_hour=[hour.value for hour in self.hours if hour.score > 5])
            )
        return self.default_dict
