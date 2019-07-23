from datetime import datetime, timedelta

import pytest
from sqlalchemy import func
import json

from server.api.database.models import Appointment, PlaceType, Place
from server.api.rules import (
    LessonRule,
    more_than_lessons_week,
    regular_students,
    place_distance,
)


def test_abc_class():
    class Test(LessonRule):
        def a():
            return "hello"

    with pytest.raises(TypeError):
        t = Test()


def test_blacklisted(student):
    s = {1, 2, 3}
    date = datetime.utcnow()

    class A(LessonRule):
        def filter_(self):
            return None

        def start_hour_rule(self):
            return s

    assert A(date, student, []).blacklisted() == {"start_hour": s, "end_hour": set()}


def test_init_hours(student, teacher, meetup, dropoff):
    # TODO improve test logic
    initial_hours = LessonRule.hours
    date = datetime.utcnow().replace(hour=6, minute=0) + timedelta(days=2)
    Appointment.create(
        teacher=teacher,
        student=student,
        creator=teacher.user,
        duration=teacher.lesson_duration,
        date=date,
        meetup_place=meetup,
        dropoff_place=dropoff,
        is_approved=True,
    )
    query = Appointment.query.filter(
        func.extract("day", Appointment.date) == date.day
    ).filter(func.extract("month", Appointment.date) == date.month)
    new_hours = LessonRule.init_hours(
        date,
        student,
        teacher.work_hours_for_date(date),
        teacher.taken_appointments_tuples(query, only_approved=True),
    )
    assert initial_hours != new_hours
    # we want to fill the gap after 6, so hours 7 and 8 should be really cold
    hour_8 = new_hours[1].score
    hour_7 = new_hours[0].score
    old_hour_7 = initial_hours[0].score
    old_hour_8 = initial_hours[1].score
    assert hour_7 < old_hour_7
    assert hour_8 < old_hour_8


@pytest.fixture
def hours(student, teacher):
    date = datetime.utcnow() + timedelta(days=2)
    query = Appointment.query.filter(
        func.extract("day", Appointment.date) == date.day
    ).filter(func.extract("month", Appointment.date) == date.month)
    return LessonRule.init_hours(
        date,
        student,
        teacher.work_hours_for_date(date),
        teacher.taken_appointments_tuples(query, only_approved=True),
    )


def test_more_than_lessons_in_week(student, teacher, hours, meetup, dropoff):
    date = datetime.utcnow() + timedelta(days=2)
    rule = more_than_lessons_week.MoreThanLessonsWeek(date, student, hours)
    assert not rule.blacklisted()["start_hour"]
    for i in range(3):
        Appointment.create(
            teacher=teacher,
            student=student,
            creator=teacher.user,
            duration=teacher.lesson_duration,
            date=date + timedelta(minutes=i * teacher.lesson_duration),
            meetup_place=meetup,
            dropoff_place=dropoff,
            is_approved=True,
        )
    assert rule.blacklisted()["start_hour"]


def test_regular_students(student, teacher, hours, meetup, dropoff):
    date = datetime.utcnow() - timedelta(days=2)
    rule = regular_students.RegularStudents(date, student, hours)
    assert not rule.blacklisted()["start_hour"]
    for i in range(10):
        Appointment.create(
            teacher=teacher,
            student=student,
            creator=teacher.user,
            duration=teacher.lesson_duration,
            date=date + timedelta(minutes=i * teacher.lesson_duration),
            meetup_place=meetup,
            dropoff_place=dropoff,
            is_approved=True,
        )
    assert rule.blacklisted()["start_hour"]


def test_place_distances(student, teacher, meetup, dropoff, hours, responses):
    date = datetime.utcnow().replace(hour=16, minute=0)
    Appointment.create(
        teacher=teacher,
        student=student,
        creator=teacher.user,
        duration=teacher.lesson_duration,
        date=date,
        meetup_place=meetup,
        dropoff_place=dropoff,
        is_approved=True,
    )
    ret = {
        "destination_addresses": ["HaNassi Blvd, Haifa, Israel"],
        "origin_addresses": ["Gruenbaum St 3, Haifa, Israel"],
        "rows": [
            {
                "elements": [
                    {
                        "distance": {"text": "4.8 mi", "value": 7742},
                        "duration": {"text": "17 mins", "value": 1037},
                        "status": "OK",
                    }
                ]
            }
        ],
        "status": "OK",
    }
    responses.add(
        responses.GET,
        "https://maps.googleapis.com/maps/api/distancematrix/json",
        body=json.dumps(ret),
        status=200,
        content_type="application/json",
    )
    rule = place_distance.PlaceDistances(date, student, hours, ("test1", "test2"))
    assert not rule.blacklisted()["start_hour"]
    ret = {
        "destination_addresses": ["Arlozorov St, Tel Aviv-Yafo, Israel"],
        "origin_addresses": ["Gruenbaum St 3, Haifa, Israel"],
        "rows": [
            {
                "elements": [
                    {
                        "distance": {"text": "59.4 mi", "value": 95649},
                        "duration": {"text": "1 hour 16 mins", "value": 4539},
                        "status": "OK",
                    }
                ]
            }
        ],
        "status": "OK",
    }
    responses.replace(
        responses.GET,
        "https://maps.googleapis.com/maps/api/distancematrix/json",
        body=json.dumps(ret),
        status=200,
        content_type="application/json",
    )
    rule = place_distance.PlaceDistances(date, student, hours, ("test2", "test3"))
    blacklist = rule.blacklisted()
    assert blacklist["start_hour"]
    assert blacklist["end_hour"]
