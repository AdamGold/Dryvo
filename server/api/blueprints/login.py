import os
import random
import re
import string

import flask
import requests
from flask import Blueprint
from flask_login import current_user, login_required, login_user, logout_user
from loguru import logger
from sqlalchemy.orm.exc import NoResultFound

from server.api.blueprints.user import get_user_info
from server.api.database.models import BlacklistToken, OAuth, Provider, TokenScope, User
from server.api.utils import jsonify_response
from server.consts import DEBUG_MODE, FACEBOOK_SCOPES, MOBILE_LINK
from server.error_handling import RouteError, TokenError
from server.extensions import login_manager

login_routes = Blueprint("login", __name__, url_prefix="/login")


def init_app(app):
    app.register_blueprint(login_routes)


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    return User.query.filter_by(id=int(user_id)).first()


@login_manager.request_loader
def load_user_from_request(request):
    # get the auth token
    if not request.headers.get("Authorization"):
        return None
    return token_tuple(request)[1]


def token_tuple(request):
    auth_header = request.headers.get("Authorization")
    try:
        auth_token = auth_header.split(" ")[1]
    except IndexError:
        raise TokenError("INVALID_TOKEN")
    return auth_token, User.from_login_token(auth_token)


@login_routes.route("/direct", methods=["POST"])
@jsonify_response
def direct_login():
    data = flask.request.get_json()
    user = User.query.filter_by(email=data.get("email")).first()
    # Try to authenticate the found user using their password
    if user and user.check_password(data.get("password")):
        tokens = user.generate_tokens()
        user_dict = dict(**user.to_dict(), **get_user_info(user))
        return dict(**tokens, **{"user": user_dict})
    # User does not exist. Therefore, we return an error message
    raise RouteError("Invalid email or password.", 401)


@login_routes.route("/logout", methods=["POST"])
@jsonify_response
@login_required
def logout():
    data = flask.request.get_json()
    (auth_token, _) = token_tuple(flask.request)
    if not data["refresh_token"]:
        raise TokenError("INVALID_REFRESH_TOKEN")
    # mark all tokens as blacklisted
    BlacklistToken.create(token=auth_token)
    BlacklistToken.create(token=data["refresh_token"])
    return {"message": "Logged out successfully."}


@login_routes.route("/register", methods=["POST"])
@jsonify_response
def register():
    post_data = flask.request.get_json()
    email = post_data.get("email")
    name = post_data.get("name")
    area = post_data.get("area")
    password = post_data.get("password")
    if not email:
        raise RouteError("Email is required.")
    if not name:
        raise RouteError("Name is required.")
    if not area:
        raise RouteError("Area is required.")
    if not password:
        raise RouteError("Password is required.")
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        raise RouteError("Email is not valid.")
    # Query to see if the user already exists
    user = User.query.filter_by(email=email).first()
    if not user:
        # There is no user so we'll try to register them
        # Register the user
        user = User(email=email, password=password, name=name, area=area)
        user.save()
        # generate auth token
        tokens = user.generate_tokens()
        return dict(**tokens, **{"user": user.to_dict()}), 201
    # There is an existing user. We don't want to register users twice
    # Return a message to the user telling them that they they already exist
    raise RouteError("Email is already registered.")


@login_routes.route("/facebook", methods=["GET"])
def oauth_facebook():
    """setup Facebook API, redirect to facebook login & permissions
    when redirected back, check auth code and setup a server session
    with credentials
    """
    # If authenticated from JWT, login using a session
    # and blacklist token
    auth_token = flask.request.values.get("token")
    if auth_token:
        user = User.from_login_token(auth_token)
        BlacklistToken.create(token=auth_token)
        logger.debug("logged wih token, creating session...")
        login_user(user, remember=True)
    state = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    redirect = flask.url_for(".facebook_authorized", _external=True)
    auth_url = (
        "https://www.facebook.com/v3.2/dialog/oauth?client_id={}"
        "&redirect_uri={}&state={}&scope={}".format(
            flask.current_app.config.get("FACEBOOK_CLIENT_ID"),
            redirect,
            state,
            FACEBOOK_SCOPES,
        )
    )
    # Store the state so the callback can verify the auth server response.
    flask.session["state"] = state
    return flask.redirect(auth_url)


