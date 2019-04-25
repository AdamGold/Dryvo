from datetime import datetime, timedelta, date

import pytest

from server.api.blueprints import user
from server.api.database.models import (
    Lesson,
    Student,
    User,
    WorkDay,
    Payment,
    Teacher,
    PaymentType,
)
from server.consts import DATE_FORMAT, WORKDAY_DATE_FORMAT


def test_teachers(auth, teacher, requester):
    new_user = User.create(
        email="a@a.c", password="huh", name="absolutely", area="nope"
    )
    new_teacher = Teacher.create(
        user=new_user, is_approved=True, price=100, lesson_duration=40
    )
    auth.login()
    resp = requester.get("/teacher/")
    first_length = len(resp.json["data"])
    assert resp.json["data"][1]["teacher_id"] == new_teacher.id
    resp = requester.get("/teacher/?order_by=created_at desc")
    assert resp.json["data"][0]["teacher_id"] == new_teacher.id
    resp = requester.get("/teacher/?name=solut")
    assert resp.json["data"][0]["teacher_id"] == new_teacher.id
    resp = requester.get("/teacher/?name=le:no way")
    assert not resp.json["data"]
    resp = requester.get("/teacher/?limit=1")
    assert len(resp.json["data"]) == 1
    new_teacher.is_approved = False
    resp = requester.get("/teacher/")
    assert len(resp.json["data"]) == first_length - 1


def test_work_days(teacher, auth, requester):
    date = datetime.utcnow() + timedelta(hours=10)
    first_kwargs_hour = 13
    kwargs = {
        "teacher": teacher,
        "day": 1,
        "from_hour": first_kwargs_hour,
        "from_minutes": 0,
        "to_hour": 17,
        "to_minutes": 0,
        "on_date": date,
    }
    day1 = WorkDay.create(**kwargs)
    kwargs.pop("on_date")
    kwargs["from_hour"] = 15
    day2 = WorkDay.create(**kwargs)
    auth.login(email=teacher.user.email)
    resp = requester.get("/teacher/work_days").json
    assert resp["data"][0]["from_hour"] == kwargs["from_hour"]
    day = date.date()
    resp = requester.get(f"/teacher/work_days?on_date=eq:{day}").json
    assert resp["data"][0]["from_hour"] == first_kwargs_hour


def test_update_work_days(teacher, auth, requester):
    auth.login(email=teacher.user.email)
    # update normal work days
    data = {
        0: [{"from_hour": "23", "from_minutes": 0, "to_hour": "24", "to_minutes": 0}]
    }
    resp = requester.post("/teacher/work_days", json=data)
    assert resp.status_code == 200
    assert WorkDay.query.filter_by(from_hour=23).first().day.value == 0
    # check everything older gets deleted
    data = {0: [{"from_hour": 11, "from_minutes": 0, "to_hour": 12, "to_minutes": 0}]}
    resp = requester.post("/teacher/work_days", json=data)
    assert resp.status_code == 200
    assert not WorkDay.query.filter_by(day=0).filter_by(from_hour=23).first()
    # update specific work days
    data = {
        "2018-11-27": [
            {"from_hour": 1, "from_minutes": 0, "to_hour": 2, "to_minutes": 0}
        ]
    }
    resp = requester.post("/teacher/work_days", json=data)
    assert resp.status_code == 200
    assert WorkDay.query.filter_by(from_hour=1).first().on_date == date(2018, 11, 27)


def test_add_work_day_invalid_values(teacher, auth, requester):
    auth.login(email=teacher.user.email)
    # to_hour smaller than from_hour
    data = {0: [{"from_hour": 24, "from_minutes": 0, "to_hour": 23, "to_minutes": 0}]}
    resp = requester.post("/teacher/work_days", json=data)
    assert resp.status_code == 400


def test_delete_work_day(teacher, auth, requester):
    auth.login(email=teacher.user.email)
    kwargs = {
        "teacher_id": 1,
        "day": 1,
        "from_hour": 13,
        "from_minutes": 0,
        "to_hour": 17,
        "to_minutes": 0,
    }
    day = WorkDay.create(**kwargs)
    resp = requester.delete(f"/teacher/work_days/{day.id}")
    assert "Day deleted" in resp.json["message"]
    resp = requester.delete("/teacher/work_days/8")
    assert "not exist" in resp.json["message"]


