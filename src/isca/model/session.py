from .core import Person
from .paper import Paper


class Session:
    def __init__(
        self, title: str, chairs: list[Person], papers: list[Paper], start_time=None, end_time=None, room=None
    ):
        self.title = title
        self.chairs = chairs
        self.papers = papers
        self.start_time = start_time
        self.end_time = end_time
        self.room = room

    @property
    def start_date_str(self) -> str:
        return ""

    @property
    def end_date_str(self) -> str:
        return ""

    @property
    def start_time_str(self) -> str:
        return ""

    @property
    def end_time_str(self) -> str:
        return ""
