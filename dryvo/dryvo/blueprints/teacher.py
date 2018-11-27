import flask
from flask import Blueprint
from flask_login import current_user, login_required, logout_user

from api.database.consts import LESSONS_PER_PAGE, DAYS_PER_PAGE
from consts import DATE_FORMAT
from api.utils import jsonify_response, RouteError, paginate
from api.database.models.teacher import Teacher
from api.database.models.lesson import Lesson
from api.database.models.student import Student
from api.database.models.work_day import WorkDay, Day

from functools import wraps
from datetime import datetime

teacher_routes = Blueprint('teacher', __name__, url_prefix='/teacher')


def get_lesson_data():
    data = flask.request.get_json()
    student_id = data.get('student_id')
    if student_id:
        student = Student.get_by_id(int(data.get('student_id')))
        if not student:
            student_id = None
    return {
        'date': datetime.strptime(data.get('date'), DATE_FORMAT),
        'meetup': data.get('meetup'),
        'student_id': student_id,
        'duration': data.get('duration', current_user.teacher.lesson_duration),
        'is_approved': True if student_id else False
    }


def teacher_required(func):
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        if not current_user.teacher:
            raise RouteError('User is not a teacher.')

        return func(*args, **kwargs)

    return func_wrapper


@teacher_routes.route('/lessons', methods=['GET'])
@jsonify_response
@login_required
@teacher_required
@paginate
def lessons():
    page = flask.request.args.get('page', 1, type=int)
    pagination = current_user.teacher.lessons.filter_by(deleted=False). \
        paginate(page, LESSONS_PER_PAGE, False)
    return pagination


@teacher_routes.route('/lessons', methods=['POST'])
@jsonify_response
@login_required
@teacher_required
def new_lesson():
    if not flask.request.get_json().get('date'):
        raise RouteError('Please insert the date of the lesson.')
    lesson = Lesson(**get_lesson_data())
    current_user.teacher.lessons.append(lesson)
    lesson.save()

    return {'message': 'Lesson created successfully.'}, 201


@teacher_routes.route('/lessons/<int:lesson_id>', methods=['DELETE'])
@jsonify_response
@login_required
@teacher_required
def delete_lesson(lesson_id):
    lesson = current_user.teacher.lessons.filter_by(id=lesson_id).first()
    lesson.update(deleted=True)

    return {'message': 'Lesson deleted successfully.'}


@teacher_routes.route('/lessons/<int:lesson_id>', methods=['POST'])
@jsonify_response
@login_required
@teacher_required
def update_lesson(lesson_id):
    lesson = current_user.teacher.lessons.filter_by(id=lesson_id).first()
    if not lesson:
        raise RouteError('Lesson does not exist', 404)

    for k, v in get_lesson_data().items():
        if v:
            setattr(lesson, k, v)

    lesson.update_only_changed_fields()

    return {'message': 'Lesson updated successfully.'}


@teacher_routes.route('/work_days', methods=['GET'])
@jsonify_response
@login_required
@teacher_required
@paginate
def work_days():
    page = flask.request.args.get('page', 1, type=int)
    pagination = current_user.teacher.work_days. \
        paginate(page, DAYS_PER_PAGE, False)
    return pagination


@teacher_routes.route('/work_days', methods=['POST'])
@jsonify_response
@login_required
@teacher_required
def new_work_day():
    data = flask.request.get_json()
    day = data.get('day')
    if not isinstance(day, int):
        day = getattr(Day, day, 1)
    day = WorkDay(day=day,
                  from_hour=max(min(data.get('from_hour'), 24), 0),
                  from_minutes=max(min(data.get('from_minutes'), 60), 0),
                  to_hour=max(min(data.get('to_hour'), 24), 0),
                  to_minutes=max(min(data.get('to_minutes'), 60), 0))
    current_user.teacher.work_days.append(day)
    day.save()

    return {'message': 'Day created successfully.'}, 201


@teacher_routes.route('/work_days/<int:day_id>', methods=['POST'])
@jsonify_response
@login_required
@teacher_required
def edit_work_day(day_id):
    day = current_user.teacher.work_days.filter_by(id=day_id).first()
    if not day:
        raise RouteError('Day does not exist', 404)
    data = flask.request.get_json()
    from_hour = data.get('from_hour', day.from_hour)
    to_hour = data.get('to_hour', day.to_hour)
    day.update(from_hour=from_hour, to_hour=to_hour)
    return {'message': 'Day updated successfully.'}


@teacher_routes.route('/work_days/<int:day_id>', methods=['DELETE'])
@jsonify_response
@login_required
@teacher_required
def delete_work_day(day_id):
    day = current_user.teacher.work_days.filter_by(id=day_id).first()
    if not day:
        raise RouteError('Day does not exist', 404)
    day.delete()
    return {'message': 'Day deleted.'}


@teacher_routes.route('/<int:teacher_id>/available_hours', methods=['POST'])
@jsonify_response
@login_required
def available_hours(teacher_id):
    data = flask.request.get_json()
    teacher = Teacher.get_by_id(teacher_id)
    return teacher.available_hours(datetime.strptime(data.get('date'), '%Y-%m-%d'))
