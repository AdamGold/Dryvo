import itertools
from datetime import datetime
from typing import Optional, Tuple, Dict

import flask
from flask import Blueprint
from flask_babel import gettext
from flask_login import current_user, login_required, logout_user
from loguru import logger
from sqlalchemy import and_

from server.api.blueprints import teacher_required
from server.api.database.models import (
    Appointment,
    AppointmentType,
    LessonTopic,
    Place,
    PlaceType,
    Student,
    Teacher,
    Topic,
    User,
)
from server.api.push_notifications import FCM
from server.api.utils import jsonify_response, paginate
from server.consts import DATE_FORMAT, DEBUG_MODE
from server.error_handling import RouteError, NotificationError

appointments_routes = Blueprint("appointments", __name__, url_prefix="/appointments")


def init_app(app):
    app.register_blueprint(appointments_routes)


def handle_places(
    meetup_place: Optional[Dict], dropoff_place: Optional[Dict], student: Student
) -> Tuple[Place, Place]:
    if not student:
        return None, None
    return (
        Place.create_or_find(meetup_place, PlaceType.meetup, student),
        Place.create_or_find(dropoff_place, PlaceType.dropoff, student),
    )


def get_data(data: dict, user: User, appointment: Optional[Appointment] = None) -> dict:
    """get request data and a specific user
    - we need the user because we are not decorated in login_required here
    returns dict of new lesson or edited lesson"""
    if not data.get("date"):
        raise RouteError("Date is not valid.")
    date = datetime.strptime(data["date"], DATE_FORMAT)
    if not appointment and date < datetime.utcnow():
        # trying to add a new lesson in the past??
        raise RouteError("Date is not valid.")

    meetup_input = data.get("meetup_place", {})
    dropoff_input = data.get("dropoff_place", {})
    type_ = None
    if appointment:
        type_ = appointment.type
        # don't update same places
        if (
            appointment.meetup_place
            and meetup_input.get("description") == appointment.meetup_place.description
        ):
            meetup_input = None
        if (
            appointment.dropoff_place
            and dropoff_input.get("description")
            == appointment.dropoff_place.description
        ):
            dropoff_input = None

    duration_mul = float(data.get("duration_mul", 1))
    if user.student:
        student = user.student
        teacher = user.student.teacher
        type_ = type_ or AppointmentType.LESSON.value
        available_hours = itertools.dropwhile(
            lambda hours_range: hours_range[0] != date,
            user.student.teacher.available_hours(
                requested_date=date, student=student, duration_mul=duration_mul
            ),
        )  # check if requested date in available hours
        try:
            next(available_hours)
        except StopIteration:
            if (appointment and date != appointment.date) or not appointment:
                raise RouteError("This hour is not available.")
    elif user.teacher:
        type_ = getattr(
            AppointmentType,
            data.get("type", "").upper(),
            type_ or AppointmentType.LESSON.value,
        )
        teacher = user.teacher
        student = Student.get_by_id(data.get("student_id"))
        if not student:
            raise RouteError("Student does not exist.")
    else:
        raise RouteError("Not authorized.", 401)

    meetup, dropoff = handle_places(meetup_input, dropoff_input, student)
    try:
        price = int(data.get("price", ""))
    except ValueError:
        price = None
    return {
        "date": date,
        "meetup_place": meetup,
        "dropoff_place": dropoff,
        "student": student,
        "teacher": teacher,
        "duration": duration_mul * teacher.lesson_duration,
        "price": price,
        "comments": data.get("comments"),
        "is_approved": True if user.teacher else False,
        "type": type_,
    }


@appointments_routes.route("/", methods=["GET"])
@jsonify_response
@login_required
@paginate
def appointments():
    user = current_user.teacher
    if not current_user.teacher:
        user = current_user.student

    try:
        return user.filter_appointments(flask.request.args)
    except ValueError:
        raise RouteError("Wrong parameters passed.")


@appointments_routes.route("/<int:id_>", methods=["GET"])
@jsonify_response
@login_required
def appointment(id_):
    appointment = Appointment.get_by_id(id_)
    if not appointment:
        raise RouteError("Appointment does not exist.")

    if current_user.id not in (
        appointment.student.user.id,
        appointment.teacher.user.id,
    ):
        raise RouteError("You are not allowed to view this appointment.", 401)

    return {"data": appointment.to_dict()}


