import flask
from flask import Blueprint
from flask_login import current_user, login_required, logout_user
from functools import wraps
from datetime import datetime

from server.api.database.consts import LESSONS_PER_PAGE, DAYS_PER_PAGE
from server.api.utils import jsonify_response, paginate
from server.error_handling import RouteError
from server.api.database.models import Topic, Student, Lesson
from server.api.blueprints.teacher import teacher_required

student_routes = Blueprint("student", __name__, url_prefix="/student")


def init_app(app):
    app.register_blueprint(student_routes)


@student_routes.route("/<int:student_id>/topics", methods=["GET"])
@jsonify_response
@login_required
def topics(student_id: int):
    """show topics by: finished, unfinished or haven't started"""
    student = Student.get_by_id(student_id)
    if not student:
        raise RouteError("Student does not exist.")
    finished_topics = [topic.to_dict() for topic in student.filter_topics(
        is_finished=True)]
    in_progress_topics = [topic.to_dict() for topic in student.filter_topics(
        is_finished=False)]
    new_topics = [topic.to_dict() for topic in Topic.query.all(
    ) if topic.to_dict() not in in_progress_topics and topic.to_dict() not in finished_topics]
    return {
        "data": {
            "finished": finished_topics,
            "in_progress": in_progress_topics,
            "new": new_topics,
        }
    }


@student_routes.route("/<int:student_id>/new_lesson_topics", methods=["GET"])
@jsonify_response
@teacher_required
def new_lesson_topics(student_id: int):
    """return possible topics for next lesson (without duplicates):
    { Lesson.topics_for_lesson + student.in progress topics }"""
    student = Student.get_by_id(student_id)
    if not student:
        raise RouteError("Student does not exist.")
    topics_for_lesson = set(Lesson.topics_for_lesson(
        student.new_lesson_number)) - set(student.filter_topics(is_finished=True))
    in_progress_topics = student.filter_topics(is_finished=False)
    non_duplicates = (list(topics_for_lesson) +
                      list(set(in_progress_topics) - topics_for_lesson))
    return {"data": [topic.to_dict() for topic in non_duplicates]}
