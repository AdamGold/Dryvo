import urllib
import contextlib
from typing import Dict, List, Union, ContextManager

import flask
import flask_login
import pytest
from tests import AuthActions

from server.api.blueprints.login import (
    handle_oauth,
    validate_inputs,
    create_or_get_oauth,
)
from server.api.database.models import BlacklistToken, User, OAuth, Provider
from server.api.social import Facebook
from server.error_handling import RouteError, TokenError


@pytest.fixture
def fake_profile():
    return {
        "name": "test",
        "email": "t@t.com",
        "picture": {"data": {"url": "test.jpg"}},
        "provider_user_id": 1111,
    }


@pytest.fixture
def mock_facebook_user_id(responses, fake_profile):
    user_id = {"data": {"user_id": fake_profile["provider_user_id"]}}
    responses.add(
        responses.GET,
        "https://graph.facebook.com/debug_token",
        status=200,
        json=user_id,
    )


@pytest.fixture
def mock_facebook_profile(responses, fake_profile):
    responses.add(
        responses.GET,
        f"https://graph.facebook.com/v3.2/{fake_profile['provider_user_id']}",
        status=200,
        json=fake_profile,
    )


def test_normal_register(app, auth: AuthActions):
    resp = auth.register()
    assert "auth_token" in resp.json
    assert "refresh_token" in resp.json
    assert "user" in resp.json
    with app.app_context():
        assert User.query.filter_by(email="test@test.com").one()


def test_login(user, auth):
    resp = auth.login()
    assert "auth_token" in resp.json
    assert "refresh_token" in resp.json
    assert user.to_dict()["id"] == resp.json["user"]["id"]
    payload = User.decode_token(resp.json["auth_token"])
    assert "email" in payload


def test_login_validate_input(auth: AuthActions):
    resp = auth.login("t@aaa.com", "123")
    assert resp.json.get("message") == "Invalid email or password."


def test_encode_auth_token(user):
    auth_token = user.encode_auth_token()
    assert isinstance(auth_token, bytes)


def test_decode_auth_token(user):
    auth_token = user.encode_auth_token()
    assert isinstance(auth_token, bytes)
    assert User.from_login_token(auth_token.decode("utf-8")) == user


def test_logout(auth: AuthActions):
    login = auth.login()
    resp = auth.logout()
    assert "Logged out successfully" in resp.json.get("message")
    # check that token was blacklisted
    refresh_token = login.json.get("refresh_token")
    auth_token = login.json.get("auth_token")
    assert len(BlacklistToken.query.all()) == 2
    assert all(
        (
            token.token == auth_token or token.token == refresh_token
            for token in BlacklistToken.query.all()
        )
    )


def test_blacklist_token(app, auth: AuthActions):
    resp_login = auth.login()
    with app.app_context():
        blacklist_token = BlacklistToken(token=resp_login.json["auth_token"])
        blacklist_token.save()
        resp = auth.logout()
        assert "BLACKLISTED_TOKEN" in str(resp.json)


def test_invalid_token(auth: AuthActions):
    resp = auth.logout(headers={"Authorization": "Bearer NOPE"})
    assert "INVALID_TOKEN" in resp.json.get("message")


@pytest.mark.parametrize(
    ("email", "password", "name", "area", "message"),
    (
        ("", "bb", "test", "test", "Email is required."),
        ("tt@t.com", "", "test", "test", "Password is required."),
        ("ttom", "a", "test", "test", "Email is not valid."),
        ("test", "a", "test", "", "Area is required."),
        ("test", "a", "", "test", "Name is required."),
        ("t@test.com", "a", "a", "A", "Email is already registered."),
    ),
)
def test_register_validate_input(
    auth: AuthActions, email, password, name, area, message
):
    resp = auth.register(email=email, password=password, name=name, area=area)
    assert message in resp.json.get("message")


def test_facebook_first_step(client, auth, requester):
    with client:
        auth.login()
        resp = requester.get("/login/facebook")
        assert resp.status_code == 302  # redirect
        assert flask.session["state"]
        auth.logout()
        assert flask_login.current_user.is_authenticated
    assert not flask_login.current_user.is_authenticated


