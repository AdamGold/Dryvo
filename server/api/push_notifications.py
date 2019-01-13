from pyfcm import FCMNotification
from pyfcm.errors import InvalidDataError, FCMServerError
from flask import current_app
from flask import _app_ctx_stack as stack
from server.error_handling import NotificationError


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
        try:
            response = self.service.notify_single_device(*args, **kwargs)
            error = response.get('failure')
        except (InvalidDataError, FCMServerError) as e:
            error = str(e)
        self._handle_failure(error)
        return response

    def notify_multiple_devices(self, *args, **kwargs):
        try:
            response = self.service.notify_multiple_devices(*args, **kwargs)
            error = response.get('failure')
        except (InvalidDataError, FCMServerError) as e:
            error = str(e)
        self._handle_failure(error)
        return response

    def _handle_failure(self, error):
        if error:
            raise NotificationError(error)


fcm_service = FCM()


def get_fcm_service():
    return fcm_service
