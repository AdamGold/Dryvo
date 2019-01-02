from tests import AuthActions
from server.api.utils import RouteError, TokenError
import pytest
from server.api.database.models import User, BlacklistToken

def test_normal_register(auth: AuthActions):
    resp = auth.register()
    assert "auth_token" in resp.json
    assert "successfully" in resp.json['message']


def test_login_validate_input(auth):
    with pytest.raises(RouteError):
        resp = auth.login("t@aaa.com", "123")
        assert resp.json.get('message') == "Invalid email or password."


def test_encode_auth_token(user):
    auth_token = user.encode_auth_token()
    assert isinstance(auth_token, bytes)


def test_decode_auth_token(user):
    auth_token = user.encode_auth_token()
    assert isinstance(auth_token, bytes)
    assert User.from_token(auth_token.decode("utf-8")) == 1


def test_logout(requester, auth):
    login = auth.login()

    with requester:
        resp = auth.logout()
        assert "Logged out successfuly" in resp.json.get("message")
        # check that token was blacklisted
        assert login.json.get("auth_token") == BlacklistToken.query.first().token


def test_blacklist_token(requester, auth):
    with requester:
        resp_login = auth.login()
        blacklist_token = BlacklistToken(token=resp_login.json["auth_token"])
        blacklist_token.save()
        with pytest.raises(TokenError) as e:
            auth.logout()
        assert "Token blacklisted" in str(e)


def test_invalid_token(auth, requester):
    with requester:
        with pytest.raises(TokenError) as e:
            auth.get("/login/logout", headers={"Authorization": "Bearer NOPE"})
        assert "Invalid token" in str(e)


@pytest.mark.parametrize(
    ("email", "password", "name", "area", "message"),
    (
        ("", "bb", "test", "test", "Email is required."),
        ("tt@t.com", "", "test", "test", "Password is required."),
        ("ttom", "", "test", "test", "Not a valid email."),
        ("test", "a", "test", "", "Area is taken"),
        ("test", "a", "", "test", "Name is taken"),
    ),
)
def test_register_validate_input(requester, email, password, name, area, message):
    with pytest.raises(RouteError) as e:
        requester.post(
            "/api/register", data={"email": email, "password": password, "name": name, "area": area}
        )
    assert message in e.value.json.get("message")
