import os
import flask
from flask import Blueprint
from flask_login import login_user, current_user
from sqlalchemy.orm.exc import NoResultFound
from flask_dance.contrib.facebook import make_facebook_blueprint, facebook
from flask_dance.consumer.backend.sqla import OAuthConsumerMixin, SQLAlchemyBackend
from flask_dance.consumer import oauth_authorized, oauth_error

from api.database.mixins import db
from api.database.models.user import User
from api.database.models.oauth import OAuth
from api.utils import RouteError, jsonify_response
from extensions import login_manager


login_routes = Blueprint('login', __name__, url_prefix='/login')
facebook_blueprint = make_facebook_blueprint(
    client_id="473596283140535",
    client_secret="553ebd9c279f5ce8e59af259a003ead8",
)

facebook_blueprint.backend = SQLAlchemyBackend(OAuth, db.session, user=current_user)


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    return User.query.filter_by(id=int(user_id)).first()


@login_routes.route("/facebook")
def facebook_login():
    return flask.redirect(flask.url_for("facebook.login"))


@login_routes.route('/direct', methods=['POST'])
@jsonify_response
def direct_login():
    data = flask.request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()

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

        # return a response notifying the user that they registered successfully
        return {'message': 'You registered successfully. Please log in.'}, 201
    else:
        # There is an existing user. We don't want to register users twice
        # Return a message to the user telling them that they they already exist
        raise RouteError('Can not create user.')


# create/login local user on successful OAuth login
@oauth_authorized.connect_via(facebook_blueprint)
def facebook_logged_in(blueprint, token):
    if not token:
        #flash("Failed to log in with Facebook.", category="error")
        return False

    resp = blueprint.session.get("/user")
    print(resp)
    if not resp.ok:
        msg = "Failed to fetch user info from Facebook."
        #flash(msg, category="error")
        return False

    info = resp.json()
    user_id = str(info["id"])

    # Find this OAuth token in the database, or create it
    query = OAuth.query.filter_by(
        provider=blueprint.name,
        provider_user_id=user_id,
    )
    try:
        oauth = query.one()
    except NoResultFound:
        oauth = OAuth(
            provider=blueprint.name,
            provider_user_id=user_id,
            token=token,
        )

    if oauth.user:
        login_user(oauth.user)
        #flash("Successfully signed in with GitHub.")
    else:
        # Create a new local user account for this user
        user = User(
            # Remember that `email` can be None, if the user declines
            # to publish their email address on GitHub!
            email=info["email"],
            name=info["name"],
        )
        # Associate the new local user account with the OAuth token
        oauth.user = user
        # Save and commit our database models
        user.save()
        oauth.save()
        # Log in the new local user account
        login_user(user)
        #flash("Successfully signed in with GitHub.")

    # Disable Flask-Dance's default behavior for saving the OAuth token
    return False


# notify on OAuth provider error
@oauth_error.connect_via(facebook_blueprint)
def github_error(blueprint, error, error_description=None, error_uri=None):
    msg = (
        "OAuth error from {name}! "
        "error={error} description={description} uri={uri}"
    ).format(
        name=blueprint.name,
        error=error,
        description=error_description,
        uri=error_uri,
    )
    #flash(msg, category="error")