@appointments_routes.route("/", methods=["POST"])
@jsonify_response
@login_required
def new_appointment():
    data = flask.request.get_json()
    if not data.get("date"):
        raise RouteError("Please insert the date of the appointment.")
    appointment = Appointment.create(**get_data(data, current_user))

    # send fcm to the user who wasn't the one creating the lesson
    user_to_send_to = appointment.teacher.user
    body_text = gettext(
        "%(student)s wants to schedule a new lesson at %(date)s. Click here to check it out.",
        student=appointment.student.user.name,
        date=appointment.date,
    )
    if appointment.creator == appointment.teacher.user and appointment.student:
        user_to_send_to = appointment.student.user
        body_text = gettext(
            "%(teacher)s scheduled a new lesson at %(value)s. Click here to check it out.",
            teacher=appointment.teacher.user.name,
            value=appointment.date,
        )
    if user_to_send_to.firebase_token:
        logger.debug(f"sending fcm to {user_to_send_to} for new appointment")
        try:
            FCM.notify(
                token=user_to_send_to.firebase_token,
                title=gettext("New Lesson!"),
                body=body_text,
            )
        except NotificationError:
            pass
    return {"data": appointment.to_dict()}, 201


@appointments_routes.route("/<int:lesson_id>/topics", methods=["POST"])
@jsonify_response
@login_required
@teacher_required
def update_topics(lesson_id):
    """update or add lesson topics
    accepts {'progress': [topics in progress], 'finished': [finished topics]}"""
    data = flask.request.get_json()
    FINISHED_KEY = "finished"
    lesson = Appointment.query.filter(
        and_(
            Appointment.type == AppointmentType.LESSON.value,
            Appointment.id == lesson_id,
        )
    ).first()
    if not lesson:
        raise RouteError("Lesson does not exist.")
    if not lesson.student:
        raise RouteError("Lesson must have a student assigned.")
    appended_ids = []
    for key, topic_ids in data.get("topics").items():
        for topic_id in topic_ids:
            if not Topic.get_by_id(topic_id):
                raise RouteError("Topic does not exist.")
            if topic_id in appended_ids:  # we don't want the same topic twice
                continue
            is_finished = True if key == FINISHED_KEY else False
            # existing_lesson_topic = lesson.topics.filter_by(topic_id=topic_id).first()
            # if existing_lesson_topic:
            #     if is_finished:
            #         existing_lesson_topic.update(is_finished=is_finished)
            #     continue
            lesson_topic = LessonTopic(is_finished=is_finished, topic_id=topic_id)
            lesson.topics.append(lesson_topic)
            appended_ids.append(topic_id)

    lesson.save()
    return {"data": lesson.to_dict()}, 201


@appointments_routes.route("/<int:id_>", methods=["DELETE"])
@jsonify_response
@login_required
def delete_appointment(id_):
    try:
        appointments = current_user.teacher.appointments
    except AttributeError:
        appointments = current_user.student.appointments
    appointment = appointments.filter_by(id=id_).first()
    if not appointment:
        raise RouteError("Appointment does not exist.")

    appointment.update(deleted=True)

    user_to_send_to = appointment.teacher.user
    if current_user == appointment.teacher.user:
        user_to_send_to = appointment.student.user
    if user_to_send_to.firebase_token:
        try:
            logger.debug(f"sending fcm to {user_to_send_to} for deleting lesson")
            FCM.notify(
                token=user_to_send_to.firebase_token,
                title=gettext("Lesson Deleted"),
                body=gettext(
                    "The lesson at %(value)s has been deleted.", value=appointment.date
                ),
            )
        except NotificationError:
            pass

    return {"message": "Appointment deleted successfully."}


