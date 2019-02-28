import flask
from flask import Blueprint
from flask_login import current_user, login_required

from server.api.blueprints import teacher_required
from server.api.database.models import Student, Teacher, User
from server.api.utils import jsonify_response
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
def search():
    try:
        return User.filter_and_sort(flask.request.args, with_pagination=True)
    except ValueError:
        raise RouteError("Wrong parameters passed.")


@user_routes.route("/make_student", methods=["POST"])
@jsonify_response
@login_required
def make_student():
    data = flask.request.get_json()
    user_id = data.get("user_id")
    if user_id == 0:
        user = current_user
    elif current_user.is_admin:
        user = User.get_by_id(user_id)
    else:
        raise RouteError("Not authorized.", 401)

    if user.teacher or user.student:
        raise RouteError("Already student or teacher.")

    teacher_id = data.get("teacher_id")
    teacher = Teacher.get_by_id(teacher_id)
    if not teacher:
        raise RouteError("Teacher not found.")

    student = Student(user_id=user.id, teacher_id=teacher_id)
    student.save()
    return {"message": "Student created successfully."}, 201


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
        raise RouteError("User not found.")

    price = data.get("price")
    phone = data.get("phone")
    if not price or not phone:
        raise RouteError("Empty fields.")

    if price <= 0:
        raise RouteError("Price must be above 0.")

    teacher = Teacher(
        user_id=user_id,
        price=price,
        phone=phone,
        lesson_duration=data.get("lesson_duration"),
    )
    teacher.save()
    return {"message": "Teacher created successfully."}, 201


@user_routes.route("/register_firebase_token", methods=["POST"])
@jsonify_response
@login_required
def register_firebase_token():
    token = flask.request.get_json()["token"]
    if not token:
        raise RouteError("Token is not valid.")

    current_user.update(firebase_token=token)
    return {"message": "Token updated successfully."}
