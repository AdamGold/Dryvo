from server.api.blueprints import user
from server.api.database.models import WorkDay, Lesson
from server.consts import DATE_FORMAT

import pytest
from datetime import datetime, timedelta


def test_work_days(teacher, auth, requester):
    auth.login(email=teacher.user.email)
    resp = requester.get("/teacher/work_days").json
    assert isinstance(resp['data'], list)
    assert 'next_url' in resp
    assert 'prev_url' in resp


def test_add_work_day(teacher, auth, requester):
    auth.login(email=teacher.user.email)
    data = {
        "day": "tuesday",
        "from_hour": 13,
        "from_minutes": 0,
        "to_hour": 17,
        "to_minutes": 0,
        "on_date": "2018-11-27"
    }
    resp = requester.post("/teacher/work_days", json=data)
    assert "Day created" in resp.json['message']
    assert resp.json['data']
    assert resp.status_code == 201
    assert WorkDay.query.first().from_hour == data['from_hour']


def test_add_work_day_invalid_values(teacher, auth, requester):
    auth.login(email=teacher.user.email)
    data = {
        "day": "tuesday",
        "from_hour": 20,
        "from_minutes": 0,
        "to_hour": 19,
        "to_minutes": 0,
        "on_date": "2018-11-27"
    }
    resp = requester.post("/teacher/work_days", json=data)
    assert "difference" in resp.json['message']


def test_delete_work_day(teacher, auth, requester):
    auth.login(email=teacher.user.email)
    kwargs = {
        "teacher_id": 1,
        "day": 1,
        "from_hour": 13,
        "from_minutes": 0,
        "to_hour": 17,
        "to_minutes": 0
    }
    day = WorkDay.create(**kwargs)
    resp = requester.delete(f"/teacher/work_days/{day.id}")
    assert "Day deleted" in resp.json['message']
    resp = requester.delete("/teacher/work_days/8")
    assert "not exist" in resp.json['message']


def test_available_hours_route(teacher, student, auth, requester):
    auth.login(email=teacher.user.email)
    date = "2018-11-27"
    time_and_date = date + "T13:30Z"
    data = {
        "day": "tuesday",
        "from_hour": 13,
        "from_minutes": 0,
        "to_hour": 17,
        "to_minutes": 0,
        "on_date": date
    }
    requester.post("/teacher/work_days", json=data)  # we add a day
    # now let's add a lesson
    Lesson.create(teacher_id=teacher.id, student_id=student.id,
                  creator_id=teacher.user.id, duration=40,
                  date=datetime.strptime(time_and_date, DATE_FORMAT),
                  meetup='test', dropoff='test')
    resp = requester.post(f"/teacher/{teacher.id}/available_hours",
                          json={'date': date})
    assert isinstance(resp.json['data'], list)
    assert "14:10" in resp.json['data'][0][0]


def test_teacher_available_hours(auth, teacher, student, requester):
    date = "2018-11-27"
    time_and_date = date + "T13:30Z"
    kwargs = {
        "teacher_id": teacher.id,
        "day": 1,
        "from_hour": 13,
        "from_minutes": 30,
        "to_hour": 17,
        "to_minutes": 0,
        "on_date": datetime(year=2018, month=11, day=27)
    }
    WorkDay.create(**kwargs)
    req_day = datetime.strptime(time_and_date, DATE_FORMAT)
    assert next(teacher.available_hours(
        req_day))[0] == req_day
