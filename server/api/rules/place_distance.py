from datetime import timedelta
from typing import Dict, Set, List

from sqlalchemy import and_, func

from server.api.database.models import Lesson, PlaceType
from server.api.rules.lesson_rule import LessonRule
from server.api.rules.utils import register_rule
from server.api import gmaps


MAXIMUM_DISTANCE = 15000
MAXIMUM_DURATION = 600


@register_rule
class PlaceDistances(LessonRule):
    """if a place is >15km than the last / next lesson, eliminate that hour if that hour is >5 score"""

    def filter_(self, type_: PlaceType = PlaceType.meetup) -> List[Lesson]:
        if not self.dropoff_place_id or not self.meetup_place_id:
            return []
        # loop through today's lessons
        today_lessons = self.student.teacher.lessons.filter(
            Lesson.approved_lessons_filter(
                func.extract("day", Lesson.date) == self.date.day,
                func.extract("month", Lesson.date) == self.date.month,
            )
        ).all()
        relevant_lessons = []
        for lesson in today_lessons:
            if type_ == PlaceType.meetup:
                origin = lesson.meetup_place.google_id
                destination = self.dropoff_place_id
            else:
                origin = self.meetup_place_id
                destination = lesson.dropoff_place.google_id
            distance = gmaps.distance_matrix(
                origins=[f"place_id:{origin}"],
                destinations=[f"place_id:{destination}"],
                units="metric",
                mode="driving",
            )
            row = distance["rows"][0]["elements"]
            if (
                row["distance"]["value"] >= MAXIMUM_DISTANCE
                or row["duration"]["value"] >= MAXIMUM_DURATION
            ):
                relevant_lessons.append(lesson)

        # return list of lessons where their {type_} place (meetup/dropoff) >15km than current place
        return relevant_lessons

    def check_hour(self, hour, blacklist):
        try:
            hour = self.hours[hour - 7]
            if hour.score >= 6:
                blacklist.add(hour)
        except IndexError:
            return None

    def start_hour_rule(self) -> Set[int]:
        """eliminate the ending hours of the lessons where the current meetup place >15km than dropoff place"""
        lessons = self.filter_(PlaceType.dropoff)
        blacklist: Set[int] = set()
        for lesson in lessons:
            end_hour = (lesson.date + timedelta(minutes=lesson.duration)).hour
            self.check_hour(end_hour, blacklist)

        return blacklist

    def end_hour_rule(self) -> Set[int]:
        """eliminate the starting hours of the lessons where the current meetup place >15km than meetup place"""
        lessons = self.filter_(PlaceType.meetup)
        blacklist: Set[int] = set()
        for lesson in lessons:
            start_hour = lesson.date.hour
            self.check_hour(start_hour, blacklist)

        return blacklist
