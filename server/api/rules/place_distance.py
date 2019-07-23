from datetime import timedelta
from typing import Dict, Set, List

from sqlalchemy import and_, func

from server.api.database.models import Appointment, PlaceType
from server.api.rules.lesson_rule import LessonRule
from server.api.rules.utils import register_rule
from server.api.gmaps import gmaps


MAXIMUM_DISTANCE = 15000
MAXIMUM_DURATION = 1200  # 20 min


@register_rule
class PlaceDistances(LessonRule):
    """if a place is >15km than the last / next lesson, eliminate that hour if that hour is >5 score"""

    def __init__(self, date, student, hours, places):
        super().__init__(date, student, hours)
        self.meetup_place_id = places[0]
        self.dropoff_place_id = places[1]
        self.today_lessons = self.student.teacher.lessons.filter(
            Appointment.approved_filter(
                func.extract("day", Appointment.date) == self.date.day,
                func.extract("month", Appointment.date) == self.date.month,
            )
        ).all()

    def filter_(self, type_: PlaceType = PlaceType.meetup) -> List[Appointment]:
        if not self.dropoff_place_id or not self.meetup_place_id:
            return []
        # loop through today's lessons
        relevant_lessons = []
        for lesson in self.today_lessons:
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
            row = distance["rows"][0]["elements"][0]
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
            if hour.score >= 5:
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
