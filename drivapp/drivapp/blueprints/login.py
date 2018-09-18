import json

import flask
from flask import Blueprint
from flask_login import login_user, current_user

import consts
from api.database.models.user import User
from api.utils import RouteError
from api.utils import jsonify_response
from extensions import login_manager


login_routes = Blueprint('login', __name__, url_prefix='/login')


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    return User.get_by_id(int(user_id))


@login_routes.route('/direct', methods=['POST'])
@jsonify_response
def direct_login():
    data = flask.request.get_json()
    # Get the user object using their email (unique to every user)
    email = data.get('email')
    if email:
        user = User.get_user_by_email(email)
    else:
        user = User.query.filter_by(username=data.get('username')).first()

    # Try to authenticate the found user using their password
    if user and user.check_password(data.get('password')):
        login_user(user, remember=True)
        return {'message': 'You logged in successfully.'}
    else:
        # User does not exist. Therefore, we return an error message
        raise RouteError('Invalid email or password.', 401)


@login_routes.route('/register', methods=['POST'])
@jsonify_response
def register():
    post_data = flask.request.get_json()
    email = post_data.get('email')
    username = post_data.get('username')
    # Query to see if the user already exists
    user = User.get_user_by_email(email)
    user_by_username = User.query.filter_by(username=username).first()
    if email and not user:
        if user_by_username:
            # taken username
            raise RouteError('This username is taken.', 409)
        # There is no user so we'll try to register them
        # Register the user
        username = post_data.get('username')
        password = post_data.get('password')
        user = User(email=email, username=username, password=password, manually_registered=True)
        user.save()

        # return a response notifying the user that they registered successfully
        return {'message': 'You registered successfully. Please log in.'}, 201
    else:
        # There is an existing user. We don't want to register users twice
        # Return a message to the user telling them that they they already exist
        raise RouteError('User already exists.')
