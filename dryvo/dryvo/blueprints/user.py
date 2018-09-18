import flask
from flask import Blueprint
from flask_login import current_user, login_required, logout_user

from api.utils import jsonify_response, RouteError
from api.database.models.user import User
from api.database.models.student import Student
from api.database.models.teacher import Teacher


user_routes = Blueprint('user', __name__, url_prefix='/user')


@user_routes.route('/make_student', methods=['POST'])
@jsonify_response
@login_required
def make_student():
    data = flask.request.get_json()
    user_id = data.get('user_id')
    if user_id == 0:
        user = current_user
    elif current_user.is_admin:
        user = User.get_by_id(user_id)
    else:
        raise RouteError('Not authorized.', 401)

    if user.teacher or user.student:
        raise RouteError('Already student or teacher.')

    teacher_id = data.get('teacher_id')
    teacher = Teacher.get_by_id(teacher_id)
    if not teacher:
        raise RouteError('Teacher not found.')

    student = Student(user_id=user.id, teacher_id=teacher_id)
    student.save()
    return {'message': 'Student created successfully.'}, 201


@user_routes.route('/make_teacher', methods=['POST'])
@jsonify_response
@login_required
def make_teacher():
    data = flask.request.get_json()
    if not current_user.is_admin:
        raise RouteError('Not authorized.', 401)

    user_id = data.get('user_id')
    user = User.get_by_id(user_id)
    if not user or user.student or user.teacher:
        raise RouteError('User not found.')

    price = data.get('price')
    phone = data.get('phone')
    if not price or not phone:
        raise RouteError('Empty fields.')

    teacher = Teacher(user_id=user_id,
                      price=price,
                      phone=phone,
                      is_paying=data.get('is_paying', True))
    teacher.save()
    return {'message': 'Teacher created successfully.'}, 201


@user_routes.route('/logout')
@jsonify_response
@login_required
def logout():
    logout_user()
    return {'message': 'Logout successfully.'}
