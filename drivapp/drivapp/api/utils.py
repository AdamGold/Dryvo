import os
from functools import wraps
import traceback

import flask
from flask.json import jsonify


class RouteError(Exception):
    def __init__(self, msg, code=400):
        self.msg = msg
        self.code = code


def jsonify_response(func):
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
            if not response:
                return flask.make_response(), 400
            elif isinstance(response, tuple):
                (data, code) = response
            else:
                data = response
                code = 200
        except RouteError as e:
            data = {'message': e.msg}
            code = e.code
        except Exception:
            if not DEBUG_MODE:
                raise
            data = {'message': traceback.format_exc()}
            code = 500

        return flask.make_response(jsonify(data)), code

    return func_wrapper


def paginate(func):
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        if isinstance(response, tuple):
            pagination = response[0]
            data = response[1]
        else:
            pagination = response
            data = [item.to_dict() for item in response.items]

        next_url = flask.url_for('.{}'.format(func.__name__), \
                                 page=pagination.next_num, _external=True, *args, **kwargs) \
            if pagination.has_next else None
        prev_url = flask.url_for('.{}'.format(func.__name__), \
                                 page=pagination.prev_num, _external=True, *args, **kwargs) \
            if pagination.has_prev else None
        return {
            'next_url': next_url,
            'prev_url': prev_url,
            'data': data
        }

    return func_wrapper
