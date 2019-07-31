import os
from datetime import datetime, timedelta

import pytest
from flask_sqlalchemy import BaseQuery

from server.api.database.models import (
    Appointment,
    LessonTopic,
    Payment,
    Place,
    PlaceType,
    Student,
    Topic,
    User,
)
from server.consts import DATE_FORMAT


def new_lesson(requester, date, student):
    return requester.post(
        "/appointments/",
        json={
            "date": date,
            "student_id": student.id,
            "meetup_place": "test",
            "dropoff_place": "test",
        },
    )


def new_topics(requester, topics, lesson_id):
    return requester.post(f"/appointments/{lesson_id}/topics", json={"topics": topics})


def test_commons(teacher, student, meetup, dropoff):
    """add 3 lessons, 2 of them with same meetup
    and dropoff. check returns of common_meetup
    and common_dropoff"""
    for _ in range(2):
        Appointment.create(
            teacher=teacher,
            student=student,
            creator=teacher.user,
            duration=40,
            date=datetime.utcnow(),
            meetup_place=meetup,
            dropoff_place=dropoff,
        )

    second_meetup = Place.create(
        description="other", used_as=PlaceType.meetup.value, student=student
    )
    second_dropoff = Place.create(
        description="other", used_as=PlaceType.dropoff.value, student=student
    )

    Appointment.create(
        teacher=teacher,
        student=student,
        creator=teacher.user,
        duration=40,
        date=datetime.utcnow(),
        meetup_place=second_meetup,
        dropoff_place=second_dropoff,
    )
    assert student.common_meetup == meetup
    assert student.common_dropoff == dropoff


def test_topics(auth, requester, teacher, student, topic):
    """create lesson with topic in progress and make sure
    the response from topics include it in progress"""
    auth.login(email=teacher.user.email)
    date = (
        (datetime.utcnow() + timedelta(days=1)).replace(hour=13, minute=00)
    ).strftime(DATE_FORMAT)
    resp = new_lesson(requester, date, student)
    new_topics(
        requester, {"progress": [topic.id], "finished": []}, resp.json["data"]["id"]
    )
    resp = requester.get(f"/student/{student.id}/topics")
    assert len(resp.json["data"]["new"]) == 0
    assert topic.title == resp.json["data"]["in_progress"][0]["title"]


def test_lessons_done(teacher, student, meetup, dropoff):
    """create new lesson for student,
    check lessons_done updates"""
    old_lesson_number = student.lessons_done
    lesson = Appointment.create(
        teacher=teacher,
        student=student,
        creator=teacher.user,
        duration=60,
        date=datetime.utcnow(),
        meetup_place=meetup,
        dropoff_place=dropoff,
    )
    assert student.lessons_done == old_lesson_number + 60 / teacher.lesson_duration
    assert student.lessons_done == lesson.lesson_number
    old_lesson_number = student.lessons_done
    Appointment.create(
        teacher=teacher,
        student=student,
        creator=teacher.user,
        duration=40,
        date=datetime.utcnow() + timedelta(hours=20),
        meetup_place=meetup,
        dropoff_place=dropoff,
    )
    assert (
        student.lessons_done == old_lesson_number
    )  # because it's later than now, it hasn't changed

    st = Student.query.filter(Student.lessons_done == old_lesson_number).first()
    assert st.id == student.id


def test_filter_topics(teacher, student, meetup, dropoff, topic, lesson):
    """make topic in-progress and check. then make it finished
    and check again"""
    topic2 = Topic.create(title="aa", min_lesson_number=3, max_lesson_number=5)
    lesson_topic = LessonTopic(is_finished=False, topic_id=topic.id)
    lesson.topics.append(lesson_topic)
    assert topic in student.topics(is_finished=False)

    # let's create another lesson with same topic
    lesson = Appointment.create(
        teacher=teacher,
        student=student,
        creator=teacher.user,
        duration=40,
        date=datetime.utcnow(),
        meetup_place=meetup,
        dropoff_place=dropoff,
    )
    lesson_topic = LessonTopic(is_finished=True, topic_id=topic.id)
    lesson.topics.append(lesson_topic)
    lesson_topic2 = LessonTopic(is_finished=False, topic_id=topic2.id)
    lesson.topics.append(lesson_topic2)
    assert topic in student.topics(is_finished=True)
    assert topic2 in student.topics(is_finished=False)


def test_lesson_topics(teacher, student, topic, meetup, dropoff):
    lesson = Appointment.create(
        teacher=teacher,
        student=student,
        creator=teacher.user,
        duration=40,
        date=datetime.utcnow(),
        meetup_place=meetup,
        dropoff_place=dropoff,
    )
    lesson_topic = LessonTopic(is_finished=False, topic_id=topic.id)
    lesson.topics.append(lesson_topic)
    lt = student._lesson_topics(is_finished=False)
    assert lesson_topic in lt
    assert isinstance(lt, BaseQuery)


def test_topics_in_progress(teacher, student, topic, meetup, dropoff, lesson):
    lesson_topic = LessonTopic(is_finished=False, topic_id=topic.id)
    lesson.topics.append(lesson_topic)
    lesson = Appointment.create(
        teacher=teacher,
        student=student,
        creator=teacher.user,
        duration=40,
        date=datetime.utcnow(),
        meetup_place=meetup,
        dropoff_place=dropoff,
    )
    lesson_topic = LessonTopic(is_finished=False, topic_id=topic.id)
    lesson.topics.append(lesson_topic)

    lt = student._lesson_topics(is_finished=False)
    in_progress = student._topics_in_progress(lt)
    assert topic in in_progress

    lesson = Appointment.create(
        teacher=teacher,
        student=student,
        creator=teacher.user,
        duration=40,
        date=datetime.utcnow(),
        meetup_place=meetup,
        dropoff_place=dropoff,
    )
    lesson_topic = LessonTopic(is_finished=True, topic_id=topic.id)
    lesson.topics.append(lesson_topic)
    lt = student._lesson_topics(is_finished=False)
    in_progress = student._topics_in_progress(lt)
    assert len(in_progress) == 0


