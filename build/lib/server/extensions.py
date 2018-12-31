"""Extensions module. Each extension is initialized in the app factory located in app.py."""
from flask_login import LoginManager
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy

sess = Session()  # we use the Session extension so we can have server sessions
db = SQLAlchemy()
login_manager = LoginManager()
