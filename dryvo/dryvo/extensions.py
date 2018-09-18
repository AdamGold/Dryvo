"""Extensions module. Each extension is initialized in the app factory located in app.py."""
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()
