import pytest
import flask
import tempfile

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
