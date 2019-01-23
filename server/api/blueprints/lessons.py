import itertools
from datetime import datetime
from typing import Tuple

import flask
from flask import Blueprint
from flask_login import current_user, login_required, logout_user
from loguru import logger

from server.api.blueprints import teacher_required
from server.api.database.consts import LESSONS_PER_PAGE
from server.api.database.models import (Lesson, LessonTopic, Place, PlaceType,
                                        Student, Teacher, Topic, User)
from server.api.push_notifications import FCM
from server.api.utils import jsonify_response, paginate
from server.consts import DATE_FORMAT, DEBUG_MODE
from server.error_handling import RouteError

lessons_routes = Blueprint("lessons", __name__, url_prefix="/lessons")


def init_app(app):
    app.register_blueprint(lessons_routes)


def handle_places(
    meetup_place: str, dropoff_place: str, student: Student
) -> Tuple[Place, Place]:
    if not student:
        return None, None
    return (
        Place.create_or_find(meetup_place, PlaceType.meetup, student),
        Place.create_or_find(dropoff_place, PlaceType.dropoff, student),
    )


def get_lesson_data(data: dict, user: User) -> dict:
    """get request data and a specific user
    - we need the user because we are not decorated in login_required here
    returns dict of new lesson or edited lesson"""
    date = data.get("date")
    if date:
        date = datetime.strptime(date, DATE_FORMAT)
        if date < datetime.now():
            raise RouteError("Date is not valid.")
    if user.student:
        duration = user.student.teacher.lesson_duration
        student = user.student
        if date:
            available_hours = itertools.dropwhile(
                lambda hour_with_date: hour_with_date[0] != date,
                user.student.teacher.available_hours(date),
            )
            try:
                next(available_hours)
            except StopIteration:
                raise RouteError("This hour is not available.")
        teacher = user.student.teacher
    elif user.teacher:
        duration = data.get("duration", user.teacher.lesson_duration)
        teacher = user.teacher
        student = Student.get_by_id(data.get("student_id"))
        if not student and data.get("student_id") is not None:
            raise RouteError("No student with this ID.")

    meetup, dropoff = handle_places(
        data.get("meetup_place"), data.get("dropoff_place"), student
    )
    return {
        "date": date,
        "meetup_place": meetup,
        "dropoff_place": dropoff,
        "student": student,
        "teacher": teacher,
        "duration": duration,
        "comments": data.get("comments"),
        "is_approved": True if user.teacher else False,
    }


@lessons_routes.route("/", methods=["GET"])
@jsonify_response
@login_required
@paginate
def lessons():
    filter_args = flask.request.args
    page = flask.request.args.get("page", 1, type=int)
    user = current_user.teacher
    if not current_user.teacher:
        user = current_user.student

    pagination = user.filter_lessons(filter_args).paginate(
        page, LESSONS_PER_PAGE, False
    )
    return pagination


@lessons_routes.route("/", methods=["POST"])
@jsonify_response
@login_required
def new_lesson():
    data = flask.request.get_json()
    if not data.get("date"):
        raise RouteError("Please insert the date of the lesson.")
    lesson = Lesson.create(**get_lesson_data(data, current_user))

    # send fcm to the user who wasn't the one creating the lesson
    user_to_send_to = lesson.teacher.user
    if lesson.creator == lesson.teacher.user and lesson.student:
        user_to_send_to = lesson.student.user
    if user_to_send_to.firebase_token:
        logger.debug(f"sending fcm to {user_to_send_to}")
        FCM.notify(
            token=user_to_send_to.firebase_token,
            title="New Lesson",
            body=f"New lesson at {lesson.date}",
        )
    return {"data": lesson.to_dict()}, 201


@lessons_routes.route("/<int:lesson_id>/topics", methods=["POST"])
@jsonify_response
@login_required
@teacher_required
def update_topics(lesson_id):
    """update or add lesson topics
    accepts {'progress': [topics in progress], 'finished': [finished topics]}"""
    data = flask.request.get_json()
    FINISHED_KEY = "finished"
    lesson = Lesson.get_by_id(lesson_id)
    if not lesson:
        raise RouteError("Lesson does not exist.")
    if not lesson.student:
        raise RouteError("Lesson must have a student assigned.")
    appended_ids = []
    for key, topic_ids in data.get("topics").items():
        for topic_id in topic_ids:
            if not Topic.get_by_id(topic_id):
                raise RouteError("Invalid topic id.")
            if topic_id in appended_ids:  # we don't want the same topic twice
                continue
            is_finished = True if key == FINISHED_KEY else False
            lesson_topic = LessonTopic(
                is_finished=is_finished, topic_id=topic_id)
            lesson.topics.append(lesson_topic)
            appended_ids.append(topic_id)

    return {"data": lesson.to_dict()}, 201


@lessons_routes.route("/<int:lesson_id>", methods=["DELETE"])
@jsonify_response
@login_required
def delete_lesson(lesson_id):
    try:
        lessons = current_user.teacher.lessons
    except AttributeError:
        lessons = current_user.student.lessons
    lesson = lessons.filter_by(id=lesson_id).first()
    if not lesson:
        raise RouteError("Lesson does not exist.")

    lesson.update(deleted=True)

    user_to_send_to = lesson.teacher.user
    if current_user == lesson.teacher.user:
        user_to_send_to = lesson.student.user
    if user_to_send_to.firebase_token:
        FCM.notify(
            token=user_to_send_to.firebase_token,
            title="Lesson Deleted",
            body=f"The lesson at {lesson.date} has been deleted.",
        )

    return {"message": "Lesson deleted successfully."}


@lessons_routes.route("/<int:lesson_id>", methods=["POST"])
@jsonify_response
@login_required
def update_lesson(lesson_id):
    try:
        lessons = current_user.teacher.lessons
    except AttributeError:
        lessons = current_user.student.lessons
    lesson = lessons.filter_by(id=lesson_id).first()
    if not lesson:
        raise RouteError("Lesson does not exist", 404)
    data = flask.request.get_json()
    lesson.update_only_changed_fields(**get_lesson_data(data, current_user))

    user_to_send_to = lesson.teacher.user
    if current_user == lesson.teacher.user:
        user_to_send_to = lesson.student.user
    if user_to_send_to.firebase_token:
        FCM.notify(
            token=user_to_send_to.firebase_token,
            title="Lesson Updated",
            body=f"Lesson with {lesson.student.user.name} updated to {lesson.date}",
        )

    return {"message": "Lesson updated successfully.", "data": lesson.to_dict()}


@lessons_routes.route("/<int:lesson_id>/approve", methods=["GET"])
@jsonify_response
@login_required
@teacher_required
def approve_lesson(lesson_id):
    lesson = current_user.teacher.lessons.filter_by(id=lesson_id).first()
    if not lesson:
        raise RouteError("Lesson does not exist", 404)
    lesson.update(is_approved=True)

    if lesson.student.user.firebase_token:
        FCM.notify(
            token=lesson.student.user.firebase_token,
            title="Lesson Approved",
            body=f"Lesson at {lesson.date} has been approved!",
        )

    return {"message": "Lesson approved."}
