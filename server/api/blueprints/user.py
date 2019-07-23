import flask
from cloudinary.uploader import upload
from flask import Blueprint
from flask_babel import gettext
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


@user_routes.route("/me", methods=["GET"])
@jsonify_response
@login_required
def me():
    return {"user": current_user.to_dict()}


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
    user = current_user
    teacher = Teacher.get_by_id(data.get("teacher_id"))
    if current_user.teacher:
        user = User.get_by_id(data.get("user_id"))
        teacher = current_user.teacher

    if not user:
        raise RouteError("User was not found.", 401)
    if user.teacher or user.student:
        raise RouteError("User is already a student or a teacher.")

    if not teacher:
        raise RouteError("Teacher was not found.")

    try:
        price = int(data.get("price", ""))
    except ValueError:
        price = None
    student = Student.create(
        user=user, teacher=teacher, creator=current_user, price=price
    )
    # send notification
    user_to_send_to = student.user
    body_text = gettext(
        "%(teacher)s added you as a student!", teacher=teacher.user.name
    )
    if student.creator == user_to_send_to:
        user_to_send_to = teacher.user
        body_text = gettext(
            "%(student)s added you as a teacher!", student=student.user.name
        )
    if user_to_send_to.firebase_token:
        logger.debug(f"sending fcm to {user_to_send_to}")
        FCM.notify(
            token=user_to_send_to.firebase_token,
            title=gettext("Join Request"),
            body=body_text,
        )
    return {"data": student.to_dict()}, 201


@user_routes.route("/make_teacher", methods=["POST"])
@jsonify_response
@login_required
def make_teacher():
    data = flask.request.get_json()

    if not current_user or current_user.student or current_user.teacher:
        raise RouteError("User was not found.")

    price = data.get("price")
    if not price:
        raise RouteError("Empty fields.")

    if price <= 0:
        raise RouteError("Price must be above 0.")

    teacher = Teacher.create(
        user=current_user,
        price=price,
        lesson_duration=data.get("lesson_duration"),
        crn=data.get("crn"),
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
        different_user.update(firebase_token=None)

    current_user.update(firebase_token=token)

    return {"message": "Token updated successfully."}


@user_routes.route("/delete_firebase_token", methods=["GET"])
@jsonify_response
@login_required
def delete_firebase_token():
    current_user.update(firebase_token=None)

    return {"message": "Token deleted successfully."}


@user_routes.route("/image", methods=["POST"])
@jsonify_response
@login_required
def upload_profile_image():
    data = flask.request.files
    uploaded_image = upload(data.get("image"))
    current_user.update(image=uploaded_image["public_id"])
    return {"image": uploaded_image["url"]}
