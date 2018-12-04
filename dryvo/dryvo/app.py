import os

import flask

from consts import DEBUG_MODE
from app_config import Config
from blueprints.login import login_routes
from blueprints.user import user_routes
from blueprints.teacher import teacher_routes
from blueprints.student import student_routes
from blueprints.lessons import lessons_routes
from blueprints.stages import stages_routes
from extensions import sess, db, login_manager


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


def create_app(config):
    """An application factory, as explained here: http://flask.pocoo.org/docs/patterns/appfactories/.
    :param config: The configuration object to use.
    """
    flask_app = flask.Flask(__name__)
    flask_app.config.from_object(config)
    register_extensions(flask_app)
    register_blueprints(flask_app)
    return flask_app


app = create_app(Config)


@app.route('/')
def home():
    return 'Debug mode enabled!' if DEBUG_MODE else 'Production mode enabled!'
