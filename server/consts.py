import os

DEBUG_MODE = os.environ.get("FLASK_DEBUG", 1)
DATE_FORMAT = "%Y-%m-%dT%H:%MZ"
MOBILE_LINK = "dryvo://auth/"
FACEBOOK_SCOPES = "email"
LOG_RETENTION = "7 days"