def test_available_hours_route(teacher, student, meetup, dropoff, auth, requester):
    auth.login(email=teacher.user.email)
    tomorrow = datetime.utcnow() + timedelta(days=1)
    date = tomorrow.strftime(WORKDAY_DATE_FORMAT)
    time_and_date = date + "T13:30:20.123123Z"
    data = {
        "teacher_id": teacher.id,
        "from_hour": 13,
        "from_minutes": 0,
        "to_hour": 17,
        "to_minutes": 0,
        "on_date": tomorrow,
    }
    WorkDay.create(**data)

    # now let's add a lesson
    lesson = Lesson.create(
        teacher_id=teacher.id,
        student_id=student.id,
        creator_id=teacher.user.id,
        duration=40,
        date=datetime.strptime(time_and_date, DATE_FORMAT),
        meetup_place=meetup,
        dropoff_place=dropoff,
        is_approved=False,
    )
    resp = requester.post(f"/teacher/{teacher.id}/available_hours", json={"date": date})

    assert len(resp.json["data"]) == 6
    lesson.update(is_approved=True)
    resp = requester.post(
        f"/teacher/{teacher.id}/available_hours", json={"date": date, "duration": "100"}
    )
    assert len(resp.json["data"]) == 1

    # if we login as student, we shouldn't see any lesson dates (even non-approved)
    auth.login(email=student.user.email)
    lesson.update(is_approved=False)
    resp = requester.post(f"/teacher/{teacher.id}/available_hours", json={"date": date})
    assert len(resp.json["data"]) == 4


def test_teacher_available_hours(teacher, student, requester, meetup, dropoff):
    tomorrow = datetime.utcnow() + timedelta(days=1)
    kwargs = {
        "teacher_id": teacher.id,
        "day": 1,
        "from_hour": tomorrow.hour,
        "from_minutes": tomorrow.minute,
        "to_hour": 23,
        "to_minutes": 59,
        "on_date": tomorrow,
    }
    WorkDay.create(**kwargs)
    assert next(teacher.available_hours(tomorrow))[0] == tomorrow

    # we create a non approved lesson - available hours should still contain its date
    lesson = Lesson.create(
        teacher_id=teacher.id,
        student_id=student.id,
        creator_id=teacher.user.id,
        duration=teacher.lesson_duration,
        date=tomorrow,
        meetup_place=meetup,
        dropoff_place=dropoff,
        is_approved=False,
    )

    assert next(teacher.available_hours(tomorrow, only_approved=True))[0] == tomorrow
    assert next(teacher.available_hours(tomorrow, only_approved=False))[0] != tomorrow


def test_add_payment(auth, requester, teacher, student):
    auth.login(email=teacher.user.email)
    resp = requester.post(
        "/teacher/add_payment",
        json={
            "amount": teacher.price,
            "student_id": student.id,
            "crn": "1101",
            "payment_type": "cash",
            "details": "test",
        },
    )
    assert resp.json["data"]["amount"] == teacher.price
    assert resp.json["data"]["crn"] == 1101

    resp = requester.post(
        "/teacher/add_payment",
        json={
            "amount": teacher.price,
            "student_id": student.id,
            "payment_type": "asdas",
        },
    )
    assert resp.json["data"]["payment_type"] == "cash"


@pytest.mark.parametrize(
    ("amount, student_id, error"),
    ((None, 1, "Amount must be given."), (100, 10000, "Student does not exist.")),
)
def test_add_invalid_payment(auth, requester, teacher, amount, student_id, error):
    auth.login(email=teacher.user.email)
    resp = requester.post(
        "/teacher/add_payment", json={"amount": amount, "student_id": student_id}
    )
    assert resp.status_code == 400
    assert resp.json["message"] == error


def test_students(auth, teacher, requester):
    new_user = User.create(
        email="a@a.c", password="huh", name="absolutely", area="nope"
    )
    new_student = Student.create(teacher=teacher, creator=teacher.user, user=new_user)
    auth.login(email=teacher.user.email)
    resp = requester.get("/teacher/students?order_by=balance desc")
    assert resp.json["data"][1]["student_id"] == new_student.id
    resp = requester.get("/teacher/students?name=solut")
    assert resp.json["data"][0]["student_id"] == new_student.id
    resp = requester.get("/teacher/students?name=le:no way")
    assert not resp.json["data"]
    resp = requester.get("/teacher/students?limit=1")
    assert len(resp.json["data"]) == 1


def test_edit_data(app, teacher, requester, auth):
    auth.login(email=teacher.user.email)
    resp = requester.post(
        "/teacher/edit_data", json={"price": 200, "lesson_duration": 100}
    )
    assert teacher.lesson_duration == 100
    assert resp.json["data"]["price"] == 200
    assert requester.post("/login/edit_data", json={})
    assert teacher.lesson_duration == 100


def test_approve(auth, admin, requester, teacher):
    auth.login(email=teacher.user.email)
    resp = requester.get(f"/teacher/{teacher.id}/approve")
    assert "Not authorized." == resp.json["message"]
    auth.login(email=admin.email)
    resp = requester.get(f"/teacher/{teacher.id}/approve")
    assert resp.json["data"]["is_approved"]


def test_add_receipt(auth, requester, teacher, student):
    auth.login(email=teacher.user.email)
    payment = Payment.create(
        teacher=teacher,
        amount=teacher.price,
        student=student,
        payment_type=PaymentType.cash,
        details="test",
        crn=1101,
    )
    assert not payment.pdf_link
    requester.get(
        f"/teacher/payments/{payment.id}/receipt",
        json={
            "amount": teacher.price,
            "student_id": student.id,
            "crn": "1101",
            "payment_type": "cash",
            "details": "test",
        },
    )
    assert payment.pdf_link

