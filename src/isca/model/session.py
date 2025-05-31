import datetime

from .person import Person
from .paper import Paper


class Room:
    def __init__(self, name: str, type: str, capacity: int|tuple[int]|list[int]|None):
        self.name: str = name
        self.type: str = type
        self.capacity: int|tuple[int]|list[int]|None = capacity


    def __str__(self) -> str:
        str = f"{self.name}"
        if self.capacity is not None:
            str += f" (capacity={self.capacity})"

        return str + f" [{self.type}]"

class Session:
    def __init__(
        self,
        id: str,
        name: str,
        papers: list[Paper] | None = None,
    ):
        self.id = id
        self.name = name
        self._papers = papers if papers is not None else []

    @property
    def papers(self) -> list[Paper]:
        return self._papers.copy()

    def add_paper(self, paper: Paper):
        self._papers.append(paper)

    def is_in_session(self, paper: Paper) -> bool:
        return paper in self._papers

    def remove_paper(self, paper: Paper):
        if self.is_in_session(paper):
            self._papers.remove(paper)

    def replace_paper(self, paper_out: Paper, paper_in: Paper):
        idx = self._papers.index(paper_out)
        if idx < 0:
            raise ValueError(f'"{paper_out.id}" is not part of the session, so it can\'t be replaced')
        self._papers[idx] = paper_in

    def sort_criterion(self) -> str:
        return self.id

class PresentationSession(Session):
    def __init__(
        self,
        id: str,
        name: str,
        start: datetime.datetime,
        end: datetime.datetime,
        room: Room | None = None,
        papers: list[Paper] | None = None,
        chairs: list[Person] | None = None,
    ):
        super().__init__(id, name, papers)
        self._chairs = chairs if chairs is not None else []
        self.room = room

        # For now, start/end can't be modified to avoid side effects!
        self._start = start
        self._end = end

    @property
    def start(self) -> datetime.datetime:
        return self._start

    @property
    def end(self) -> datetime.datetime:
        return self._end

    def sort_criterion(self) -> str:
        return "_".join([str(s) for s in (self.start, self._end, self.id, self.name)])


class OralSession(PresentationSession):
    def __init__(
        self,
        id: str,
        name: str,
        start: datetime.datetime,
        end: datetime.datetime,
        room: Room | None = None,
        papers: list[Paper] | None = None,
        chairs: list[Person] | None = None,
        presentation_duration: int = 20,
    ):
        super().__init__(id, name, start, end, room, papers, chairs)
        self._presentation_duration = presentation_duration

    def add_paper(self, paper: Paper):
        expected_duration = self._presentation_duration * (len(self.papers) + 1)
        total_duration = (self.end - self.start).seconds / 60

        if expected_duration > total_duration:
            raise Exception(
                f"When adding the paper to session \"{self.id}\", the total duration would become {expected_duration} minutes but the assigned duration is {total_duration} minutes."
            )
        super().add_paper(paper)

class PosterSession(PresentationSession):
    def __init__(
        self,
        id: str,
        name: str,
        start: datetime.datetime,
        end: datetime.datetime,
        room: Room | None = None,
        papers: list[Paper] | None = None,
        chairs: list[Person] | None = None,
    ):
        super().__init__(id, name, start, end, room, papers, chairs)
