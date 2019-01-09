from server.api.utils import jsonify_response, get_slots
import json
import flask
from datetime import datetime, timedelta


def test_jsonify_response(app):
    msg = {'message': 'testing'}

    @jsonify_response
    def func():
        return msg
    with app.app_context():
        resp, code = func()
        assert code == 200
        assert json.loads(resp.response[0]) == msg


def test_get_slots():
    from_hour = datetime.now()
    to_hour = from_hour + timedelta(hours=1)
    duration = timedelta(minutes=30)
    taken = [(from_hour, from_hour + duration)]
    slots = get_slots((from_hour, to_hour), taken, duration)
    assert slots == [(from_hour + timedelta(minutes=30), to_hour)]

