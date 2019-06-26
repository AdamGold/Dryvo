import functools
from . import cold_if_more_than_lessons
from .lesson_rule import LessonRule
from .utils import rules_registry, register_rule


# TODO add rules
# score hours (cold-hot)
# 1. if a student has already scheduled 2 lessons this week, return hours <5 score
# 2. if a place is >20km than the last / next lesson, eliminate that hour if that hour is >5 score
# 3. new student (<5 lessons) won't be before lesson that is >15km, if that hour >5 score
# 4. students with 10-20 lessons - show them hours < 8 score
# 5. students with <5 lessons, show them hours > 3 score
