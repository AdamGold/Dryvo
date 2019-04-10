import binascii
import datetime as dt
import hashlib
import os
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict

import jwt
from cloudinary.utils import cloudinary_url
from flask import current_app
from flask_login import UserMixin
from sqlalchemy.orm.exc import NoResultFound

from server.consts import PROFILE_SIZE
from server.api.database import db
from server.api.database.consts import (
    EXCHANGE_TOKEN_EXPIRY,
    REFRESH_TOKEN_EXPIRY,
    TOKEN_EXPIRY,
)
from server.api.database.mixins import (
    Column,
    Model,
    SurrogatePK,
    reference_col,
    relationship,
)
from server.api.database.models import BlacklistToken
from server.error_handling import TokenError

HASH_NAME = "sha1"
HASH_ROUNDS = 1000
SALT_LENGTH = 20


class TokenScope(Enum):

    EXCHANGE = auto()
    LOGIN = auto()
    REFRESH = auto()

    def expiry(self) -> int:
        return {
            self.EXCHANGE: EXCHANGE_TOKEN_EXPIRY,
            self.LOGIN: TOKEN_EXPIRY,
            self.REFRESH: REFRESH_TOKEN_EXPIRY,
        }[self]


class User(UserMixin, SurrogatePK, Model):
    """A user of the app."""

    __tablename__ = "users"
    email = Column(db.String(80), unique=True, nullable=False)
    password = Column(db.String(120), nullable=True)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    last_login = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    salt = Column(db.String(80), nullable=False)
    name = Column(db.String(80), nullable=False)
    is_admin = Column(db.Boolean, nullable=False, default=False)
    area = Column(db.String(80), nullable=True)
    firebase_token = Column(db.Text, nullable=True)
    image = Column(db.String(240), nullable=True)

    ALLOWED_FILTERS = ["name", "email", "area"]

    def __init__(self, email, password="", **kwargs):
        if not password:
            password = os.urandom(20)
        db.Model.__init__(self, email=email, **kwargs)
        self.set_password(password)

    @staticmethod
    def _prepare_password(password, salt=None):
        salt = binascii.a2b_base64(salt) if salt else os.urandom(SALT_LENGTH)
        if isinstance(password, str):
            password = password.encode("utf-8")
        dk = hashlib.pbkdf2_hmac(
            hash_name=HASH_NAME, password=password, salt=salt, iterations=HASH_ROUNDS
        )
        return (
            binascii.b2a_base64(salt).decode("utf-8"),
            binascii.b2a_base64(dk).decode("utf-8"),
        )

    def set_password(self, password):
        """Set password."""
        self.salt, self.password = self._prepare_password(password)

    def check_password(self, value):
        """Check password."""
        passhash = self._prepare_password(value, self.salt)[1]
        return passhash == self.password

    def generate_tokens(self) -> Dict[str, str]:
        return {
            "auth_token": self.encode_auth_token().decode(),
            "refresh_token": self.encode_refresh_token().decode(),
        }

    def _encode_jwt(self, scope: TokenScope, **kwargs) -> bytes:
        payload = dict(
            **{
                "exp": datetime.utcnow() + timedelta(days=scope.expiry()),
                "iat": datetime.utcnow(),
                "user_id": self.id,
                "scope": scope.value,
            },
            **kwargs,
        )
        return jwt.encode(
            payload, current_app.config.get("SECRET_JWT"), algorithm="HS256"
        )

    def encode_exchange_token(self) -> bytes:
        """Generates an exchange token for current user"""
        return self._encode_jwt(TokenScope.EXCHANGE)

    def encode_auth_token(self) -> bytes:
        """Generates a login token"""
        return self._encode_jwt(TokenScope.LOGIN, email=self.email)

    def encode_refresh_token(self) -> bytes:
        """Generates a refresh token."""
        return self._encode_jwt(TokenScope.REFRESH)

    @staticmethod
    def from_payload(payload: dict) -> "User":
        """Returns the user that owns the token"""
        try:
            return User.query.filter_by(id=payload["user_id"]).one()
        except NoResultFound:
            raise TokenError("No user associated with jwt token")

    @staticmethod
    def from_login_token(token: str) -> "User":
        """Returns the user that owns the auth token.
        only for auth (login) tokens and not for refresh."""
        payload = User.decode_token(token)
        if not payload["email"] or payload["scope"] != TokenScope.LOGIN.value:
            raise TokenError("INVALID_TOKEN")
        return User.from_payload(payload)

    @staticmethod
    def decode_token(auth_token: str) -> dict:
        """Decode JWT or raise familiar exceptions"""
        try:
            payload = jwt.decode(auth_token, current_app.config.get("SECRET_JWT"))
            if BlacklistToken.check_blacklist(auth_token):
                raise TokenError("BLACKLISTED_TOKEN")
            return payload
        except jwt.ExpiredSignatureError:
            raise TokenError("EXPIRED_TOKEN")
        except (jwt.InvalidTokenError, jwt.DecodeError):
            raise TokenError("INVALID_TOKEN")

    def role_info(self):
        info = self.teacher or self.student or {}
        return info.to_dict() if info else {}

    def to_dict(self):
        image = ""
        if self.image:
            try:
                image = cloudinary_url(
                    self.image,
                    width=PROFILE_SIZE,
                    height=PROFILE_SIZE,
                    crop="thumb",
                    gravity="face",
                )[0]
            except Exception:
                pass
        return {
            "id": self.id,
            "email": self.email,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "area": self.area,
            "name": self.name,
            "image": image,
        }
