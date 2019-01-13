from pyfcm import FCMNotification
from flask import current_app
from flask import _app_ctx_stack as stack
from server.api.utils import RouteError


class NotificationError(RouteError):
    pass


class FCM(object):
    @property
    def service(self):
        ctx = stack.top
        if ctx is not None:
            if not hasattr(ctx, 'fcm_service'):
                ctx.fcm_service = FCMNotification(
                    api_key=current_app.config['FIREBASE_KEY'])
            return ctx.fcm_service

    def notify_single_device(self, *args, **kwargs):
        response = self.service.notify_single_device(*args, **kwargs)
        if int(response['failure']) > 0:
            self._handle_failure()
        return response

    def notify_multiple_devices(self, *args, **kwargs):
        response = self.service.notify_multiple_devices(*args, **kwargs)
        if int(response['failure']) > 0:
            self._handle_failure()
        return response

    def _handle_failure(self):
        raise NotificationError("Failed to send notification")
