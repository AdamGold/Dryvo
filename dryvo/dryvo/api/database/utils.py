from flask_sqlalchemy import BaseQuery
from api.database.mixins import db

from datetime import timedelta

class QueryWithSoftDelete(BaseQuery):
    _with_deleted = False

    def __new__(cls, *args, **kwargs):
        obj = super(QueryWithSoftDelete, cls).__new__(cls)
        obj._with_deleted = kwargs.pop('_with_deleted', False)
        if len(args) > 0:
            super(QueryWithSoftDelete, obj).__init__(*args, **kwargs)
            return obj.filter_by(deleted=False) if not obj._with_deleted else obj
        return obj

    def __init__(self, *args, **kwargs):
        pass

    def with_deleted(self):
        return self.__class__(db.class_mapper(self._mapper_zero().class_),
                              session=db.session(), _with_deleted=True)

    def _get(self, *args, **kwargs):
        # this calls the original query.get function from the base class
        return super(QueryWithSoftDelete, self).get(*args, **kwargs)

    def get(self, *args, **kwargs):
        # the query.get method does not like it if there is a filter clause
        # pre-loaded, so we need to implement it using a workaround
        obj = self.with_deleted()._get(*args, **kwargs)
        return obj if obj is None or self._with_deleted or not obj.deleted else None


def get_slots(hours, appointments, duration):
    minimum = (hours[0], hours[0])
    maximum = (hours[1], hours[1])
    available_lessons = []
    slots = [max(min(v, maximum), minimum) for v in sorted([minimum] + appointments + [maximum])]
    for start, end in((slots[i][1], slots[i+1][0]) for i in range(len(slots)-1)):
        while start + duration <= end:
            available_lessons.append((start, start + duration))
            start += duration

    return available_lessons
