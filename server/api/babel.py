from flask import g, request
from flask_babel import Babel

babel = Babel()


def init_app(app):
    babel.init_app(app)


@babel.localeselector
def get_locale():
    """currently we only support hebrew"""
    return "he"
