import pytest
from datetime import datetime
from loguru import logger

from server.api.database.models import Stage, Topic


def test_stages(app, auth, requester, stage: Stage):
    auth.login()
    resp = requester.get("/stages/")
    assert isinstance(resp.json['data'], list)
    assert 'next_url' in resp.json
    assert 'prev_url' in resp.json


def test_new_topic(auth, admin, requester, stage: Stage):
    auth.login(email=admin.email)
    resp = requester.post("/stages/topic",
                          json={'title': "test",
                                "order": 1,
                                "stage_id": stage.id})
    assert 'successfully' in resp.json['message']
    assert resp.json['data']
    resp = requester.post("/stages/topic",
                          json={'title': "test",
                                "order": 1,
                                "stage_id": 100})
    assert "not exist" in resp.json['message']


def test_new_stage(auth, admin, requester):
    auth.login(email=admin.email)
    resp = requester.post("/stages/",
                          json={'title': "test",
                                "order": 1, })
    assert 'successfully' in resp.json['message']
    assert resp.json['data']
