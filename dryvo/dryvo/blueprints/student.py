import flask
from flask import Blueprint
from flask_login import current_user, login_required, logout_user

from api.database.consts import LESSONS_PER_PAGE, DAYS_PER_PAGE
from api.utils import jsonify_response, RouteError, paginate
from api.database.models.lesson import Lesson
from api.database.models.student import Student

from functools import wraps
from datetime import datetime

student_routes = Blueprint('student', __name__, url_prefix='/student')


def student_required(func):
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        if not current_user.student:
            raise RouteError('User is not a student.')

        return func(*args, **kwargs)

    return func_wrapper
