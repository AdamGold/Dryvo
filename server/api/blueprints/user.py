import flask
from flask import Blueprint
from flask_login import current_user, login_required
from loguru import logger
from sqlalchemy import and_

from server.api.blueprints import teacher_required
from server.api.database.models import Student, Teacher, User
from server.api.push_notifications import FCM
from server.api.utils import jsonify_response, paginate
from server.error_handling import RouteError

user_routes = Blueprint("user", __name__, url_prefix="/user")


def init_app(app):
    app.register_blueprint(user_routes)


def get_user_info(user: User):
    info = user.teacher or user.student or {}
    return info.to_dict() if info else {}


@user_routes.route("/me", methods=["GET"])
@jsonify_response
@login_required
def me():
    return {"user": dict(**current_user.to_dict(), **get_user_info(current_user))}


@user_routes.route("/search", methods=["GET"])
@jsonify_response
@teacher_required
@paginate
def search():
    try:
        query = User.query.filter(and_(User.teacher == None, User.student == None))
        return User.filter_and_sort(
            flask.request.args, query=query, with_pagination=True
        )
    except ValueError:
        raise RouteError("Wrong parameters passed.")


@user_routes.route("/make_student", methods=["GET"])
@jsonify_response
@login_required
def make_student():
    data = flask.request.args
    user = current_user if current_user.student else User.get_by_id(data.get("user_id"))

    if not user:
        raise RouteError("User was not found.", 401)
    if user.teacher or user.student:
        raise RouteError(
            "User was not found or the user is already a student or a teacher."
        )

    teacher = current_user.teacher or Teacher.get_by_id(data.get("teacher_id"))
    if not teacher:
        raise RouteError("Teacher was not found.")

    student = Student.create(
        user_id=user.id, teacher_id=teacher.id, creator=current_user
    )
    # send notification
    user_to_send_to = student.user
    if student.creator == user_to_send_to:
        user_to_send_to = teacher.user
    if user_to_send_to.firebase_token:
        logger.debug(f"sending fcm to {user_to_send_to}")
        FCM.notify(
            token=user_to_send_to.firebase_token,
            title="Join Request",
            body=f"{user_to_send_to.name} wants you to join!",
        )
    return {"data": student.to_dict()}, 201


@user_routes.route("/make_teacher", methods=["POST"])
@jsonify_response
@login_required
def make_teacher():
    data = flask.request.get_json()
    if not current_user.is_admin:
        raise RouteError("Not authorized.", 401)

    user_id = data.get("user_id")
    user = User.get_by_id(user_id)
    if not user or user.student or user.teacher:
        raise RouteError("User was not found.")

    price = data.get("price")
    phone = data.get("phone")
    if not price or not phone:
        raise RouteError("Empty fields.")

    if price <= 0:
        raise RouteError("Price must be above 0.")

    teacher = Teacher.create(
        user_id=user_id,
        price=price,
        phone=phone,
        lesson_duration=data.get("lesson_duration"),
    )
    return {"data": teacher.to_dict()}, 201


@user_routes.route("/register_firebase_token", methods=["POST"])
@jsonify_response
@login_required
def register_firebase_token():
    token = flask.request.get_json()["token"]
    if not token:
        raise RouteError("Token is not valid.")

    # now delete this token in other users (if this device connected to multiple users)
    different_user = User.query.filter_by(firebase_token=token).first()
    if different_user and different_user.id != current_user.id:
        different_user.update(token=None)

    current_user.update(firebase_token=token)

    return {"message": "Token updated successfully."}
