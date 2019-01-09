from server.api.database import db
from server.app import create_app
from server.api.database.models import *


def init_db(db):
    db.drop_all()
    db.create_all()

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        init_db(db)
