import os
import random
import re
import string
from typing import Tuple, Type

import flask
from cloudinary.uploader import upload
from flask import Blueprint
from flask_login import current_user, login_required, login_user, logout_user
from loguru import logger
from sqlalchemy.orm.exc import NoResultFound

from server.api.database.models import BlacklistToken, OAuth, Provider, TokenScope, User
from server.api.social import Facebook, SocialNetwork
from server.api.utils import jsonify_response, must_redirect
from server.consts import DEBUG_MODE
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
    email = data.get("email")
    if not email:
        raise RouteError("Email is required.")
    email = email.lower()
    user = User.query.filter_by(email=email).first()
    # Try to authenticate the found user using their password
    if user and user.check_password(data.get("password")):
        tokens = user.generate_tokens()
        return dict(**tokens, **{"user": user.to_dict()})
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


def validate_inputs(data, all_required=True) -> Tuple[str, str, str, str]:
    email: str = data.get("email")
    if email:
        email = email.lower()
    name: str = data.get("name")
    area: str = data.get("area")
    password: str = data.get("password")
    if all_required:
        if not name:
            raise RouteError("Name is required.")
        if not area:
            raise RouteError("Area is required.")
        if not password:
            raise RouteError("Password is required.")
        if not email:
            raise RouteError("Email is required.")
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise RouteError("Email is not valid.")

    return (name, area, email, password, data.get("phone"))


@login_routes.route("/register", methods=["POST"])
@jsonify_response
def register():
    post_data = flask.request.values
    (name, area, email, password, phone) = validate_inputs(post_data)
    image = flask.request.files.get("image")
    # Query to see if the user already exists
    user = User.query.filter_by(email=email).first()
    if not user:
        # There is no user so we'll try to register them
        # Register the user
        user = User(email=email, password=password, name=name, area=area, phone=phone)
        if image:
            try:
                user.image = upload(image)["public_id"]
            except Exception:
                raise RouteError("Image could not be uploaded.")
        user.save()
        # generate auth token
        tokens = user.generate_tokens()
        return dict(**tokens, **{"user": user.to_dict()}), 201
    # There is an existing user. We don't want to register users twice
    # Return a message to the user telling them that they they already exist
    raise RouteError("Email is already registered.")


@login_routes.route("/edit_data", methods=["POST"])
@jsonify_response
@login_required
def edit_data():
    post_data = flask.request.get_json()
    (name, area, _, password, phone) = validate_inputs(post_data, all_required=False)
    user = User.query.filter_by(email=current_user.email).first()
    if not user:
        raise RouteError("User was not found.")
    if name:
        user.name = name
    if area:
        user.area = area
    if password:
        user.set_password(password)
    if phone:
        user.phone = phone

    user.save()
    return {"data": user.to_dict()}


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
    # Store the state so the callback can verify the auth server response.
    state = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    flask.session["state"] = state
    return flask.redirect(Facebook.auth_url(state))


@login_routes.route("/facebook/authorized", methods=["GET"])
def facebook_authorized():
    # TODO handle association of a network when a user is already logged in
    return oauth_process(Facebook)


def oauth_process(network: Type[SocialNetwork]):
    data = flask.request.values
    access_token = network.access_token(data.get("state"), data.get("code"))
    logger.debug(f"got access token {access_token}")
    return handle_oauth(network, access_token)


@must_redirect
def handle_oauth(network: Type[SocialNetwork], access_token: str):
    if not access_token:
        raise RouteError("No token received.")
    network_user_id = network.token_metadata(access_token)
    oauth = create_or_get_oauth(network.network_name, network_user_id, access_token)
    user = oauth.user
    if not user:
        profile = network.profile(network_user_id, access_token)
        logger.debug(f"profile of user is {profile}")

        if not profile.get("email"):
            raise RouteError("Can not get email from user.")

        try:
            image_url = profile["picture"]["data"].get("url")
            logger.info(f"Uploading {image_url} to Cloudinary...")
            image = upload(image_url)["public_id"]
        except Exception:
            image = ""
        # Create a new local user account for this user
        user = User(
            email=profile.get("email"), name=profile.get("name"), image=image
        ).save()
        oauth.user = user
        oauth.save()
        logger.debug(f"creating new user {user}")

    exchange_token = user.encode_exchange_token().decode()
    logger.debug("Logging out of session")
    logout_user()
    return {"token": exchange_token}


def create_or_get_oauth(provider_name: str, user_id: int, access_token: str) -> OAuth:
    # Find this OAuth token in the database, or create it
    provider = getattr(Provider, provider_name)
    query = OAuth.query.filter_by(provider=provider, provider_user_id=user_id)
    try:
        logger.debug(f"found existing oauth row")
        return query.one()
    except NoResultFound:
        logger.debug(f"Creating new oauth row")
        return OAuth(provider=provider, provider_user_id=user_id, token=access_token)
