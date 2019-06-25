from typing import Dict, List
from abc import ABC, abstractmethod


class LessonRule(ABC):
    default_dict: Dict[str, List[int]] = {"start_hour": [], "end_hour": []}

    def __init__(self, date, student):
        self.date = date
        self.student = student

    @abstractmethod
    def filter_(self):
        """the filtering of the lessons"""

    @abstractmethod
    def rule(self) -> Dict[str, List[int]]:
        """the actual rule conditions
        returns the blacklisted hours"""
