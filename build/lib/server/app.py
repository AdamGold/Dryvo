import os
import flask

from server.consts import DEBUG_MODE
from server.app_config import Config
from server.api.blueprints import (
    login_routes,
    user_routes,
    teacher_routes,
    student_routes,
    lessons_routes,
    stages_routes,
)
from server.extensions import sess, db, login_manager


def register_blueprints(app):
    app.register_blueprint(login_routes)
    app.register_blueprint(user_routes)
    app.register_blueprint(teacher_routes)
    app.register_blueprint(student_routes)
    app.register_blueprint(lessons_routes)
    app.register_blueprint(stages_routes)


def register_extensions(flask_app):
    """Register Flask extensions."""
    sess.init_app(flask_app)
    db.init_app(flask_app)
    login_manager.init_app(flask_app)


def create_app(**test_config):
    """An application factory, as explained here: http://flask.pocoo.org/docs/patterns/appfactories/.
    :param config: The configuration object to use.
    """
    flask_app = flask.Flask(__name__)
    config = Config()
    config.update(test_config)
    flask_app.config.from_object(config)
    register_extensions(flask_app)
    register_blueprints(flask_app)
    add_endpoints(flask_app)
    return flask_app


# app = create_app(Config)


def add_endpoints(app):
    @app.route("/")
    def home():
        return "Debug mode enabled!" if DEBUG_MODE else "Production mode enabled!"
