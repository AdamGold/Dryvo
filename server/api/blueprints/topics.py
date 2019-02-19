import flask
from flask import Blueprint
from flask_login import current_user, login_required, logout_user
from datetime import datetime

from server.api.utils import jsonify_response, paginate
from server.error_handling import RouteError
from server.api.database.models import Topic


topics_routes = Blueprint("topics", __name__, url_prefix="/topics")


def init_app(app):
    app.register_blueprint(topics_routes)


@topics_routes.route("/", methods=["GET"])
@jsonify_response
@login_required
def topics():
    return {"data": [topic.to_dict() for topic in Topic.query.all()]}


@topics_routes.route("/", methods=["POST"])
@jsonify_response
@login_required
def new_topic():
    if not current_user.is_admin:
        raise RouteError("Admin required.", 401)

    data = flask.request.get_json()
    topic = Topic.create(
        title=data.get("title"),
        min_lesson_number=data.get("min_lesson_number"),
        max_lesson_number=data.get("max_lesson_number"),
    )
    return {"data": topic.to_dict()}, 201


@topics_routes.route("/<int:topic_id>", methods=["DELETE"])
@jsonify_response
@login_required
def delete_topic(topic_id):
    if not current_user.is_admin:
        raise RouteError("Admin required.", 401)
    topic = Topic.get_by_id(topic_id)
    if not topic:
        raise RouteError("Topic does not exist", 404)
    topic.delete()
    return {"message": "Topic deleted."}
