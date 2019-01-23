from enum import Enum
from datetime import datetime

from sqlalchemy_utils import ChoiceType

from server.api.database import db
from server.api.database.mixins import Column, Model
from server.api.database.models import Topic


class LessonTopic(Model):
    """lesson-topics association"""

    __tablename__ = "lesson_topics"
    topic_id = Column(db.Integer, db.ForeignKey("topics.id"), primary_key=True)
    lesson_id = Column(db.Integer, db.ForeignKey("lessons.id"), primary_key=True)
    is_finished = Column(db.Boolean, nullable=False, default=False)
    created_at = Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __init__(self, **kwargs):
        """Create instance."""
        db.Model.__init__(self, **kwargs)

    def to_dict(self):
        return dict(
            **Topic.get_by_id(self.topic_id).to_dict(),
            **{"lesson_id": self.lesson_id, "is_finished": self.is_finished}
        )
