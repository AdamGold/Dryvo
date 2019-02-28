import json
import tempfile
from datetime import datetime, timedelta

import flask
import flask.testing
import pytest
import json
from pathlib import Path

from server import create_app
from server.api.database import db, reset_db
from server.api.database.models import (
    Lesson,
    Place,
    PlaceType,
    Student,
    Teacher,
    Topic,
    User,
    WorkDay,
)


@pytest.fixture
def app() -> flask.Flask:
    with open(Path.cwd() / "tests" / "service-account.json", "r") as f:
        firebase_json = f.read()
    with tempfile.NamedTemporaryFile() as db_f:
        # create the app with common test config
        app = create_app(
            TESTING=True,
            SECRET_KEY="VERY_SECRET",
            SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_f.name}",
            FIREBASE_JSON=firebase_json,
            SECRET_JWT="VERY_VERY_SECRET",
            FLASK_DEBUG=1,
            FACEBOOK_TOKEN="test",
            FACEBOOK_CLIENT_SECRET="test",
            FACEBOOK_CLIENT_ID="test",
        )

        with app.app_context():
            db.init_app(app)
            reset_db(db)
            setup_db(app)

        yield app


def setup_db(app):
    User.create(email="t@test.com", password="test", name="test", area="test")
    User.create(
        email="admin@test.com",
        password="test",
        name="admin",
        area="test",
        is_admin=True,
    )
    teacher_user = User.create(
        email="teacher@test.com", password="test", name="teacher", area="test"
    )
    teacher = Teacher.create(
        user_id=teacher_user.id, price=100, phone="055555555", lesson_duration=40
    )
    student_user = User.create(
        email="student@test.com", password="test", name="student", area="test"
    )
    student = Student.create(
        user_id=student_user.id, teacher_id=teacher.id, is_approved=True
    )
    meetup = Place.create(name="test", used_as=PlaceType.meetup.value, student=student)
    dropoff = Place.create(
        name="test", used_as=PlaceType.dropoff.value, student=student
    )
    WorkDay.create(
        teacher=teacher,
        day=1,
        from_hour=00,
        to_hour=23,
        to_minutes=59,
        on_date=(datetime.utcnow() + timedelta(days=2)).date(),
    )  # 2 days from now
    Topic.create(title="topic test", min_lesson_number=1, max_lesson_number=5)
    Lesson.create(
        teacher=teacher,
        student=student,
        # schedule to 5 days from now to it won't bother with no test
        creator=teacher.user,
        duration=40,
        date=(datetime.utcnow() + timedelta(days=5)),
        meetup_place=meetup,
        dropoff_place=dropoff,
    )


@pytest.fixture
def db_instance(app: flask.Flask):
    with app.app_context():
        yield db


@pytest.fixture
def user(app: flask.Flask):
    with app.app_context():
        return User.query.filter_by(email="t@test.com").one()


@pytest.fixture
def admin(app: flask.Flask):
    with app.app_context():
        return User.query.filter_by(email="admin@test.com").one()


class Requester:
    def __init__(self, client):
        self.headers = {"Authorization": ""}
        self._client = client

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def put(self, url, **kwargs):
        return self.request("PUT", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request("DELETE", url, **kwargs)

    def request(self, method, url, **kwargs):
        # overwrite instance auth header with the params?
        if "headers" in kwargs:
            self.headers.update(kwargs.pop("headers"))
        return self._client.open(url, method=method, headers=self.headers, **kwargs)


class AuthActions(object):
    def __init__(self, client):
        self._client = client
        self.refresh_token = ""

    def login(self, email="t@test.com", password="test"):
        return self.start_auth_session(
            "POST", "/login/direct", json={"email": email, "password": password}
        )

    def register(
        self, email="test@test.com", password="test", name="test", area="test"
    ):
        return self.start_auth_session(
            "POST",
            "/login/register",
            json={"email": email, "password": password, "name": name, "area": area},
        )

    def logout(self, **kwargs):
        logout = self._client.post(
            "/login/logout", json={"refresh_token": self.refresh_token}, **kwargs
        )
        self._client.headers["Authorization"] = ""
        return logout

    def start_auth_session(self, method, endpoint, **kwargs):
        """ Inserts the response token to the header
        for continue using that instance as authorized user"""
        req = self._client.request(method, endpoint, **kwargs)
        auth_token = req.json.get("auth_token")
        self.refresh_token = req.json.get("refresh_token")
        if auth_token:
            self._client.headers["Authorization"] = "Bearer " + auth_token
        return req


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def requester(client):
    return Requester(client)


@pytest.fixture
def auth(requester):
    return AuthActions(requester)


@pytest.fixture
def teacher(app):
    return Teacher.query.first()


@pytest.fixture
def student(app):
    return Student.query.first()


@pytest.fixture
def meetup(app, student):
    return (
        Place.query.filter_by(student=student)
        .filter_by(used_as=PlaceType.meetup.value)
        .first()
    )


@pytest.fixture
def dropoff(app, student):
    return (
        Place.query.filter_by(student=student)
        .filter_by(used_as=PlaceType.dropoff.value)
        .first()
    )


@pytest.fixture
def topic(app):
    return Topic.query.first()


@pytest.fixture
def lesson(app):
    return Lesson.query.first()
