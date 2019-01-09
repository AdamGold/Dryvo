from tests import AuthActions
from server.error_handling import RouteError, TokenError
import pytest
import flask
import flask_login
from urllib import parse

from server.api.database.models import User, BlacklistToken
from server.api.blueprints.login import handle_facebook


def test_normal_register(app, auth: AuthActions):
    resp = auth.register()
    assert "auth_token" in resp.json
    assert "successfully" in resp.json['message']
    with app.app_context():
        assert User.query.filter_by(email='test@test.com').one()


def test_login_validate_input(auth: AuthActions):
    resp = auth.login("t@aaa.com", "123")
    assert resp.json.get('message') == "Invalid email or password."


def test_encode_auth_token(user):
    auth_token = user.encode_auth_token()
    assert isinstance(auth_token, bytes)


def test_decode_auth_token(user):
    auth_token = user.encode_auth_token()
    assert isinstance(auth_token, bytes)
    assert User.from_token(auth_token.decode("utf-8")) == 1


def test_logout(auth: AuthActions):
    login = auth.login()
    resp = auth.logout()
    print(resp.__dict__)
    assert "Logged out successfully" in resp.json.get("message")
    # check that token was blacklisted
    assert login.json.get("auth_token") == BlacklistToken.query.first().token


def test_blacklist_token(app, auth: AuthActions):
    resp_login = auth.login()
    with app.app_context():
        blacklist_token = BlacklistToken(token=resp_login.json["auth_token"])
        blacklist_token.save()
        resp = auth.logout()
        assert "Token blacklisted" in str(resp.json)


def test_invalid_token(auth: AuthActions):
    resp = auth.logout(headers={"Authorization": "Bearer NOPE"})
    assert "Invalid token" in resp.json.get('message')


@pytest.mark.parametrize(
    ("email", "password", "name", "area", "message"),
    (
        ("", "bb", "test", "test", "Email is required."),
        ("tt@t.com", "", "test", "test", "Password is required."),
        ("ttom", "a", "test", "test", "Email is not valid."),
        ("test", "a", "test", "", "Area is required."),
        ("test", "a", "", "test", "Name is required."),
        ("t@test.com", "a", "a", "A", "Email is already registered.")
    ),
)
def test_register_validate_input(auth: AuthActions, email, password, name, area, message):
    resp = auth.register(email=email, password=password, name=name, area=area)
    assert message in resp.json.get("message")


def test_facebook_first_step(client, auth, requester):
    with client:
        auth.login()
        resp = requester.get("/login/facebook")
        assert resp.status_code == 302  # redirect
        assert flask.session['state']
        auth.logout()
        assert flask_login.current_user.is_authenticated
    assert not flask_login.current_user.is_authenticated


"""def assert_facebook_redirect_url(url, user):
    "Asserts that the url redirecting to the app is correctly formed"
    url = parse.urlsplit(url)
    url_args = dict(parse.parse_qsl(parse.urlsplit(url).query))
    assert User.from_token(url_args["token"]) == user.id

def test_login_with_facebook(client, requester):
    with client:  # to keep the session
        pass


def test_register_with_facebook(client, requester):
    pass


def test_assosicate_with_facebook(client, requester):
    pass


def test_remove_session(client, requester, auth):
    with client:
        auth.login()
        resp = requester.get("/login/facebook")
        print(resp.__dict__)
        handle_facebook(state, code, "test")
        assert not flask_login.current_user.is_authenticated
"""
