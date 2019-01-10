import flask
from flask import Blueprint
from flask_login import current_user, login_required, logout_user
from functools import wraps
from datetime import datetime

from server.api.database.consts import LESSONS_PER_PAGE, DAYS_PER_PAGE
from server.api.utils import jsonify_response, paginate
from server.error_handling import RouteError
from server.api.database.models import Stage, Topic, Student


student_routes = Blueprint("student", __name__, url_prefix="/student")


def init_app(app):
    app.register_blueprint(student_routes)


def student_required(func):
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        if not current_user.student:
            raise RouteError("User is not a student.")

        return func(*args, **kwargs)

    return func_wrapper


@student_routes.route("/<int:student_id>/stages", methods=["GET"])
@jsonify_response
@login_required
@paginate
def stages(student_id):
    student = Student.get_by_id(student_id)
    if not student:
        raise RouteError("Student does not exist.")
    page = flask.request.args.get("page", 1, type=int)

    pagination = Stage.query.order_by(Stage.order).paginate(page, 10, False)
    data = [s.to_dict(student_id) for s in pagination.items]
    return pagination, data


@student_routes.route("/<int:student_id>/topics/<int:topic_id>", methods=["POST"])
@jsonify_response
@login_required
def edit_topic(student_id, topic_id):
    student = Student.get_by_id(student_id)
    if not student:
        raise RouteError("Student does not exist.")

    topic = Topic.get_by_id(topic_id)
    if not topic:
        raise RouteError("Topic does not exist.")
    if not topic.mark_for_student(student_id):
        raise RouteError("No lesson has been done on this topic.")
    return {"message": "Topic marked successfully."}
