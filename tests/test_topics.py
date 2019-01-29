import pytest
from datetime import datetime
from loguru import logger

from server.api.database.models import Topic


def test_topics(app, auth, requester):
    auth.login()
    resp = requester.get("/topics/")
    assert isinstance(resp.json['data'], list)
    assert 'next_url' in resp.json
    assert 'prev_url' in resp.json


def test_new_topic(auth, admin, requester):
    auth.login(email=admin.email)
    resp = requester.post("/topics/",
                          json={'title': "test",
                                "min_lesson_number": 1,
                                "max_lesson_number": 4})
    assert resp.json['data']


def test_delete_topic(auth, topic, admin, requester):
    auth.login(email=admin.email)
    resp = requester.delete(f"/topics/{topic.id}")
    assert "deleted" in resp.json["message"]
    assert not Topic.get_by_id(topic.id)
