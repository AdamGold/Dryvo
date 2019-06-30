from datetime import timedelta
from typing import Dict, Set

from sqlalchemy import and_

from server.api.database.models import Lesson
from server.api.rules.lesson_rule import LessonRule
from server.api.rules.more_than_lessons_week import MoreThanLessonsWeek
from server.api.rules.utils import register_rule


@register_rule
class NewStudents(LessonRule):
    """if a student has less than 5 lessons, blacklist hours <= 3 score"""

    def filter_(self):
        return self.student.lessons_done

    def start_hour_rule(self) -> Set[int]:
        more_than_rule = MoreThanLessonsWeek(
            self.date, self.student, self.hours
        ).blacklisted()
        if self.filter_() <= 5 and not more_than_rule["start_hour"]:
            return {hour.value for hour in self.hours if hour.score <= 3}

        return set()
