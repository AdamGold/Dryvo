import traceback
import flask
import werkzeug
from loguru import logger

from server.api.utils import jsonify_response
from server.consts import DEBUG_MODE


def init_app(app):
    for exception in (RouteError, TokenError):
        app.register_error_handler(exception, handle_verified_exception)
    app.register_error_handler(Exception, handle_unverified_exception)
    app.register_error_handler(404, handle_not_found)


@jsonify_response
def handle_verified_exception(e):
    logger.debug(f"Exception! {e.msg}")
    return {"message": e.msg}, e.code


@jsonify_response
def handle_unverified_exception(e):
    msg = traceback.format_exc()
    logger.error(msg)
    if not DEBUG_MODE:
        msg = "Something went wrong. Please try again later."
    data = {"message": msg}
    return data, 500


@jsonify_response
def handle_not_found(e):
    logger.debug(f"{flask.request.full_path} Not found!")
    return ({"message": f"Endpoint {flask.request.full_path} doesn't exist"},
            404)


class RouteError(werkzeug.exceptions.HTTPException):
    def __init__(self, msg, code=400):
        self.msg = msg
        self.code = code


class TokenError(RouteError):
    def __init__(self, msg):
        self.code = 401
        self.msg = msg
