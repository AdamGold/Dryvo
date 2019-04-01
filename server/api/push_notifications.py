import json
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, messaging
from firebase_admin.project_management import ApiCallError
from loguru import logger

from server.error_handling import NotificationError


def init_app(app):
    if not len(firebase_admin._apps):
        logger.debug("initializing firebase app")
        cred = credentials.Certificate(json.loads(app.config["FIREBASE_JSON"]))
        firebase_admin.initialize_app(cred)


class FCM(object):
    @staticmethod
    def notify(token, title, body, payload=None):
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=token,
            data=json.dumps(payload),
        )
        try:
            messaging.send(message)
        except (ValueError, ApiCallError) as e:
            raise NotificationError(str(e))
