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
    Report,
)
from server.consts import DATE_FORMAT, WORKDAY_DATE_FORMAT


def test_teachers(auth, teacher, requester):
    new_user = User.create(
        email="a@a.c", password="huh", name="absolutely", area="nope"
    )
    new_teacher = Teacher.create(
        user=new_user, is_approved=True, price=100, lesson_duration=40, crn=1
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
    auth.login(email=teacher.user.email)
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
    resp = requester.get("/teacher/work_days").json
    assert resp["data"][0]["from_hour"] == kwargs["from_hour"]
    day = date.date()
    resp = requester.get(f"/teacher/work_days?on_date=eq:{day}").json
    assert resp["data"][0]["from_hour"] == first_kwargs_hour

    resp = requester.get(f"/teacher/work_days?day=1").json
    assert resp["data"][0]["from_hour"] == kwargs["from_hour"]


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
        teacher=teacher,
        student=student,
        creator=teacher.user,
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
        teacher=teacher,
        student=student,
        creator=teacher.user,
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
            "details": "test",
        },
    )
    assert resp.json["data"]["payment_type"] == "cash"


@pytest.mark.parametrize(
    ("amount", "details", "student_id", "error"),
    (
        (None, "test", 1, "Amount must not be empty."),
        (100, "test", 10000, "Student does not exist."),
        (100, "", 1, "Details must not be empty."),
    ),
)
def test_add_invalid_payment(
    auth, requester, teacher, amount, details, student_id, error
):
    auth.login(email=teacher.user.email)
    resp = requester.post(
        "/teacher/add_payment",
        json={"amount": amount, "details": details, "student_id": student_id},
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


@pytest.mark.skip
def test_ezcount_create_user(auth, requester, teacher):
    auth.login(email=teacher.user.email)
    resp = requester.get("/teacher/ezcount_user")
    assert "already has" in resp.json["message"]
    auth.logout()

    new_user = User.create(
        email="a@a.c", password="huh", name="absolutely", area="nope"
    )
    new_teacher = Teacher.create(
        user=new_user, is_approved=True, price=100, lesson_duration=40, crn=999999999
    )
    auth.login(email=new_teacher.user.email, password="huh")
    resp = requester.get("/teacher/ezcount_user")
    assert "successfully" in resp.json["message"]


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
    requester.get(f"/teacher/payments/{payment.id}/receipt")
    assert payment.pdf_link


def test_invalid_add_receipt(auth, requester, student, teacher):
    auth.login(email=teacher.user.email)
    resp = requester.get("/teacher/payments/1000/receipt")
    assert resp.status_code == 404
    auth.logout()
    new_user = User.create(
        email="a@a.c", password="huh", name="absolutely", area="nope"
    )
    new_teacher = Teacher.create(
        user=new_user, is_approved=True, price=100, lesson_duration=40, crn=999999999
    )
    auth.login(email=new_user.email, password="huh")
    payment = Payment.create(
        teacher=new_teacher,
        amount=new_teacher.price,
        student=student,
        payment_type=PaymentType.cash,
        details="test",
        crn=1101,
    )
    resp = requester.get(f"/teacher/payments/{payment.id}/receipt")
    assert "does not have an invoice account" in resp.json["message"]


def test_login_to_ezcount(auth, requester, teacher):
    auth.login(email=teacher.user.email)
    resp = requester.get("/teacher/ezcount?redirect=backoffice/expenses")
    assert resp.json["url"]


def test_invalid_login_to_ezcount(auth, requester):
    new_user = User.create(
        email="a@a.c", password="huh", name="absolutely", area="nope"
    )
    new_teacher = Teacher.create(
        user=new_user, is_approved=True, price=100, lesson_duration=40, crn=999999999
    )
    auth.login(email=new_user.email, password="huh")
    resp = requester.get("/teacher/ezcount?redirect=backoffice/expenses")
    assert "does not have an invoice account" in resp.json["message"]


@pytest.mark.parametrize(
    ("report_type", "since", "until"),
    (("lessons", "2019-05-01", "2019-05-30"), ("students", None, None)),
)
def test_create_report(auth, requester, teacher, report_type, since, until):
    auth.login(email=teacher.user.email)
    resp = requester.post(
        "/teacher/reports",
        json={"report_type": report_type, "since": since, "until": until},
    )
    assert resp.json["data"]["uuid"]
    saved_report = Report.query.filter_by(uuid=resp.json["data"]["uuid"]).first()
    assert saved_report.report_type.name == report_type


@pytest.mark.parametrize(
    ("report_type", "since", "until", "error"),
    (
        ("lessons", None, None, "Dates are not valid."),
        ("asds", None, None, "type was not found"),
        ("lessons", "2019-051", "2019-05-30", "Dates are not valid."),
    ),
)
def test_invalid_create_report(
    auth, requester, teacher, report_type, since, until, error
):
    auth.login(email=teacher.user.email)
    resp = requester.post(
        "/teacher/reports",
        json={"report_type": report_type, "since": since, "until": until},
    )
    assert error in resp.json["message"]


def test_create_bot_student(auth, requester, teacher):
    auth.login(email=teacher.user.email)
    student = {"name": "test", "email": "tt@ta.com", "phone": "05444444", "price": 120}
    resp = requester.post(f"/teacher/create_student", json=student)
    assert resp.json["data"]["my_teacher"]["teacher_id"] == teacher.id
    assert resp.json["data"]["price"] == 120


@pytest.mark.parametrize(
    ("name", "email", "phone"),
    (("", "t@ttt.com", "0511111"), ("test", "", "0511111"), ("test", "t@ttt.com", "")),
)
def test_invalid_create_bot_student(auth, requester, teacher, name, email, phone):
    auth.login(email=teacher.user.email)
    student = {"name": name, "email": email, "phone": phone, "price": 100}
    resp = requester.post(f"/teacher/create_student", json=student)
    assert "is required" in resp.json["message"]

