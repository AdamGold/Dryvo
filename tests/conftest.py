import json
import random
import string
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import flask
import flask.testing
import pytest
import responses as responses_module

from server import create_app
from server.api.database import close_db, db, reset_db
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
from server.api.social import SocialNetwork, social_networks_classes

DEMO_API_KEY = "ccbd100c5bcd1b3d31aaa33851917ca45a251d41988d6c6a3a9e0c68b13d47c2"


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
            close_db()


def setup_db(app):
    User.create(
        email="t@test.com", password="test", name="test", area="test", phone="044444444"
    )
    User.create(
        email="admin@test.com",
        password="test",
        name="admin",
        area="test",
        is_admin=True,
        phone="055555555",
    )
    teacher_user = User.create(
        email="teacher@test.com", password="test", name="teacher", area="test"
    )
    teacher = Teacher.create(
        user=teacher_user,
        price=100,
        lesson_duration=40,
        is_approved=True,
        crn=999999999,
        invoice_api_key=DEMO_API_KEY,
    )
    student_user = User.create(
        email="student@test.com", password="test", name="student", area="test"
    )
    student = Student.create(
        user=student_user, teacher=teacher, creator=teacher.user, is_approved=True
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
        yield User.query.filter_by(email="t@test.com").one()


@pytest.fixture
def admin(app: flask.Flask):
    with app.app_context():
        yield User.query.filter_by(email="admin@test.com").one()


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
        self.auth_token = ""

    def login(self, email="t@test.com", password="test"):
        return self.start_auth_session(
            "POST", "/login/direct", json={"email": email, "password": password}
        )

    def register(
        self,
        email="test@test.com",
        password="test",
        name="test",
        area="test",
        phone="0511111111",
    ):
        return self.start_auth_session(
            "POST",
            "/login/register",
            data={
                "email": email,
                "password": password,
                "name": name,
                "area": area,
                "phone": phone,
            },
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
        self.auth_token = req.json.get("auth_token")
        self.refresh_token = req.json.get("refresh_token")
        if self.auth_token:
            self._client.headers["Authorization"] = "Bearer " + self.auth_token
        return req


class TestClient(flask.testing.FlaskClient):
    """Fix for SQLAlchemy sessions
    https://stackoverflow.com/questions/51016103/unable-to-retrieve-database-objects-in-flask-test-case-session"""

    def open(self, *args, **kwargs):
        if "json" in kwargs:
            kwargs["data"] = json.dumps(kwargs.pop("json"))
            kwargs["content_type"] = "application/json"
        return super(TestClient, self).open(*args, **kwargs)


@pytest.fixture
def client(app):
    app.test_client_class = TestClient
    return app.test_client()


@pytest.fixture
def requester(client):
    return Requester(client)


@pytest.fixture
def auth(requester):
    return AuthActions(requester)


@pytest.fixture
def teacher(app):
    with app.app_context():
        yield Teacher.query.first()


@pytest.fixture
def student(app):
    with app.app_context():
        yield Student.query.first()


@pytest.fixture
def meetup(app, student):
    with app.app_context():
        yield (
            Place.query.filter_by(student=student)
            .filter_by(used_as=PlaceType.meetup.value)
            .first()
        )


@pytest.fixture
def dropoff(app, student):
    with app.app_context():
        yield (
            Place.query.filter_by(student=student)
            .filter_by(used_as=PlaceType.dropoff.value)
            .first()
        )


@pytest.fixture
def topic(app):
    with app.app_context():
        yield Topic.query.first()


@pytest.fixture
def lesson(app):
    with app.app_context():
        yield Lesson.query.first()


@pytest.fixture
def fake_token():
    return "".join(
        [random.choice(string.ascii_letters + string.digits) for n in range(32)]
    )


@pytest.fixture
def responses():
    with responses_module.RequestsMock() as rsps:
        yield rsps


@pytest.fixture(params=social_networks_classes)
def social_network(request) -> SocialNetwork:
    return request.param
