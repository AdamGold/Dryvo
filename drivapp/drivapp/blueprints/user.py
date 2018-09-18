import flask
from flask import Blueprint
from flask_login import current_user, login_required, logout_user

from api.utils import jsonify_response

user_routes = Blueprint('user', __name__, url_prefix='/user')


@user_routes.route('/logout')
@jsonify_response
@login_required
def logout():
    logout_user()
    return {'message': 'Logout successfully.'}
