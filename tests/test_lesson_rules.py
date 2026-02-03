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


def get_hour_by_value(hours, value):
    """Helper to find an Hour object by its hour value."""
    for hour in hours:
        if hour.value == value:
            return hour
    return None


def test_init_hours(student, teacher, meetup, dropoff):
    """Test that init_hours reduces scores for hours adjacent to existing appointments.

    When an appointment exists at a given time, the algorithm should reduce
    the scores of nearby hours to encourage filling gaps and creating a
    contiguous schedule.
    """
    initial_hours = LessonRule.hours
    # Create an appointment at 6 AM, two days from now
    appointment_date = datetime.utcnow().replace(hour=6, minute=0) + timedelta(days=2)
    Appointment.create(
        teacher=teacher,
        student=student,
        creator=teacher.user,
        duration=teacher.lesson_duration,
        date=appointment_date,
        meetup_place=meetup,
        dropoff_place=dropoff,
        is_approved=True,
    )

    # Query for appointments on the same day
    query = Appointment.query.filter(
        func.extract("day", Appointment.date) == appointment_date.day
    ).filter(func.extract("month", Appointment.date) == appointment_date.month)

    # Calculate new hour scores based on the existing appointment
    new_hours = LessonRule.init_hours(
        appointment_date,
        student,
        teacher.work_hours_for_date(appointment_date),
        teacher.taken_appointments_tuples(query, only_approved=True),
    )

    # The hours list should be modified with new scores
    assert initial_hours != new_hours

    # Hours 7 and 8 (immediately after the 6 AM appointment) should have reduced
    # scores to encourage filling the gap and creating a contiguous schedule
    initial_hour_7 = get_hour_by_value(initial_hours, 7)
    initial_hour_8 = get_hour_by_value(initial_hours, 8)
    new_hour_7 = get_hour_by_value(new_hours, 7)
    new_hour_8 = get_hour_by_value(new_hours, 8)

    assert new_hour_7.score < initial_hour_7.score, (
        f"Hour 7 score should decrease after adjacent appointment: "
        f"got {new_hour_7.score}, expected less than {initial_hour_7.score}"
    )
    assert new_hour_8.score < initial_hour_8.score, (
        f"Hour 8 score should decrease after adjacent appointment: "
        f"got {new_hour_8.score}, expected less than {initial_hour_8.score}"
    )


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
