from flask import g
from flask_sqlalchemy import SQLAlchemy


db_instance = SQLAlchemy()


def get_db():
    return db_instance


def close_db(unused_e=None):
    db_instance = g.pop("db_instance", None)

    if db_instance is not None:
        db_instance.close()


def init_app(app):
    db_instance.init_app(app)
    app.teardown_appcontext(close_db)
