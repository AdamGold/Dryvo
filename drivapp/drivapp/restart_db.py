from app import app
from extensions import db

from api.database.models.user import User

if __name__ == '__main__':
    with app.app_context():
        db.drop_all()
        db.create_all()