def test_exchange_token(requester, user: User):
    resp = requester.post(
        "/login/exchange_token",
        json={"exchange_token": user.encode_exchange_token().decode()},
    )
    assert "user" in resp.json
    assert "auth_token" in resp.json
    assert user == User.from_login_token(resp.json["auth_token"])


def test_refresh_token_payload(auth, user: User):
    """check that refresh token after login
    has a scope and a user_id"""
    resp = auth.login()
    assert resp.json["refresh_token"]
    payload = User.decode_token(resp.json["refresh_token"])
    assert payload["scope"]
    assert User.from_payload(payload) == user


def test_refresh_token_endpoint(auth, requester):
    """check that a valid refresh token
    generates a new auth token, and an invalid token
    doesn't"""
    auth.login()
    resp = requester.post(
        "/login/refresh_token", json={"refresh_token": auth.refresh_token}
    )
    assert resp.json["auth_token"]
    resp = requester.post("/login/refresh_token", json={"refresh_token": "none"})
    assert "INVALID_TOKEN" in resp.json["message"]


def test_refresh_without_refresh_token(requester):
    """call refresh endpoint without token"""
    resp = requester.post("/login/refresh_token", json={"refresh_token": ""})
    assert "INAVLID_REFRESH_TOKEN" == resp.json["message"]


def test_validate_inputs():
    with pytest.raises(RouteError):
        validate_inputs({"name": "test", "area": "test", "email": "test"})
        validate_inputs({"name": "test"})
    assert validate_inputs({"name": "test", "area": "test"}, all_required=False)


def test_edit_data(app, user, requester, auth: AuthActions):
    auth.login()
    resp = requester.post("/login/edit_data", json={"name": "new"})
    assert "new" == resp.json["data"]["name"]
    assert user.area == resp.json["data"]["area"]
    resp = requester.post("/login/edit_data", json={"area": "new"})
    assert "new" == resp.json["data"]["area"]
    assert requester.post("/login/edit_data", json={})
    assert requester.post("/login/edit_data", json={"password": "new"})


def test_register_with_facebook(
    app: flask.Flask,
    fake_profile,
    mock_facebook_user_id,
    mock_facebook_profile,
    fake_token,
):
    """Tests that a new user was registered"""
    with app.test_request_context("/"):
        resp = handle_oauth(Facebook, fake_token)
        user = User.query.filter_by(name=fake_profile["name"]).first()
        assert user.email
        assert "token=" in resp.headers["Location"]


def test_login_with_facebook(
    app: flask.Flask, fake_token, user, mock_facebook_user_id, fake_profile, requester
):
    length = len(User.query.all())
    OAuth.create(
        provider=Provider.facebook,
        provider_user_id=fake_profile["provider_user_id"],
        token=fake_token,
        user=user,
    )
    with app.test_request_context("/"):
        resp = handle_oauth(Facebook, fake_token)
        assert len(User.query.all()) == length
        assert "token" in resp.headers["Location"]


def test_facebook_no_token():
    resp = handle_oauth(Facebook, None)
    assert urllib.parse.quote("No token") in resp.headers["Location"]


@contextlib.contextmanager
def logged_in_context(app, auth, endpoint="", **kwargs) -> ContextManager[None]:
    """A manager to enter and exit a logged-in request context"""
    auth.login(**kwargs)
    with app.test_request_context(
        f"/{endpoint}", headers={"Authorization": f"Bearer {auth.auth_token}"}
    ) as fp:
        yield fp
        auth.logout()


def test_oauth_session(
    app: flask.Flask, auth, fake_token, mock_facebook_profile, mock_facebook_user_id
):
    with logged_in_context(app, auth, "login/facebook"):
        assert flask_login.current_user.is_authenticated
        handle_oauth(Facebook, fake_token)
        assert not flask_login.current_user.is_authenticated


def test_create_or_get_oauth(user, app, fake_profile, fake_token):
    with app.app_context():
        oauth = create_or_get_oauth(
            "facebook", fake_profile["provider_user_id"], fake_token
        )
        assert oauth.token == fake_token
        OAuth.create(
            provider=Provider.facebook,
            provider_user_id=fake_profile["provider_user_id"],
            token=fake_token,
            user=user,
        )
        oauth = create_or_get_oauth(
            "facebook", fake_profile["provider_user_id"], fake_token
        )
        assert oauth.user == user
