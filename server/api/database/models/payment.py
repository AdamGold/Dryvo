import datetime as dt
import enum

from sqlalchemy.orm import backref

from server.api.database import db
from server.api.database.mixins import (
    Column,
    Model,
    SurrogatePK,
    reference_col,
    relationship,
)
from sqlalchemy_utils import ChoiceType


class PaymentType(enum.Enum):
    cash = 1
    check = 2
    credit = 3
    bank = 4
    other = 9


class Payment(SurrogatePK, Model):
    """Payment from student to teacher"""

    __tablename__ = "payments"
    teacher_id = reference_col("teachers", nullable=False)
    teacher = relationship("Teacher", backref=backref("payments", lazy="dynamic"))
    student_id = reference_col("students", nullable=True)
    student = relationship("Student", backref=backref("payments", lazy="dynamic"))
    amount = Column(db.Integer, nullable=False)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    pdf_link = Column(db.String(300), nullable=True)
    crn = Column(db.Integer, nullable=True)
    payment_type = Column(
        ChoiceType(PaymentType, impl=db.Integer()), nullable=False, server_default="1"
    )
    details = Column(db.String(240), nullable=True)

    ALLOWED_FILTERS = ["student_id", "amount", "created_at"]
    default_sort_method = "desc"

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student": self.student.user.to_dict(),  # student contains teacher
            "amount": self.amount,
            "pdf_link": self.pdf_link,
            "crn": self.crn,
            "payment_type": self.payment_type.name,
            "created_at": self.created_at,
        }

    def __repr__(self):
        return f"<Payment created_at={self.created_at}, teacher={self.teacher}, student={self.student}>"
