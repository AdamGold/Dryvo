from datetime import datetime, timedelta

from flask_sqlalchemy import BaseQuery

from server.api.database.models import (
    Lesson,
    Student,
    LessonTopic,
    Place,
    PlaceType,
    Topic,
    Payment,
)
from server.consts import DATE_FORMAT


def new_lesson(requester, date, student):
    return requester.post(
        "/lessons/",
        json={
            "date": date,
            "student_id": student.id,
            "meetup_place": "test",
            "dropoff_place": "test",
        },
    )


def new_topics(requester, topics, lesson_id):
    return requester.post(f"/lessons/{lesson_id}/topics", json={"topics": topics})


def test_commons(teacher, student, meetup, dropoff):
    """add 3 lessons, 2 of them with same meetup
    and dropoff. check returns of common_meetup
    and common_dropoff"""
    for _ in range(2):
        Lesson.create(
            teacher=teacher,
            student=student,
            creator=teacher.user,
            duration=40,
            date=datetime.utcnow(),
            meetup_place=meetup,
            dropoff_place=dropoff,
        )

    second_meetup = Place.create(
        name="other", used_as=PlaceType.meetup.value, student=student
    )
    second_dropoff = Place.create(
        name="other", used_as=PlaceType.dropoff.value, student=student
    )

    Lesson.create(
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


def test_new_lesson_number(teacher, student, meetup, dropoff):
    """create new lesson for student,
    check new_lesson_number updates"""
    old_lesson_number = student.new_lesson_number
    lesson = Lesson.create(
        teacher=teacher,
        student=student,
        creator=teacher.user,
        duration=40,
        date=datetime.utcnow(),
        meetup_place=meetup,
        dropoff_place=dropoff,
    )
    assert student.new_lesson_number == old_lesson_number + 1
    assert student.new_lesson_number == lesson.lesson_number + 1
    old_lesson_number = student.new_lesson_number
    Lesson.create(
        teacher=teacher,
        student=student,
        creator=teacher.user,
        duration=40,
        date=datetime.utcnow() + timedelta(hours=20),
        meetup_place=meetup,
        dropoff_place=dropoff,
    )
    assert student.new_lesson_number == old_lesson_number


def test_filter_topics(teacher, student, meetup, dropoff, topic, lesson):
    """make topic in-progress and check. then make it finished
    and check again"""
    topic2 = Topic.create(title="aa", min_lesson_number=3, max_lesson_number=5)
    lesson_topic = LessonTopic(is_finished=False, topic_id=topic.id)
    lesson.topics.append(lesson_topic)
    assert topic in student.topics(is_finished=False)

    # let's create another lesson with same topic
    lesson = Lesson.create(
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
    lesson = Lesson.create(
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
    lesson = Lesson.create(
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

    lesson = Lesson.create(
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
    # we have one lesson currently and 0 payments
    assert student.balance == -teacher.price
    lesson = Lesson.create(
        teacher=teacher,
        student=student,
        creator=teacher.user,
        duration=40,
        date=datetime.utcnow(),
        meetup_place=meetup,
        dropoff_place=dropoff,
        is_approved=True,
    )
    assert student.balance < -teacher.price
    lesson.update(is_approved=False)
    assert student.balance == -teacher.price

    st = Student.query.filter(Student.balance == -teacher.price).first()
    assert st == student
    Payment.create(amount=teacher.price, teacher=teacher, student=student)
    assert student.balance == 0
    st = Student.query.filter(Student.balance == 0).first()
    assert st == student


def test_total_paid(teacher, student):
    Payment.create(amount=teacher.price, teacher=teacher, student=student)
    st = Student.query.filter(Student.total_paid == teacher.price).first()
    assert st == student


def test_total_lessons_price(teacher, student, lesson):
    st = Student.query.filter(Student.total_lessons_price == teacher.price).first()
    assert st == student


def test_approve(auth, requester, student, teacher):
    auth.login(email=teacher.user.email)
    resp = requester.get(f"/student/{student.id}/approve")
    assert "Not authorized." == resp.json["message"]
    auth.login(email=student.user.email)
    resp = requester.get(f"/student/{student.id}/approve")
    assert resp.json["data"]["is_approved"]


def test_deactivate(auth, requester, student, teacher):
    auth.login(email=teacher.user.email)
    resp = requester.get(f"/student/{student.id}/deactivate")
    assert not resp.json["data"]["is_active"]