@appointments_routes.route("/<int:id_>", methods=["POST"])
@jsonify_response
@login_required
def update_lesson(id_):
    try:
        appointments = current_user.teacher.appointments
    except AttributeError:
        appointments = current_user.student.appointments
    appointment = appointments.filter_by(id=id_).first()
    if not appointment:
        raise RouteError("Appointment does not exist", 404)
    data = flask.request.get_json()
    appointment.update_only_changed_fields(
        **get_data(data, current_user, appointment=appointment)
    )

    user_to_send_to = appointment.teacher.user
    body_text = gettext(
        "%(student)s wants to edit the lesson at %(date)s. Click here to check it out.",
        student=appointment.student.user.name,
        date=appointment.date,
    )
    if current_user == appointment.teacher.user:
        user_to_send_to = appointment.student.user
        body_text = gettext(
            "%(teacher)s edited the lesson at %(value)s. Click here to check it out.",
            teacher=appointment.teacher.user.name,
            value=appointment.date,
        )
    if user_to_send_to.firebase_token:
        try:
            logger.debug(f"sending fcm to {user_to_send_to} for lesson edit")
            FCM.notify(
                token=user_to_send_to.firebase_token,
                title=gettext("Lesson Updated"),
                body=body_text,
            )
        except NotificationError:
            pass

    return {
        "message": "Appointment updated successfully.",
        "data": appointment.to_dict(),
    }


@appointments_routes.route("/<int:lesson_id>/approve", methods=["GET"])
@jsonify_response
@login_required
@teacher_required
def approve_lesson(lesson_id):
    lesson = current_user.teacher.lessons.filter_by(id=lesson_id).first()
    if not lesson:
        raise RouteError("Lesson does not exist", 404)
    # check if there isn't another lesson at the same time
    same_time_lesson = Appointment.query.filter(
        Appointment.approved_lessons_filter(
            Appointment.date == lesson.date, Appointment.id != lesson.id
        )
    ).first()
    if same_time_lesson:
        raise RouteError("There is another lesson at the same time.")

    lesson.update(is_approved=True)

    if lesson.student.user.firebase_token:
        logger.debug(f"sending fcm for lesson approval")
        try:
            FCM.notify(
                token=lesson.student.user.firebase_token,
                title=gettext("Lesson Approved"),
                body=gettext("Lesson at %(date)s has been approved!", date=lesson.date),
            )
        except NotificationError:
            pass

    return {"message": "Lesson approved."}


@appointments_routes.route("/payments", methods=["GET"])
@jsonify_response
@login_required
@paginate
def payments():
    """endpoint to return filtered payments"""
    user = current_user.teacher
    if not current_user.teacher:
        user = current_user.student

    try:
        return user.filter_payments(flask.request.args)
    except ValueError:
        raise RouteError("Wrong parameters passed.")


@appointments_routes.route("/<int:lesson_id>/topics", methods=["GET"])
@jsonify_response
@login_required
def topics(lesson_id: int):
    """return all available topics of a lesson -
    1. topics that fit its number
    2. topics in progress of the lesson's student
    3. topics that were picked in this lesson"""
    student = Student.query.filter_by(id=flask.request.args.get("student_id")).first()
    lesson = None
    if lesson_id == 0 and student:
        # lesson hasn't been created yet, let's treat this like a new lesson
        lesson_number = student.lessons_done + 1
    else:
        lesson = Appointment.query.filter_by(id=lesson_id).first()
        if not lesson or not lesson.student:
            raise RouteError("Lesson does not exist or not assigned.", 404)
        (student, lesson_number) = (lesson.student, lesson.lesson_number)

    topics_for_lesson = student.topics(is_finished=False).union(
        set(Topic.for_lesson(lesson_number))
    ) - student.topics(is_finished=True)

    in_progress: list = []
    finished_in_this_lesson: list = []
    if lesson:
        in_progress = [
            lt.topic_id for lt in lesson.topics.filter_by(is_finished=False).all()
        ]
        finished_in_this_lesson = [
            lt.topic_id for lt in lesson.topics.filter_by(is_finished=True).all()
        ]
        # available lessons don't include student's finished topics,
        # so we have to add this specific lesson finished topics
        topics_for_lesson = topics_for_lesson.union(
            {Topic.query.filter_by(id=t).first() for t in finished_in_this_lesson}
        )
    return dict(
        available=[t.to_dict() for t in topics_for_lesson],
        progress=in_progress,
        finished=finished_in_this_lesson,
    )
