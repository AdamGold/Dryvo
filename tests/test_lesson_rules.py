import pytest
from datetime import datetime, timedelta

from server.api.rules import (
    LessonRule,
    more_than_lessons_week,
    new_students,
    regular_students,
)
from server.api.database.models import Lesson


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


@pytest.fixture
def hours(student, teacher):
    date = datetime.utcnow() + timedelta(days=2)
    return LessonRule.init_hours(
        date,
        student,
        teacher.work_hours_for_date(date),
        teacher.taken_lessons_for_date(Lesson.query, only_approved=True),
    )


def test_more_than_lessons_in_week(student, teacher, hours, meetup, dropoff):
    date = datetime.utcnow() + timedelta(days=2)
    rule = more_than_lessons_week.MoreThanLessonsWeek(date, student, hours)
    assert not rule.blacklisted()["start_hour"]
    for i in range(3):
        Lesson.create(
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
        Lesson.create(
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


def test_new_students(student, teacher, hours, meetup, dropoff):
    date = datetime.utcnow() + timedelta(days=2)
    rule = new_students.NewStudents(date, student, hours)
    assert rule.blacklisted()["start_hour"]  # we have 1 lesson
    Lesson.create(
        teacher=teacher,
        student=student,
        creator=teacher.user,
        duration=teacher.lesson_duration,
        date=date,
        meetup_place=meetup,
        dropoff_place=dropoff,
        is_approved=True,
    )
    assert not rule.blacklisted()[
        "start_hour"
    ]  # more than lessons in a week rule is stronger, and we now have 2 lessons

