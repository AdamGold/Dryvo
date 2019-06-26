from datetime import timedelta
from typing import Dict, Set

from sqlalchemy import and_

from server.api.rules.utils import register_rule
from server.api.rules.lesson_rule import LessonRule
from server.api.database.models import Lesson


@register_rule
class NewStudents(LessonRule):
    """if a student has less than 5 lessons, blacklist hours <= 3 score"""

    def filter_(self):
        return self.student.lessons_done

    def start_hour_rule(self) -> Set[int]:
        if self.filter_() <= 5:
            return {hour.value for hour in self.hours if hour.score <= 3}

        return set()
