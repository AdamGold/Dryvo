from datetime import datetime, timedelta

from server.api.database.models import Lesson, Place, PlaceType, Stage, Topic
from server.consts import DATE_FORMAT


def test_commons(teacher, student, meetup, dropoff):
    """add 3 lessons, 2 of them with same meetup
    and dropoff. check returns of common_meetup
    and common_dropoff"""
    for _ in range(2):
        Lesson.create(teacher_id=teacher.id, student_id=student.id,
                      creator_id=teacher.user_id, duration=40, date=datetime.now(),
                      meetup_place=meetup, dropoff_place=dropoff)

    second_meetup = Place.create(name="other", used_as=PlaceType.meetup.value,
                                 student=student)
    second_dropoff = Place.create(name="other", used_as=PlaceType.dropoff.value,
                                  student=student)

    Lesson.create(teacher_id=teacher.id, student_id=student.id,
                  creator_id=teacher.user_id, duration=40, date=datetime.now(),
                  meetup_place=second_meetup, dropoff_place=second_dropoff)
    assert student.common_meetup == meetup
    assert student.common_dropoff == dropoff


def test_stages(auth, requester, student, stage: Stage):
    auth.login()
    resp = requester.get(f"/student/{student.id}/stages")
    assert isinstance(resp.json['data'], list)
    assert 'next_url' in resp.json
    assert 'prev_url' in resp.json


def test_invalid_edit_topic(auth, requester, student, stage: Stage):
    """ Send wrong topic & a topic where no lesson
    has been done and expect error"""
    auth.login()
    resp = requester.post(f"/student/{student.id}/topics/5")
    assert "Topic does not exist" in resp.json["message"]
    topic = Topic.create(stage=stage, title="test")
    resp = requester.post(f"/student/{student.id}/topics/{topic.id}")
    assert "No lesson has been done" in resp.json["message"]


def test_edit_topic():
    pass
