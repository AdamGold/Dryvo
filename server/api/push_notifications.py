from pyfcm import FCMNotification
from flask import current_app
from flask import _app_ctx_stack as stack
from server.error_handling import RouteError


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
        self._handle_failure(response.get('failure'))
        return response

    def notify_multiple_devices(self, *args, **kwargs):
        response = self.service.notify_multiple_devices(*args, **kwargs)
        self._handle_failure(response.get('failure'))
        return response

    def _handle_failure(self, error):
        if error:
            raise NotificationError(error)
