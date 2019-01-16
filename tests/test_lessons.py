import pytest
from datetime import datetime
from loguru import logger

from server.api.database.models import Lesson, WorkDay
from server.consts import DATE_FORMAT


def test_lessons(auth, teacher, student, requester):
    auth.login(email=student.user.email)
    Lesson.create(teacher_id=teacher.id, student_id=student.id, creator_id=student.user.id,
                  duration=40, date=datetime(year=2018, month=11, day=27, hour=13, minute=00),
                  meetup='test', dropoff='test')
    resp = requester.get("/lessons/")
    assert isinstance(resp.json['data'], list)
    assert 'next_url' in resp.json
    assert 'prev_url' in resp.json


def test_student_new_lesson(auth, teacher, student, requester):
    auth.login(email=student.user.email)
    date = "2018-11-27T13:00Z"
    kwargs = {
        "teacher_id": teacher.id,
        "day": 1,
        "from_hour": 13,
        "from_minutes": 0,
        "to_hour": 17,
        "to_minutes": 0,
        "on_date": datetime(year=2018, month=11, day=27)
    }
    WorkDay.create(**kwargs)
    logger.debug(f"added work day for {teacher}")
    resp = requester.post("/lessons/",
                          json={'date': date, "meetup": "test", "dropoff": "test"})
    assert 'successfully' in resp.json['message']
    assert not resp.json['data']['is_approved']


def test_hour_not_available(auth, teacher, student, requester):
    auth.login(email=student.user.email)
    date = "2018-11-27T12:00Z"
    kwargs = {
        "teacher_id": teacher.id,
        "day": 1,
        "from_hour": 13,
        "from_minutes": 0,
        "to_hour": 17,
        "to_minutes": 0,
        "on_date": datetime(year=2018, month=11, day=27)
    }
    WorkDay.create(**kwargs)
    logger.debug(f"added work day for {teacher}")
    resp = requester.post("/lessons/",
                          json={'date': date, "meetup": "test", "dropoff": "test"})
    assert 'not available' in resp.json['message']


def test_teacher_new_lesson(auth, teacher, student, requester):
    auth.login(email=teacher.user.email)
    date = "2018-11-27T13:00Z"
    resp = requester.post("/lessons/",
                          json={'date': date, "meetup": "test", "dropoff": "test"})
    assert 'successfully' in resp.json['message']
    assert resp.json['data']['is_approved']


def test_delete_lesson(auth, teacher, student, requester):
    auth.login(email=student.user.email)
    lesson = Lesson.create(teacher_id=teacher.id, student_id=student.id,
                           creator_id=student.user.id, duration=40, date=datetime.now(),
                           meetup="test", dropoff="test")
    resp = requester.delete(f"/lessons/{lesson.id}")
    assert "successfully" in resp.json['message']


def test_approve_lesson(auth, teacher, student, requester):
    auth.login(email=teacher.user.email)
    lesson = Lesson.create(teacher_id=teacher.id, student_id=student.id,
                           creator_id=teacher.user.id, duration=40, date=datetime.now(),
                           meetup="test", dropoff="test")
    resp = requester.get(f"/lessons/{lesson.id}/approve")
    assert "approved" in resp.json['message']
    resp = requester.get(f"/lessons/7/approve")
    assert "not exist" in resp.json['message']
    assert lesson.is_approved


def test_user_edit_lesson(app, auth, student, teacher, requester):
    """ test that is_approved turns false when user edits lesson"""
    auth.login(email=student.user.email)
    lesson = Lesson.create(teacher_id=teacher.id, student_id=student.id,
                           creator_id=student.user.id, duration=40, date=datetime.now(),
                           meetup="test", dropoff="test")
    resp = requester.post(f"/lessons/{lesson.id}",
                          json={'meetup': 'nowhere'})
    assert 'successfully' in resp.json['message']
    assert not resp.json['data']['is_approved']
