from typing import Dict, List
from abc import ABC, abstractmethod
from server.api.rules.utils import Hour
from server.api.utils import get_free_ranges_of_hours
from datetime import timedelta


class LessonRule(ABC):
    default_dict: Dict[str, List[int]] = {"start_hour": [], "end_hour": []}
    hours = [
        Hour(value=7, score=1),
        Hour(value=8, score=2),
        Hour(value=9, score=3),
        Hour(value=10, score=3),
        Hour(value=11, score=5),
        Hour(value=12, score=7),
        Hour(value=13, score=8),
        Hour(value=14, score=9),
        Hour(value=15, score=9),
        Hour(value=16, score=9),
        Hour(value=17, score=8),
        Hour(value=18, score=8),
        Hour(value=19, score=7),
        Hour(value=20, score=5),
        Hour(value=21, score=3),
        Hour(value=22, score=1),
    ]

    def __init__(self, date, student, start_hour, finish_hour, taken_lessons):
        self.date = date
        self.student = student

        # calculate new scores for hours, based on existing lessons
        free_ranges = get_free_ranges_of_hours(
            (date.replace(hour=start_hour), date.replace(hour=finish_hour)),
            taken_lessons,
        )

        get_delta = lambda time1, time2: int(
            (time1 - time2).total_seconds() / 60 / student.teacher.lesson_duration
        )
        for range_ in free_ranges:
            current_time = range_[0]
            while current_time <= range_[1]:
                delta_from_start = get_delta(current_time, range_[0])
                delta_from_end = get_delta(range_[1], current_time)
                score_decrease = round(
                    (
                        (delta_from_start * delta_from_end)
                        + (delta_from_start + delta_from_end)
                    )
                    / 2
                )
                hour = next(
                    (x for x in self.hours if x.value == current_time.hour), None
                )
                hour.score -= score_decrease
                current_time += timedelta(hours=1)

    @abstractmethod
    def blacklisted(self) -> Dict[str, List[int]]:
        """the actual rule conditions
        returns the blacklisted hours"""
