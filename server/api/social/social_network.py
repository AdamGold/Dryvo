import abc


class SocialNetwork(abc.ABC):
    """Social network abstract class"""

    @staticmethod
    @abc.abstractmethod
    def auth_url(state):
        """return auth url of provider for oauth"""

    @staticmethod
    @abc.abstractmethod
    def access_token(state: str, code: str) -> str:
        """get access token by code given in URL"""

    @staticmethod
    @abc.abstractmethod
    def user_id(access_token: str):
        """get user external provider user id"""

    @staticmethod
    @abc.abstractmethod
    def profile(user_id: int, access_token: str):
        """get user profile fields from provider"""
