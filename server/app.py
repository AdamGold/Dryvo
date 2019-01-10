import os
import flask
from loguru import logger

from server.consts import DEBUG_MODE
from server.app_config import Config
from server.api.blueprints import (
    login,
    user,
    teacher,
    student,
    lessons,
    stages,
)
from server.extensions import sess, login_manager
from server.api.database import database
from server import error_handling


def register_extensions_and_blueprints(flask_app):
    """Register Flask extensions and blueprints (each has init_app method)."""
    for module in (sess, database, login_manager, error_handling, login,
                   lessons, stages, user, teacher, student):
        module.init_app(flask_app)


def create_app(**test_config):
    """An application factory, as explained here: http://flask.pocoo.org/docs/patterns/appfactories/.
    :param config: The configuration object to use.
    """
    flask_app = flask.Flask(__name__)
    logger.debug("Starting Flask app")
    config = Config()
    config.update(test_config)
    flask_app.config.from_object(config)
    register_extensions_and_blueprints(flask_app)
    add_endpoints(flask_app)
    return flask_app


# app = create_app(Config)


def add_endpoints(app):
    @app.route("/")
    def home():
        return "Debug mode enabled!" if DEBUG_MODE else "Production mode enabled!"
