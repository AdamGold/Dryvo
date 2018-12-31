import datetime as dt

from server.api.database.mixins import (
    Column,
    Model,
    SurrogatePK,
    db,
    relationship,
    reference_col,
)
from server.api.database.models.user import User

from sqlalchemy.orm import backref
from sqlalchemy_utils import ChoiceType
import enum


class Provider(enum.Enum):
    facebook = 1
    google = 2


class OAuth(SurrogatePK, Model):
    """oauh provider"""

    __tablename__ = "oauth_providers"
    provider_user_id = Column(db.String(256), unique=True)
    user_id = reference_col("users", nullable=False)
    user = relationship(User)
    provider = Column(ChoiceType(Provider, impl=db.Integer()), nullable=False)
    token = Column(db.JSON, nullable=False, default=dt.datetime.utcnow)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)
