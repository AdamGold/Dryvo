import werkzeug
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import backref

from server.api.database.mixins import (
    Column,
    Model,
    SurrogatePK,
    reference_col,
    relationship,
)
from server.api.database.models import Appointment, Payment, User, AppointmentType


class LessonCreator(Model):
    @declared_attr
    def user_id(self):
        return reference_col("users", nullable=False)

    @declared_attr
    def user(self):
        return relationship(
            "User",
            backref=backref(
                self.__tablename__[:-1], uselist=False
            ),  # slice the `s` from table name
            uselist=False,
            foreign_keys=[self.user_id],
        )

    __abstract__ = True

    @hybrid_property
    def lessons(self):
        return self.appointments.filter_by(type=AppointmentType.LESSON)

    @hybrid_method
    def filter_appointments(self, args: werkzeug.datastructures.MultiDict):
        args = args.copy()
        query = self.appointments
        if "deleted" not in args or self.__class__.__name__.lower() == "student":
            # default to non deleted items
            query = query.filter_by(deleted=False)
            try:
                args.pop("deleted")
            except KeyError:
                pass
        return Appointment.filter_and_sort(args, query=query, with_pagination=True)

    @hybrid_method
    def filter_payments(self, args: werkzeug.datastructures.MultiDict):
        query = self.payments
        return Payment.filter_and_sort(args, query=query, with_pagination=True)
