from server.extensions import db
from server.app import create_app
from server.app_config import Config
from server.api.database.models import *

if __name__ == "__main__":
    app = create_app(Config)
    with app.app_context():
        db.drop_all()
        db.create_all()
