import flask
from flask import Blueprint
from flask_login import current_user, login_required, logout_user
from datetime import datetime
from loguru import logger

from server.api.database.consts import LESSONS_PER_PAGE
from server.api.utils import jsonify_response, paginate
from server.error_handling import RouteError
from server.api.database.models import Teacher, Lesson, Student
from server.consts import DATE_FORMAT, DEBUG_MODE
from server.api.blueprints import teacher_required


lessons_routes = Blueprint("lessons", __name__, url_prefix="/lessons")


def init_app(app):
    app.register_blueprint(lessons_routes)


def get_lesson_data():
    data = flask.request.get_json()
    date = data.get("date")
    if date:
        date = datetime.strptime(date, DATE_FORMAT)
        if date < datetime.now() and not DEBUG_MODE:
            raise RouteError("Date is not valid.")

    if current_user.student:
        duration = current_user.student.teacher.lesson_duration
        student_id = current_user.student.id
        if date:
            logger.debug(f"Available hours for teacher {current_user.student.teacher.id} "
                         f"in date {date}:"
                         f"{current_user.student.teacher.available_hours(date)}"
                         )
            flag = False
            for lesson_tuple in current_user.student.teacher.available_hours(date):
                if lesson_tuple[0] == date:
                    flag = True
            if not flag:
                raise RouteError("This hour is not available.")
        teacher_id = current_user.student.teacher.id
    elif current_user.teacher:
        duration = data.get("duration", current_user.teacher.lesson_duration)
        teacher_id = current_user.teacher.id
        student_id = data.get("student_id")

    return {
        "date": date,
        "meetup": data.get("meetup"),
        "student_id": student_id,
        "teacher_id": teacher_id,
        "duration": duration,
        "topic_id": data.get("topic_id"),
        "comments": data.get("comments"),
        "is_approved": True if current_user.teacher else False,
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
    if not flask.request.get_json().get("date"):
        raise RouteError("Please insert the date of the lesson.")
    lesson = Lesson.create(**get_lesson_data())
    # TODO send notification to student / teacher

    return {"message": "Lesson created successfully.", "data": lesson.to_dict()}, 201


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

    # TODO send notification

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

    for k, v in get_lesson_data().items():
        if v:
            setattr(lesson, k, v)

    lesson.update_only_changed_fields()

    # TODO send notification

    return {"message": "Lesson updated successfully."}


@lessons_routes.route("/<int:lesson_id>/approve", methods=["GET"])
@jsonify_response
@login_required
@teacher_required
def approve_lesson(lesson_id):
    lesson = current_user.teacher.lessons.filter_by(id=lesson_id).first()
    if not lesson:
        raise RouteError("Lesson does not exist", 404)
    lesson.update(is_approved=True)

    # TODO send notification to student

    return {"message": "Lesson approved."}
