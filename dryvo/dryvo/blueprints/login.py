import os
import flask
import string
import random
import requests
from flask import Blueprint
from flask_login import login_user, current_user
from sqlalchemy.orm.exc import NoResultFound

from api.database.models.user import User
from api.database.models.blacklist_token import BlacklistToken
from api.database.models.oauth import OAuth, Provider
from api.utils import RouteError, jsonify_response
from extensions import login_manager
from consts import DEBUG_MODE

login_routes = Blueprint('login', __name__, url_prefix='/login')


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    return User.query.filter_by(id=int(user_id)).first()


@login_manager.request_loader
def load_user_from_request(request):
    # get the auth token
    auth_header = request.headers.get('Authorization')
    if auth_header:
        try:
            auth_token = auth_header.split(" ")[1]
        except IndexError:
            raise RouteError('Bearer token malformed.', 401)
    else:
        auth_token = ''
    if auth_token:
        resp = User.decode_auth_token(auth_token)
        if not isinstance(resp, str):
            return User.query.filter_by(id=resp).first()
    return None


@login_routes.route('/direct', methods=['POST'])
@jsonify_response
def direct_login():
    data = flask.request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()
    # Try to authenticate the found user using their password
    if user and user.check_password(data.get('password')):
        auth_token = user.encode_auth_token(user.id)
        if auth_token:
            login_user(user, remember=True)
            return {'message': 'You logged in successfully.',
                    'auth_token': auth_token.decode()}
    else:
        # User does not exist. Therefore, we return an error message
        raise RouteError('Invalid email or password.', 401)


@login_routes.route('/logout', methods=['POST'])
@jsonify_response
def logout():
    auth_header = flask.request.headers.get('Authorization')
    auth_token = auth_header.split(" ")[1]
    # mark the token as blacklisted
    blacklist_token = BlacklistToken(token=auth_token)
    # insert the token
    blacklist_token.save()
    return {'message': 'Logged out successfully.'}


@login_routes.route('/register', methods=['POST'])
@jsonify_response
def register():
    post_data = flask.request.get_json()
    email = post_data.get('email')
    name = post_data.get('name')
    area = post_data.get('area')
    # Query to see if the user already exists
    user = User.query.filter_by(email=email).first()
    if email and name and area and not user:
        # There is no user so we'll try to register them
        # Register the user
        password = post_data.get('password')
        user = User(email=email, password=password, name=name, area=area)
        user.save()
        # generate auth token
        auth_token = user.encode_auth_token(user.id)
        # return a response notifying the user that they registered successfully
        return {'message': 'You registered successfully. Please log in.',
                'auth_token': auth_token.decode()}, 201
    else:
        # There is an existing user. We don't want to register users twice
        # Return a message to the user telling them that they they already exist
        raise RouteError('Can not create user.')


@login_routes.route('/facebook', methods=['GET'])
@jsonify_response
def oauth_facebook():
    """setup Facebook API, redirect to facebook login & permissions
    when redirected back, check auth code and setup a server session
    with credentials
    """
    if current_user.is_authenticated:
        raise RouteError('User already logged in.')

    state = ''.join(random.choices(
        string.ascii_uppercase + string.digits, k=6))
    redirect = flask.url_for('.facebook_authorized', _external=True)
    auth_url = "https://www.facebook.com/v3.2/dialog/oauth?client_id={}" \
               "&redirect_uri={}&state={}&scope={}". \
               format(os.environ['FACEBOOK_CLIENT_ID'], redirect,
                      state, os.environ['FACEBOOK_SCOPES'])
    # Store the state so the callback can verify the auth server response.
    flask.session['state'] = state
    return {'auth_url': auth_url}


@login_routes.route('/facebook/authorized', methods=['POST'])
@jsonify_response
def facebook_authorized():
    data = flask.request.get_json()
    if data.get('state') != flask.session.get('state') and not DEBUG_MODE:
        raise RouteError('State not valid.')

    redirect = flask.url_for('.facebook_authorized',
                             _external=True)  # the url we are on
    token_url = "https://graph.facebook.com/v3.2/oauth/access_token?client_id=" \
                "{}&redirect_uri={}&client_secret={}&code={}". \
                format(os.environ['FACEBOOK_CLIENT_ID'], redirect,
                       os.environ['FACEBOOK_CLIENT_SECRET'], data.get('code'))
    access_token = requests.get(token_url).json().get('access_token')

    url = "https://graph.facebook.com/debug_token?input_token={}&access_token={}". \
          format(access_token, os.environ['FACEBOOK_TOKEN'])

    validate_token_resp = requests.get(url).json()['data']

    # Find this OAuth token in the database, or create it
    query = OAuth.query.filter_by(
        provider=Provider.facebook,
        provider_user_id=validate_token_resp.get('user_id'),
    )
    try:
        oauth = query.one()
    except NoResultFound:
        oauth = OAuth(
            provider=Provider.facebook,
            provider_user_id=validate_token_resp.get('user_id'),
            token=access_token,
        )

    if oauth.user:
        login_user(oauth.user)
    else:
        profile = requests.get('https://graph.facebook.com/v3.2/{}?'
                               'fields=email,name&access_token={}'.
                               format(validate_token_resp.get('user_id'), access_token)).json()

        # Create a new local user account for this user
        user = User(
            email=profile.get('email'),
            name=profile.get('name'),
            area=data.get('area')
        ).save()
        oauth.user = user
        oauth.save()
        # Log in the new local user account
        login_user(user)

    auth_token = user.encode_auth_token(user.id)
    if auth_token:
        return {'message': 'User logged in from facebook.', 'auth_token': auth_token.decode()}, 201
