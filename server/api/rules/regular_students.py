from datetime import timedelta
from typing import Dict, List, Set

from sqlalchemy import and_

from server.api.rules.utils import register_rule
from server.api.rules.lesson_rule import LessonRule
from server.api.database.models import Lesson


@register_rule
class RegularStudents(LessonRule):
    """students with 10-20 lessons - blacklist hours > 8 score"""

    def filter_(self):
        return self.student.lessons_done

    def start_hour_rule(self) -> Set[int]:
        if self.filter_() >= 10 and self.filter_() <= 20:
            return {hour.value for hour in self.hours if hour.score > 8}
        return set()
