import flask
import requests
from loguru import logger

from server.consts import DEBUG_MODE, FACEBOOK_SCOPES, MOBILE_LINK
from server.error_handling import RouteError
from server.api.social.social_network import SocialNetwork
from server.consts import PROFILE_SIZE

BASE_URL = "https://graph.facebook.com/v3.2"


class Facebook(SocialNetwork):
    @staticmethod
    def auth_url(state):
        redirect = flask.url_for(".facebook_authorized", _external=True)
        return (
            "https://www.facebook.com/v3.2/dialog/oauth?client_id={}"
            "&redirect_uri={}&state={}&scope={}".format(
                flask.current_app.config.get("FACEBOOK_CLIENT_ID"),
                redirect,
                state,
                FACEBOOK_SCOPES,
            )
        )

    @staticmethod
    def access_token(state: str, code) -> str:
        if state != flask.session.get("state") and not DEBUG_MODE:
            raise RouteError("INVALID_STATE")

        logger.debug("State is valid, moving on")

        redirect = flask.url_for(
            ".facebook_authorized", _external=True
        )  # the url we are on
        token_url = (
            f"{BASE_URL}/oauth/access_token?client_id="
            "{}&redirect_uri={}&client_secret={}&code={}".format(
                flask.current_app.config.get("FACEBOOK_CLIENT_ID"),
                redirect,
                flask.current_app.config.get("FACEBOOK_CLIENT_SECRET"),
                code,
            )
        )

        access_token = requests.get(token_url).json().get("access_token")
        return access_token

    @staticmethod
    def user_id(access_token: str):
        url = "https://graph.facebook.com/debug_token?input_token={}&access_token={}".format(
            access_token, flask.current_app.config.get("FACEBOOK_TOKEN")
        )

        request = requests.get(url).json()
        logger.debug(f"trying to get user id, got {request}")
        return request["data"]["user_id"]

    @staticmethod
    def profile(user_id: int, access_token: str):
        request = requests.get(
            f"{BASE_URL}/{user_id}?"
            f"fields=email,name,picture.width({PROFILE_SIZE}).height({PROFILE_SIZE})&access_token={access_token}"
        ).json()
        return request
