from . import more_than_lessons_week, regular_students, new_students
from .lesson_rule import LessonRule
from .utils import rules_registry, register_rule


# score hours (cold-hot)
# 1. if a student has already scheduled 2 lessons this week, return hours <4 score
# 2. if a place is >20km than the last / next lesson, eliminate that hour if that hour is >5 score
# 3. new student (<5 lessons) won't be before lesson that is >15km, if that hour >5 score
# 4. students with 10-20 lessons - show them hours < 8 score
# 5. students with <5 lessons, show them hours > 3 score
# 6. if a student already had a high score hour this week (>=8), don't allow another one
