from server.api.blueprints import user
from server.api.database.models import WorkDay, Lesson
from server.consts import DATE_FORMAT, WORKDAY_DATE_FORMAT

import pytest
from datetime import datetime, timedelta


def test_work_days(teacher, auth, requester):
    date = datetime.now() + timedelta(hours=10)
    first_kwargs_hour = 13
    kwargs = {
        "teacher_id": teacher.id,
        "day": 1,
        "from_hour": first_kwargs_hour,
        "from_minutes": 0,
        "to_hour": 17,
        "to_minutes": 0,
        "on_date": date
    }
    day1 = WorkDay.create(**kwargs)
    kwargs.pop("on_date")
    kwargs["from_hour"] = 15
    day2 = WorkDay.create(**kwargs)
    auth.login(email=teacher.user.email)
    resp = requester.get("/teacher/work_days").json
    assert resp["data"][0]["from_hour"] == kwargs["from_hour"]
    day = datetime.strptime("2019-02-20", WORKDAY_DATE_FORMAT).date()
    resp = requester.get(
        f"/teacher/work_days?on_date={day}").json
    assert resp["data"][0]["from_hour"] == first_kwargs_hour


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
    assert WorkDay.query.filter_by(
        from_hour=13).first().from_hour == data['from_hour']


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


def test_available_hours_route(teacher, student, meetup, dropoff, auth, requester):
    auth.login(email=teacher.user.email)
    date = "2018-11-27"
    time_and_date = date + "T13:30:20.123123Z"
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
                  meetup_place=meetup, dropoff_place=dropoff)
    resp = requester.post(f"/teacher/{teacher.id}/available_hours",
                          json={'date': date})
    assert isinstance(resp.json['data'], list)
    assert "14:10" in resp.json['data'][0][0]


def test_teacher_available_hours(teacher, student, requester):
    date = "2018-11-27"
    time_and_date = date + "T13:30:20.123123Z"
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


def test_add_payment(auth, requester, teacher, student):
    auth.login(email=teacher.user.email)
    resp = requester.post("/teacher/add_payment",
                          json={"amount": teacher.price, "student_id": student.id})
    assert resp.json["data"]["amount"] == teacher.price


@pytest.mark.parametrize(
    ('amount, student_id, error'),
    (
        (None, 1, "Amount must be given."),
        (100, 10000, "Student does not exist."),
    ),
)
def test_add_invalid_payment(auth, requester, teacher, amount, student_id, error):
    auth.login(email=teacher.user.email)
    resp = requester.post("/teacher/add_payment",
                          json={"amount": amount, "student_id": student_id})
    assert resp.status_code == 400
    assert resp.json["message"] == error
