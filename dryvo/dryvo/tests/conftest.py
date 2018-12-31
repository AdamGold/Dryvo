import pytest
import flask
import tempfile


@pytest.fixture
def app() -> flask.Flask:
    with tempfile.NamedTemporaryFile() as db_f:
        # create the app with common test config
        app = create_app(
            TESTING=True,
            DATABASE=db_f.name,
            SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_f.name}",
            JWT_SECRET='SUPER_SECRET',
        )

        with app.app_context():
            init_db()
            setup_db()

        yield app

def setup_db():
    user = User.create_from_credentials(
        username='test', password='test')
    get_db().session.add(user)
    network_names = social_networks.keys()
    for network_name in network_names:
        get_db().session.add(Network(external_id=0,
                                     network_name=network_name, user=user))
        fake_token = generate_fake_token(generate_fake_person(network_name))
        get_db().session.add(OAuth(provider=network_name,
                                   token=fake_token, external_user_id=0, user=user))
    get_db().session.commit()


@pytest.fixture
def db_instance(app: flask.Flask):
    with app.app_context():
        yield get_db()


@pytest.fixture
def user(app: flask.Flask):
    with app.app_context():
        yield User.query.filter_by(username='test').one()