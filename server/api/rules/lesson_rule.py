import copy
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Dict, List, Set

from loguru import logger

from server.api.rules.utils import Hour
from server.api.utils import get_free_ranges_of_hours


class LessonRule(ABC):
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

    def __init__(self, date, student, hours):
        self.date = date
        self.student = student
        self.hours = hours

    @classmethod
    def init_hours(cls, date, student, start_hour, finish_hour, taken_lessons):
        """calculate new scores for hours, based on existing lessons"""
        hours = copy.deepcopy(cls.hours)
        if not taken_lessons:
            # if no lessons have been scheduled, keep default hours score list
            return hours
        free_ranges = get_free_ranges_of_hours(
            (date.replace(hour=start_hour), date.replace(hour=finish_hour)),
            taken_lessons,
        )

        get_delta = lambda time1, time2: int(
            (time1 - time2).total_seconds() / 60 / student.teacher.lesson_duration
        )  # how many lessons can fit between time1 and time2
        for range_ in free_ranges:
            current_time = range_[0]
            while current_time <= range_[1]:
                # how many lessons can fit until the end of the range
                delta_from_start = get_delta(current_time, range_[0])
                # how many from the start
                delta_from_end = get_delta(range_[1], current_time)
                addition = delta_from_start + delta_from_end
                score_decrease = 0
                if addition:
                    score_decrease = min(
                        9, round(((delta_from_start * delta_from_end)) / addition)
                    )
                hour = next(
                    (x for x in hours if x.value == current_time.hour), None
                )  # find the object in self.hours
                if hour:
                    logger.debug(
                        f"we want to decrease {score_decrease} from hour {hour.value} = {hour.score - score_decrease}"
                    )
                    hour.score -= score_decrease
                current_time += timedelta(hours=1)

        return hours

    def start_hour_rule(self) -> Set[int]:
        """returns the blacklisted start hours"""
        return set()

    def end_hour_rule(self) -> Set[int]:
        """returns the blacklisted end hours"""
        return set()

    def blacklisted(self) -> Dict[str, Set[int]]:
        """return entire dict with end_hour and start_hour"""
        return dict(start_hour=self.start_hour_rule(), end_hour=self.end_hour_rule())
