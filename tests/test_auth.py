from tests import AuthActions
from server.error_handling import RouteError, TokenError
import pytest
from server.api.database.models import User, BlacklistToken


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
    assert "Logged out successfully" in resp.json.get("message")
    # check that token was blacklisted
    assert login.json.get("auth_token") == BlacklistToken.query.first().token


def test_blacklist_token(app, auth: AuthActions):
    resp_login = auth.login()
    with app.app_context():
        blacklist_token = BlacklistToken(token=resp_login.json["auth_token"])
        blacklist_token.save()
        resp = auth.logout()
        print(resp.json)
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
