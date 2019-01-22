from datetime import datetime, timedelta

from server.api.database.models import Lesson, Place, PlaceType
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
