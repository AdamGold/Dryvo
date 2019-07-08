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

    def __init__(self, date, student, hours, **kwargs):
        self.date = date
        self.student = student
        self.hours = hours

    @classmethod
    def init_hours(cls, date, student, work_hours, taken_lessons):
        """calculate new scores for hours, based on existing lessons"""
        hours = copy.deepcopy(cls.hours)
        if not taken_lessons or not work_hours:
            # if no lessons have been scheduled / no work hours, keep default hours score list
            return hours
        hours_range = (
            date.replace(hour=work_hours[0].from_hour),
            date.replace(hour=work_hours[-1].to_hour),
        )
        free_ranges = get_free_ranges_of_hours(hours_range, taken_lessons)

        get_delta = lambda time1, time2: int(
            (time1 - time2).total_seconds() / 60 / student.teacher.lesson_duration
        )  # how many lessons can fit between time1 and time2
        current_time = None
        for range_ in free_ranges:
            if range_[0].hour <= getattr(
                current_time, "hour", -1
            ):  # in 2nd iteration, we've already done this hour
                current_time = range_[0] + timedelta(hours=1)
            else:
                current_time = range_[0]

            while current_time <= range_[1]:
                # how many lessons can fit until the end of the range
                delta_from_start = get_delta(current_time, range_[0])
                # how many from the start
                delta_from_end = get_delta(range_[1], current_time)
                addition = delta_from_start + delta_from_end
                score_decrease = 0
                if delta_from_start:
                    score_decrease = min(
                        9, round(addition / delta_from_start)
                    )  # extra emphasis on delta from start (we want to fill the first ones first)
                try:
                    hour = hours[current_time.hour - 7]  # every index is hour - 7
                    if hour.value == current_time.hour:
                        logger.debug(
                            f"we want to decrease {score_decrease} from hour {hour.value} = {hour.score - score_decrease}"
                        )
                        hour.score -= score_decrease
                except IndexError:
                    logger.debug(
                        f"Trying to get {current_time.hour} hour but it doesn't exist."
                    )
                current_time += timedelta(hours=1)

        return hours

    @abstractmethod
    def filter_(self):
        """return the filtering result of the rule"""

    def start_hour_rule(self) -> Set[int]:
        """returns the blacklisted start hours"""
        return set()

    def end_hour_rule(self) -> Set[int]:
        """returns the blacklisted end hours"""
        return set()

    def blacklisted(self) -> Dict[str, Set[int]]:
        """return entire dict with end_hour and start_hour"""
        return dict(start_hour=self.start_hour_rule(), end_hour=self.end_hour_rule())
