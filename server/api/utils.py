import os
import traceback
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Tuple, List

import flask
from flask.json import jsonify
from loguru import logger

from server.consts import DEBUG_MODE, MOBILE_LINK


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

        # response isn't a pagination this time - probably because there was no limit argument supplied
        if isinstance(response, list):
            return {"data": [item.to_dict() for item in response]}

        if isinstance(response, tuple):  # we have pagination and data separate
            pagination = response[0]
            data = response[1]
        else:
            pagination = response
            data = [item.to_dict() for item in response.items]

        next_url = (
            build_pagination_url(func, pagination.next_num, *args, **kwargs)
            if pagination.has_next
            else None
        )
        prev_url = (
            build_pagination_url(func, pagination.prev_num, *args, **kwargs)
            if pagination.has_prev
            else None
        )
        return {"next_url": next_url, "prev_url": prev_url, "data": data}

    return func_wrapper


def build_pagination_url(func: callable, page, *args, **kwargs) -> str:
    return flask.url_for(
        f".{func.__name__}", page=page, _external=True, *args, **kwargs
    )


def get_free_ranges_of_hours(
    hours: Tuple[datetime, datetime], appointments: List[Tuple[datetime, datetime]]
):
    """ take actual hour to hour ranges from SLOTS. Ex: if the slots are:
    SLOTS [(datetime.datetime(2019, 6, 26, 13, 0), datetime.datetime(2019, 6, 26, 13, 0)),
           (datetime.datetime(2019, 6, 26, 13, 30, 20, 123123), datetime.datetime(2019, 6, 26, 14, 10, 20, 123123)),
           (datetime.datetime(2019, 6, 26, 17, 0), datetime.datetime(2019, 6, 26, 17, 0))]
    Then the free ranges will be:
    RETURN [(datetime.datetime(2019, 6, 26, 13, 0), datetime.datetime(2019, 6, 26, 13, 30, 20, 123123)),
                 (datetime.datetime(2019, 6, 26, 14, 10, 20, 123123), datetime.datetime(2019, 6, 26, 17, 0))]
    """
    minimum = (hours[0], hours[0])
    maximum = (hours[1], hours[1])
    slots = [
        max(min(v, maximum), minimum)
        for v in sorted([minimum] + appointments + [maximum])
    ]  # limit to maximum and mimimum hours
    return ((slots[i][1], slots[i + 1][0]) for i in range(len(slots) - 1))


def get_slots(
    hours: Tuple[datetime, datetime],
    appointments: List[Tuple[datetime, datetime]],
    duration: timedelta,
    blacklist: Dict[str, list],
    force_future: bool = False,
):
    """get a tuple with an hour range and a list of lessons, return empty slots
    in that hour range"""

    available_lessons = []
    free_ranges = get_free_ranges_of_hours(hours, appointments)
    for start, end in free_ranges:
        while start + duration <= end:
            if (
                (not force_future or (start >= datetime.utcnow()))
                and start.hour not in blacklist["start_hour"]
                and (start + duration).hour not in blacklist["end_hour"]
            ):
                available_lessons.append((start, start + duration))
            start += duration

    return available_lessons


def must_redirect(func):
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        try:
            params = func(*args, **kwargs)
        except Exception as e:
            params = {"error": str(e)}
        app_url = build_url(url=MOBILE_LINK, **params)
        logger.info(f"Redirecting them to {app_url}")
        return flask.redirect(app_url)

    return func_wrapper


def build_url(url: str, **params: Dict[str, str]) -> str:
    param_str = "&".join(f"{key}={val}" for key, val in params.items())
    return f"{url}?{param_str}"
