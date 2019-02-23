from datetime import datetime
from functools import wraps

import flask
from flask import Blueprint
from flask_login import current_user, login_required, logout_user

from server.api.database.models import Day, Payment, Student, Teacher, User, WorkDay
from server.api.utils import jsonify_response, paginate
from server.error_handling import RouteError

teacher_routes = Blueprint("teacher", __name__, url_prefix="/teacher")


def init_app(app):
    app.register_blueprint(teacher_routes)


def teacher_required(func):
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        if not current_user.teacher:
            raise RouteError("User is not a teacher.", 401)

        return func(*args, **kwargs)

    return func_wrapper


@teacher_routes.route("/work_days", methods=["GET"])
@jsonify_response
@login_required
@teacher_required
def work_days():
    """ return work days with filter - only on a specific date,
    or with no date at all"""
    try:
        return {
            "data": [
                day.to_dict()
                for day in current_user.teacher.filter_work_days(
                    flask.request.args.copy()
                )
            ]
        }
    except ValueError:
        raise RouteError("Wrong parameters passed.")


@teacher_routes.route("/work_days", methods=["POST"])
@jsonify_response
@login_required
@teacher_required
def new_work_day():
    data = flask.request.get_json()
    day = data.get("day")
    if not isinstance(day, int):
        day = getattr(Day, day, 1)
    date_input = data.get("on_date")
    date = datetime.strptime(date_input, "%Y-%m-%d")
    from_hour = max(min(data.get("from_hour"), 24), 0)
    to_hour = max(min(data.get("to_hour"), 24), 0)
    from_minutes = max(min(data.get("from_minutes"), 60), 0)
    to_minutes = max(min(data.get("to_minutes"), 60), 0)
    from_time = datetime.strptime(f"{from_hour}:{from_minutes}", "%H:%M")
    to_time = datetime.strptime(f"{to_hour}:{to_minutes}", "%H:%M")
    if from_time >= to_time:
        raise RouteError("There must be a bigger difference between the two times.")
    day = WorkDay(
        day=day,
        from_hour=from_hour,
        from_minutes=from_minutes,
        to_hour=to_hour,
        to_minutes=to_minutes,
        on_date=date,
    )
    current_user.teacher.work_days.append(day)
    day.save()

    return {"message": "Day created successfully.", "data": day.to_dict()}, 201


@teacher_routes.route("/work_days/<int:day_id>", methods=["POST"])
@jsonify_response
@login_required
@teacher_required
def edit_work_day(day_id):
    day = current_user.teacher.work_days.filter_by(id=day_id).first()
    if not day:
        raise RouteError("Day does not exist", 404)
    data = flask.request.get_json()
    from_hour = data.get("from_hour", day.from_hour)
    to_hour = data.get("to_hour", day.to_hour)
    day.update(from_hour=from_hour, to_hour=to_hour)
    return {"message": "Day updated successfully."}


@teacher_routes.route("/work_days/<int:day_id>", methods=["DELETE"])
@jsonify_response
@login_required
@teacher_required
def delete_work_day(day_id):
    day = current_user.teacher.work_days.filter_by(id=day_id).first()
    if not day:
        raise RouteError("Day does not exist", 404)
    day.delete()
    return {"message": "Day deleted."}


@teacher_routes.route("/<int:teacher_id>/available_hours", methods=["POST"])
@jsonify_response
@login_required
def available_hours(teacher_id):
    data = flask.request.get_json()
    teacher = Teacher.get_by_id(teacher_id)
    return {
        "data": list(
            teacher.available_hours(datetime.strptime(data.get("date"), "%Y-%m-%d"))
        )
    }


@teacher_routes.route("/add_payment", methods=["POST"])
@jsonify_response
@login_required
@teacher_required
def add_payment():
    data = flask.request.get_json()
    student = Student.get_by_id(data.get("student_id"))
    if not student:
        raise RouteError("Student does not exist.")
    if not data.get("amount"):
        raise RouteError("Amount must be given.")
    payment = Payment.create(
        teacher=current_user.teacher, student=student, amount=data.get("amount")
    )
    return {"data": payment.to_dict()}, 201


@teacher_routes.route("/students", methods=["GET"])
@jsonify_response
@login_required
@teacher_required
@paginate
def students():
    """allow filtering by name / area of student, and sort by balance,
    lesson number"""

    def custom_filter(model, key, value):
        return getattr(model, key).like(f"%{value}%")

    try:
        query = current_user.teacher.students
        args = flask.request.args.copy()
        extra_filters = {User: {"name": custom_filter, "area": custom_filter}}
        return Student.filter_and_sort(
            args, query, extra_filters=extra_filters, with_pagination=True
        )
    except ValueError:
        raise RouteError("Wrong parameters passed.")
