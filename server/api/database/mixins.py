"""Database module, including the SQLAlchemy database object and DB-related utilities.
from: https://github.com/sloria/cookiecutter-flask/
"""
from server.api.database import db
import operator

# Alias common SQLAlchemy names
Column = db.Column
relationship = db.relationship


class CRUDMixin(object):
    """Mixin that adds convenience methods for CRUD (create, read, update, delete) operations."""

    @classmethod
    def create(cls, **kwargs):
        """Create a new record and save it the database."""
        instance = cls(**kwargs)
        return instance.save()

    def update(self, commit=True, **kwargs):
        """Update specific fields of a record."""
        for attr, value in kwargs.items():
            setattr(self, attr, value)
        return commit and self.save() or self

    def save(self, commit=True):
        """Save the record."""
        db.session.add(self)
        if commit:
            db.session.commit()
        return self

    def delete(self, commit=True):
        """Remove the record from the database."""
        db.session.delete(self)
        return commit and db.session.commit()


class Model(CRUDMixin, db.Model):
    """Base model class that includes CRUD convenience methods."""

    __abstract__ = True

    @staticmethod
    def _filter_data(model: object, column: str, filter_: str):
        """get column and filter strings and return filtering function
        e.g get id=lt:200
        return operator.lt(Model.id, 200)"""
        fields = filter_.split(":", 1)
        operators = {"le": operator.le, "ge": operator.ge, "eq": operator.eq,
                     "lt": operator.lt, "gt": operator.gt, "ne": operator.ne}

        method = "eq"
        value_to_compare = filter_
        if len(fields) > 1 and fields[0] in operators.keys():
            method = fields[0]
            value_to_compare = fields[1]

        return operators[method](getattr(model, column), value_to_compare)

    @staticmethod
    def _sort_data(model: object, args: dict, default_column: str, default_method: str = "asc") -> callable:
        """ get arguments and return order_by function.
        e.g get order_by=date desc
        return Model.date.asc
        """
        order_by_args = args.get("order_by", "").split()
        try:
            column = order_by_args[0]
            method = order_by_args[1]
        except IndexError:
            column = default_column
            method = default_method

        return getattr(
            getattr(model, column), method)


# From Mike Bayer's "Building the app" talk
# https://speakerdeck.com/zzzeek/building-the-app
class SurrogatePK(object):
    """A mixin that adds a surrogate integer 'primary key' column named ``id`` to any declarative-mapped class."""

    __table_args__ = {"extend_existing": True}

    id = Column(db.Integer, primary_key=True)

    @classmethod
    def get_by_id(cls, record_id):
        """Get record by ID."""
        if any(
            (
                isinstance(record_id, (str, bytes)) and record_id.isdigit(),
                isinstance(record_id, (int, float)),
            )
        ):
            return cls.query.get(int(record_id))
        return None


def reference_col(tablename, nullable=False, pk_name="id", **kwargs):
    """Column that adds primary key foreign key reference.
    Usage: ::
        category_id = reference_col('category')
        category = relationship('Category', backref='categories')
    """
    return Column(
        db.ForeignKey("{0}.{1}".format(tablename, pk_name)), nullable=nullable, **kwargs
    )
