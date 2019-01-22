import traceback
import flask
import werkzeug
from loguru import logger

from server.api.utils import jsonify_response
from server.consts import DEBUG_MODE


def init_app(app):
    for exception in (RouteError,
                      TokenError,
                      NotificationError,
                      werkzeug.exceptions.MethodNotAllowed,
                      werkzeug.exceptions.Unauthorized,
                      werkzeug.exceptions.BadRequest,):
        app.register_error_handler(exception, handle_verified_exception)
    app.register_error_handler(Exception, handle_unverified_exception)
    app.register_error_handler(404, handle_not_found)


@jsonify_response
def handle_verified_exception(e):
    logger.debug(f"Exception! {e.description}")
    return {"message": e.description}, e.code


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
    return ({"message": f"Endpoint {flask.request.full_path} doesn't exist"}, 404)


class RouteError(werkzeug.exceptions.HTTPException):
    def __init__(self, description, code=400):
        self.description = description
        self.code = code


class TokenError(RouteError):
    def __init__(self, description):
        self.code = 401
        self.description = description


class NotificationError(RouteError):
    pass
