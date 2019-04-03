import abc


class SocialNetwork(abc.ABC):
    """Social network abstract class"""

    @classmethod
    @abc.abstractmethod
    def auth_url(cls, state):
        """return auth url of provider for oauth"""

    @classmethod
    @abc.abstractmethod
    def access_token(cls, state: str, code: str) -> str:
        """get access token by code given in URL"""

    @classmethod
    @abc.abstractmethod
    def token_metadata(cls, access_token: str):
        """get token metadata - includes user external provider user id"""

    @classmethod
    @abc.abstractmethod
    def profile(cls, user_id: int, access_token: str):
        """get user profile fields from provider"""