def test_balance(teacher, student, meetup, dropoff):
    # we have one lesson currently and 0 payments, but the lesson hasn't yet happened
    assert student.balance == 0
    lesson = Appointment.create(
        teacher=teacher,
        student=student,
        creator=teacher.user,
        duration=40,
        date=datetime.utcnow() - timedelta(hours=2),
        meetup_place=meetup,
        dropoff_place=dropoff,
        is_approved=True,
    )
    assert student.balance == -teacher.price
    lesson.update(is_approved=False)
    assert student.balance == 0

    st = Student.query.filter(Student.balance == 0).first()
    assert st == student
    Payment.create(amount=teacher.price, teacher=teacher, student=student)
    assert student.balance == teacher.price


def test_total_paid(teacher, student):
    Payment.create(amount=teacher.price, teacher=teacher, student=student)
    st = Student.query.filter(Student.total_paid == teacher.price).first()
    assert st == student


def test_total_lessons_price(teacher, student, meetup, dropoff):
    st = Student.query.filter(
        Student.total_lessons_price == 0
    ).first()  # no lesson has been done yet
    assert st == student
    Appointment.create(
        teacher=teacher,
        student=student,
        creator=teacher.user,
        duration=40,
        date=datetime.utcnow() - timedelta(hours=2),
        meetup_place=meetup,
        dropoff_place=dropoff,
        is_approved=True,
    )
    st = Student.query.filter(Student.total_lessons_price == teacher.price).first()
    assert st == student

    student.update(price=1000)
    # this is still true because lessons have a fixed price once scheduled
    assert student.total_lessons_price == teacher.price

    Appointment.create(
        teacher=teacher,
        student=student,
        creator=teacher.user,
        duration=40,
        date=datetime.utcnow() - timedelta(hours=2),
        meetup_place=meetup,
        dropoff_place=dropoff,
        is_approved=True,
    )
    assert student.total_lessons_price == teacher.price + student.price


def test_total_lessons_price_with_different_prices(teacher, student, meetup, dropoff):
    st = Student.query.filter(
        Student.total_lessons_price == 0
    ).first()  # no lesson has been done yet
    assert st == student
    price = 100
    prices = price
    for x in range(3):
        Appointment.create(
            teacher=teacher,
            student=student,
            creator=teacher.user,
            duration=40,
            date=datetime.utcnow() - timedelta(hours=x),
            meetup_place=meetup,
            dropoff_place=dropoff,
            is_approved=True,
            price=price * x,
        )
        prices += price * x

    assert student.total_lessons_price == prices
    st = Student.query.filter(Student.total_lessons_price == prices).first()
    assert st == student


def test_approve(auth, requester, student, teacher):
    auth.login(email=teacher.user.email)
    resp = requester.get(f"/student/{student.id}/approve")
    assert "Not authorized." == resp.json["message"]
    auth.login(email=student.user.email)
    resp = requester.get(f"/student/{student.id}/approve")
    assert resp.json["data"]["is_approved"]


def test_delete_student(auth, requester, student, teacher):
    auth.login(email=teacher.user.email)
    resp = requester.delete(f"/student/{student.id}")
    assert "Can't delete" in resp.json["message"]
    student_user = User.create(
        email="aa@test.com", password="test", name="student", area="test"
    )
    new_student = Student.create(
        user=student_user, teacher=teacher, creator=teacher.user, is_approved=True
    )
    resp = requester.delete(f"/student/{new_student.id}")
    assert "deleted" in resp.json["message"]


def test_deactivate(auth, requester, student, teacher):
    auth.login(email=teacher.user.email)
    resp = requester.get(f"/student/{student.id}/deactivate")
    assert not resp.json["data"]["is_active"]


def test_edit_student(auth, requester, teacher, student):
    auth.login(email=teacher.user.email)
    resp = requester.post(
        f"/student/{student.id}",
        data={
            "theory": "true",
            "price": "1000",
            "number_of_old_lessons": 10,
            "doctor_check": "true",
        },
    )
    assert not resp.json["data"]["eyes_check"]
    assert resp.json["data"]["theory"]
    assert resp.json["data"]["price"] == 1000
    auth.login(email=student.user.email)
    resp = requester.post(
        f"/student/{student.id}", data={"theory": "false", "eyes_check": "true"}
    )
    assert resp.json["data"]["theory"]
    assert resp.json["data"]["eyes_check"]


def test_not_authorized_edit_student(auth, requester, student, admin):
    auth.login(email=admin.email)
    resp = requester.post(
        f"/student/{student.id}",
        data={"theory": "true", "number_of_old_lessons": 10, "doctor_check": "true"},
    )
    assert "authorized" in resp.json["message"]


@pytest.mark.skip
def test_upload_green_form(teacher, auth, requester, student):
    """skip this one so we won't upload an image to cloudinary
    on each tests - the test passes though"""
    auth.login(email=teacher.user.email)
    image = os.path.join("./tests/assets/av.png")
    file = (image, "av.png")
    resp = requester.post(
        f"/student/{student.id}",
        data={"green_form": file},
        content_type="multipart/form-data",
    )
    assert requester.get(resp.json["data"]["green_form"])


def test_number_of_old_lessons(auth, requester, student, teacher):
    old_lesson_number = student.lessons_done
    old_balance = student.balance
    student.update(number_of_old_lessons=40)
    assert student.lessons_done == old_lesson_number + 40
    assert student.balance == old_balance - 40 * teacher.price
