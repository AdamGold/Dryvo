import os

CURRENT_FOLDER = os.path.dirname(
    os.path.abspath(__file__))  # get current file path
DEBUG_MODE = os.environ.get("FLASK_DEBUG", 1)
DATE_FORMAT = "%Y-%m-%dT%H:%MZ"
MOBILE_LINK = "dryvo://auth/"
FACEBOOK_SCOPES = "email"
