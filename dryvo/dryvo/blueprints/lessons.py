import flask
from flask import Blueprint
from flask_login import current_user, login_required, logout_user

from api.database.consts import LESSONS_PER_PAGE
from api.utils import jsonify_response, RouteError, paginate
from api.database.models.teacher import Teacher
from api.database.models.lesson import Lesson
from api.database.models.student import Student
from consts import DATE_FORMAT, DEBUG_MODE

from datetime import datetime

lessons_routes = Blueprint('lessons', __name__, url_prefix='/lessons')


def get_lesson_data():
    data = flask.request.get_json()

    date = datetime.strptime(data.get('date'), DATE_FORMAT)
    if date < datetime.now() and not DEBUG_MODE:
        raise RouteError('Date is not valid.')
    student_id = data.get('student_id')
    student = Student.get_by_id(int(student_id))
    if not student:
        student_id = None

    if current_user.student:
        duration = current_user.student.teacher.lesson_duration
        student_id = current_user.student.id
        flag = False
        for lesson_tuple in current_user.student.teacher.available_hours(date):
            if lesson_tuple[0] == date:
                flag = True
        if not flag:
            raise RouteError('This hour is not available.')
        teacher_id = current_user.student.teacher.id
    elif current_user.teacher:
        duration = data.get('duration', current_user.teacher.lesson_duration)
        teacher_id = current_user.teacher.id

    return {
        'date': date,
        'meetup': data.get('meetup'),
        'student_id': student_id,
        'teacher_id': teacher_id,
        'duration': duration,
        'is_approved': True if student_id and not current_user.student else False
    }


@lessons_routes.route('/', methods=['GET'])
@jsonify_response
@login_required
@paginate
def lessons():
    filter_args = flask.request.args
    page = flask.request.args.get('page', 1, type=int)
    user = current_user.teacher
    if not current_user.teacher:
        user = current_user.student

    pagination = user.filter_lessons(filter_args). \
        paginate(page, LESSONS_PER_PAGE, False)
    return pagination


@lessons_routes.route('/', methods=['POST'])
@jsonify_response
@login_required
def new_lesson():
    if not flask.request.get_json().get('date'):
        raise RouteError('Please insert the date of the lesson.')
    lesson = Lesson(**get_lesson_data())
    lesson.save()

    return {'message': 'Lesson created successfully.'}, 201


@lessons_routes.route('/lessons/<int:lesson_id>', methods=['DELETE'])
@jsonify_response
@login_required
def delete_lesson(lesson_id):
    try:
        lessons = current_user.teacher.lessons
    except AttributeError:
        lessons = current_user.student.lessons
    lessons.filter_by(id=lesson_id).first().update(deleted=True)

    return {'message': 'Lesson deleted successfully.'}


@lessons_routes.route('/lessons/<int:lesson_id>', methods=['POST'])
@jsonify_response
@login_required
def update_lesson(lesson_id):
    lesson = current_user.teacher.lessons.filter_by(id=lesson_id).first()
    if not lesson:
        raise RouteError('Lesson does not exist', 404)

    for k, v in get_lesson_data().items():
        if v:
            setattr(lesson, k, v)

    lesson.update_only_changed_fields()

    return {'message': 'Lesson updated successfully.'}
