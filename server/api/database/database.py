from flask import g
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import click


db_instance = SQLAlchemy()


def get_db():
    return db_instance


def reset_db(db):
    # db.session.remove()
    db.drop_all()
    db.create_all()


def close_db(unused_e=None):
    db_instance = g.pop("db_instance", None)

    if db_instance is not None:
        db_instance.close()


def init_app(app):
    db_instance.init_app(app)
    migrate = Migrate(app, db_instance)
    app.teardown_appcontext(close_db)

    @app.cli.command()
    def restartdb():
        reset_db(db_instance)
