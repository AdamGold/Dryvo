import pytest
import flask
import flask.testing
import tempfile
import json

from server.extensions import db
from server.api.database.models import User
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
            setup_db(db)

        yield app


def setup_db(db_instance):
    user = User(email='t@test.com', password='test', name='test', area='test')
    user.save()


@pytest.fixture
def db_instance(app: flask.Flask):
    with app.app_context():
        yield db


@pytest.fixture
def user(app: flask.Flask):
    with app.app_context():
        yield User.query.filter_by(username='test').one()


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
        return self._client.post(
            '/login/direct',
            json={'email': email, 'password': password}
        )

    def register(self, email='test@test.com', password='test', name='test', area='test'):
        return self._client.post(
            'login/register',
            json={'email': email, 'password': password,
                  'name': name, 'area': area}
        )

    def logout(self):
        return self._client.get('/login/logout')


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def requester(client):
    return Requester(client)


@pytest.fixture
def auth(requester):
    return AuthActions(requester)