@login_routes.route("/exchange_token", methods=["POST"])
@jsonify_response
def exchange_token():
    args = flask.request.get_json()
    payload = User.decode_token(args["exchange_token"])
    if payload["scope"] != TokenScope.EXCHANGE.value:
        raise TokenError("INVALID_EXCHANGE_TOKEN")
    user = User.from_payload(payload)
    logger.debug(f"{user} exchanged auth token")
    tokens = user.generate_tokens()
    return dict(**tokens, **{"user": user.to_dict()})


@login_routes.route("/refresh_token", methods=["POST"])
@jsonify_response
def refresh_token():
    args = flask.request.get_json()
    if not args.get("refresh_token"):
        raise RouteError("INAVLID_REFRESH_TOKEN")
    payload = User.decode_token(args["refresh_token"])
    if payload["scope"] != TokenScope.REFRESH.value:
        raise TokenError("INAVLID_REFRESH_TOKEN")
    user = User.from_payload(payload)
    return {"auth_token": user.encode_auth_token().decode()}


@login_routes.route("/facebook/authorized", methods=["GET"])
def facebook_authorized():
    data = flask.request.values
    return handle_facebook(state=data.get("state"), code=data.get("code"))


def handle_facebook(state, code):
    if state != flask.session.get("state") and not DEBUG_MODE:
        raise RouteError("INVALID_STATE")

    logger.debug("State is valid, moving on")

    redirect = flask.url_for(
        ".facebook_authorized", _external=True
    )  # the url we are on
    token_url = (
        "https://graph.facebook.com/v3.2/oauth/access_token?client_id="
        "{}&redirect_uri={}&client_secret={}&code={}".format(
            flask.current_app.config.get("FACEBOOK_CLIENT_ID"),
            redirect,
            flask.current_app.config.get("FACEBOOK_CLIENT_SECRET"),
            code,
        )
    )
    access_token = requests.get(token_url).json().get("access_token")

    logger.debug(f"got access token {access_token}")

    url = "https://graph.facebook.com/debug_token?input_token={}&access_token={}".format(
        access_token, flask.current_app.config.get("FACEBOOK_TOKEN")
    )

    validate_token_resp = requests.get(url).json()["data"]

    # Find this OAuth token in the database, or create it
    query = OAuth.query.filter_by(
        provider=Provider.facebook, provider_user_id=validate_token_resp.get("user_id")
    )

    try:
        oauth = query.one()
        logger.debug(f"found existing oauth row {oauth}")
    except NoResultFound:
        oauth = OAuth(
            provider=Provider.facebook,
            provider_user_id=validate_token_resp.get("user_id"),
            token=access_token,
        )
        logger.debug(f"Creating new oauth row {oauth}")

    user = oauth.user
    if not user:
        profile = requests.get(
            "https://graph.facebook.com/v3.2/{}?"
            "fields=email,name&access_token={}".format(
                validate_token_resp.get("user_id"), access_token
            )
        ).json()

        logger.debug(f"profile of user is {profile}")

        if not profile.get("email"):
            raise RouteError("Can not get email from user.")

        # Create a new local user account for this user
        user = User(email=profile.get("email"), name=profile.get("name")).save()
        oauth.user = user
        oauth.save()
        logger.debug(f"creating new user {user}")

    exchange_token = user.encode_exchange_token().decode()
    logger.debug("Logging out of session")
    logout_user()
    logger.debug(f"redirecting {user} to {MOBILE_LINK}?token=TOKEN")
    return flask.redirect(f"{MOBILE_LINK}?token={exchange_token}")
