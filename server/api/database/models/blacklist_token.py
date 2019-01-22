import datetime as dt

from server.api.database.mixins import (
    Column,
    Model,
    SurrogatePK,
    relationship,
    reference_col,
)
from server.api.database import db


class BlacklistToken(SurrogatePK, Model):
    """
    Token Model for storing JWT tokens
    """

    __tablename__ = "blacklist_tokens"

    id = Column(db.Integer, primary_key=True, autoincrement=True)
    token = Column(db.String(500), unique=True, nullable=False)
    blacklisted_on = Column(db.DateTime, nullable=False)

    def __init__(self, token):
        self.token = token
        self.blacklisted_on = dt.datetime.now()

    def __repr__(self):
        return "<id: token: {}".format(self.token)

    @staticmethod
    def check_blacklist(token):
        # check whether token has been blacklisted
        res = BlacklistToken.query.filter_by(token=str(token)).first()
        if res:
            return True
        else:
            return False
