import binascii
import datetime as dt
import hashlib
import os
from datetime import datetime
from flask_login import UserMixin

from api.database.mixins import Column, Model, SurrogatePK, db, relationship, reference_col

HASH_NAME = 'sha1'
HASH_ROUNDS = 1000
SALT_LENGTH = 20


class User(UserMixin, SurrogatePK, Model):
    """A user of the app."""

    __tablename__ = 'users'
    username = Column(db.String(80), unique=True, nullable=False)
    email = Column(db.String(80), unique=True, nullable=False)
    password = Column(db.String(120), nullable=True)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    last_login = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    salt = Column(db.String(80), nullable=False)
    is_admin = Column(db.Boolean, nullable=False, default=False)

    def __init__(self, email, username='', password='', **kwargs):
        """Create instance."""
        if not username:
            username = binascii.b2a_base64(hashlib.sha1(email.encode('utf-8')).digest()).decode("utf-8")
        if not password:
            password = os.urandom(20)
        db.Model.__init__(self, username=username, email=email, **kwargs)
        self.set_password(password)

    @staticmethod
    def _prepare_password(password, salt=None):
        salt = binascii.a2b_base64(salt) if salt else os.urandom(SALT_LENGTH)
        if isinstance(password, str):
            password = password.encode('utf-8')
        dk = hashlib.pbkdf2_hmac(hash_name=HASH_NAME, password=password, salt=salt, iterations=HASH_ROUNDS)
        return binascii.b2a_base64(salt).decode("utf-8"), binascii.b2a_base64(dk).decode("utf-8")

    def set_password(self, password):
        """Set password."""
        self.salt, self.password = self._prepare_password(password)

    def check_password(self, value):
        """Check password."""
        passhash = self._prepare_password(value, self.salt)[1]
        return passhash == self.password

    @staticmethod
    def get_user_by_email(email):
        return User.query.filter_by(email=email).first() or False

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at,
            'last_login': self.last_login,
        }
