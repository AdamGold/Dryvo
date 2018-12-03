from app import app
from extensions import db

from api.database.models.user import User
from api.database.models.lesson import Lesson
from api.database.models.review import Review
from api.database.models.stage import Stage
from api.database.models.topic import Topic
from api.database.models.student import Student
from api.database.models.teacher import Teacher
from api.database.models.test import Test
from api.database.models.work_day import WorkDay
from api.database.models.oauth import OAuth

if __name__ == '__main__':
    with app.app_context():
        db.drop_all()
        db.create_all()
