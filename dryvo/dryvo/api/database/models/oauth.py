from api.database.mixins import Column, Model, db, relationship, reference_col

from flask_dance.consumer.backend.sqla import OAuthConsumerMixin

from api.database.models.user import User


class OAuth(OAuthConsumerMixin, Model):
    provider_user_id = Column(db.String(256), unique=True)
    user_id = reference_col('users', nullable=False)
    user = relationship(User)
