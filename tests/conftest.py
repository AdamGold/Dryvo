import pytest
import flask
import flask.testing
import tempfile
import json

from server.api.database import db
from server.api.database.models import User, Student, Teacher
from server import create_app, init_db


@pytest.fixture
def app() -> flask.Flask:
    with tempfile.NamedTemporaryFile() as db_f:
        # create the app with common test config
        app = create_app(
            TESTING=True,
            SECRET_KEY='VERY_SECRET',
            SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_f.name}",
            JWT_SECRET='SUPER_SECRET',
        )

        with app.app_context():
            db.init_app(app)
            init_db(db)
            setup_db(app)

        yield app


def setup_db(app):
    with app.app_context():
        User(email='t@test.com', password='test', name='test', area='test').save()
        User(email='admin@test.com', password='test', name='admin', area='test', is_admin=True).save()
        teacher_user = User(email='teacher@test.com', password='test', name='teacher', area='test').save()
        teacher = Teacher(user_id=teacher_user.id, price=100, phone="055555555",
                          lesson_duration=40).save()
        student_user = User(email='student@test.com', password='test', name='student', area='test').save()
        Student(user_id=student_user.id, teacher_id=teacher.id).save()


@pytest.fixture
def db_instance(app: flask.Flask):
    with app.app_context():
        yield db


@pytest.fixture
def user(app: flask.Flask):
    with app.app_context():
        return User.query.filter_by(email='t@test.com').one()


@pytest.fixture
def admin(app: flask.Flask):
    with app.app_context():
        return User.query.filter_by(email='admin@test.com').one()


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

    def request(self, method, url, **kwargs):
        # overwrite instance auth header with the params?
        if 'headers' in kwargs:
            self.headers.update(kwargs.pop("headers"))
        return self._client.open(url, method=method, headers=self.headers, **kwargs)

    def start_auth_session(self, method, endpoint, **kwargs):
        """ Inserts the response token to the header
        for continue using that instance as authorized user"""
        req = self.request(method, endpoint, **kwargs)
        auth_token = req.json.get("auth_token")
        if auth_token:
            self.headers["Authorization"] = "Bearer " + auth_token
        return req


class AuthActions(object):
    def __init__(self, client):
        self._client = client

    def login(self, email='t@test.com', password='test'):
        return self._client.start_auth_session("POST",
                                               '/login/direct',
                                               json={'email': email, 'password': password})

    def register(self, email='test@test.com', password='test', name='test', area='test'):
        return self._client.start_auth_session("POST",
                                               '/login/register',
                                               json={'email': email, 'password': password,
                                                     'name': name, 'area': area})

    def logout(self, **kwargs):
        logout = self._client.get('/login/logout', **kwargs)
        self._client.headers['Authorization'] = ''
        return logout


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
    with app.app_context():
        yield Teacher.query.filter_by(user_id=3).one()


@pytest.fixture
def student(app):
    with app.app_context():
        yield Student.query.filter_by(user_id=4).one()
