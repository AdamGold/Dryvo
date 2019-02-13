import os
from pathlib import Path


class Config(object):
    SECRET_KEY = os.urandom(24)
    SECRET_JWT = os.environ.get("SECRET_JWT")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    FIREBASE_JSON = os.environ.get("FIREBASE_JSON")
    FACEBOOK_CLIENT_ID = os.environ.get("FACEBOOK_CLIENT_ID")
    FACEBOOK_CLIENT_SECRET = os.environ.get("FACEBOOK_CLIENT_SECRET")
    FACEBOOK_TOKEN = os.environ.get("FACEBOOK_TOKEN")

    def update(self, newdata):
        for key, value in newdata.items():
            setattr(self, key, value)
