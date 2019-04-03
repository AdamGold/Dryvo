from typing import Type

import flask
import requests
from loguru import logger

from server.api.social.social_network import SocialNetwork
from server.consts import DEBUG_MODE, MOBILE_LINK, PROFILE_SIZE
from server.error_handling import RouteError


class Facebook(SocialNetwork):
    network_name = "facebook"
    authorization_url = "https://www.facebook.com/v3.2/dialog/oauth"
    base_url = "https://graph.facebook.com/"
    token_metadata_url = "debug_token"
    token_url = "v3.2/oauth/access_token"
    scopes = "email"

    @classmethod
    def auth_url(cls, state: str) -> str:
        redirect = flask.url_for(".facebook_authorized", _external=True)
        return "{}?client_id={}" "&redirect_uri={}&state={}&scope={}".format(
            cls.authorization_url,
            flask.current_app.config.get("FACEBOOK_CLIENT_ID"),
            redirect,
            state,
            cls.scopes,
        )

    @classmethod
    def access_token(cls, state: str, code: str) -> str:
        if state != flask.session.get("state") and not DEBUG_MODE:
            raise RouteError("INVALID_STATE")

        redirect = flask.url_for(
            ".facebook_authorized", _external=True
        )  # the url we are on
        token_url = (
            "{}{}?client_id="
            "{}&redirect_uri={}&client_secret={}&code={}".format(
                cls.base_url,
                cls.token_url,
                flask.current_app.config.get("FACEBOOK_CLIENT_ID"),
                redirect,
                flask.current_app.config.get("FACEBOOK_CLIENT_SECRET"),
                code,
            )
        )

        access_token = requests.get(token_url).json().get("access_token")
        return access_token

    @classmethod
    def token_metadata(cls, access_token: str):
        url = "{}{}?input_token={}&access_token={}".format(
            cls.base_url,
            cls.token_metadata_url,
            access_token,
            flask.current_app.config.get("FACEBOOK_TOKEN"),
        )

        request = requests.get(url).json()
        return request["data"]["user_id"]

    @classmethod
    def profile(cls, user_id: int, access_token: str):
        request = requests.get(
            f"{cls.base_url}{user_id}?"
            f"fields=email,name,picture.width({PROFILE_SIZE}).height({PROFILE_SIZE})&access_token={access_token}"
        ).json()
        return request
