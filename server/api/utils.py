import os
from functools import wraps
import traceback

import flask
from flask.json import jsonify
from server.consts import DEBUG_MODE
from datetime import datetime, timedelta


def jsonify_response(func):
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        if not response:
            return flask.make_response(), 400
        elif isinstance(response, tuple):
            (data, code) = response
        else:
            data = response
            code = 200

        return flask.make_response(jsonify(data)), code

    return func_wrapper


def paginate(func):
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        response = func(*args, **kwargs)

        query_params = flask.request.args.copy()
        if "page" in query_params:
            query_params.pop("page")  # we are changing page
        kwargs.update(query_params)

        if isinstance(response, list):  # response isn't a pagination this time
            return {"data": [item.to_dict() for item in response]}

        if isinstance(response, tuple):  # we have pagination and data separate
            pagination = response[0]
            data = response[1]
        else:
            pagination = response
            data = [item.to_dict() for item in response.items]

        next_url = (
            flask.url_for(
                ".{}".format(func.__name__),
                page=pagination.next_num,
                _external=True,
                *args,
                **kwargs
            )
            if pagination.has_next
            else None
        )
        prev_url = (
            flask.url_for(
                ".{}".format(func.__name__),
                page=pagination.prev_num,
                _external=True,
                *args,
                **kwargs
            )
            if pagination.has_prev
            else None
        )
        return {"next_url": next_url, "prev_url": prev_url, "data": data}

    return func_wrapper


def get_slots(hours: (datetime, datetime), appointments: [tuple], duration: timedelta):
    minimum = (hours[0], hours[0])
    maximum = (hours[1], hours[1])
    available_lessons = []
    slots = [
        max(min(v, maximum), minimum)
        for v in sorted([minimum] + appointments + [maximum])
    ]
    for start, end in ((slots[i][1], slots[i + 1][0]) for i in range(len(slots) - 1)):
        while start + duration <= end:
            available_lessons.append((start, start + duration))
            start += duration

    return available_lessons
