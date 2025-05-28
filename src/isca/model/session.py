import datetime

from .person import Person
from .paper import Paper


class Session:
    def __init__(
        self,
        id: str,
        name: str,
        start: datetime.datetime,
        end: datetime.datetime,
    ):
        self.id = id
        self.name = name
        self._start = start
        self._end = end

    @property
    def start(self) -> datetime.datetime:
        return self._start

    @property
    def end(self) -> datetime.datetime:
        return self._end

class PresentationSession(Session):
    def __init__(
        self,
        id: str,
        name: str,
        start: datetime.datetime,
        end: datetime.datetime,
        papers: list[Paper] = [],
        chairs: list[Person] = [],
    ):
        super().__init__(id, name, start, end)
        self._papers = papers
        self._chairs = chairs

    def add_paper(self, paper: Paper):
        self._papers.append(paper)

    def get_paper(self, idx: int) -> Paper:
        if idx >= len(self._papers):
            raise IndexError(
                f'There are {len(self._papers)} in the session, you are asking for the paper at index "{idx}"'
            )

        return self._papers[idx]

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

    @property
    def papers(self) -> list[Paper]:
        return self._papers


class OralSession(Session):
    def __init__(
        self,
        id: str,
        name: str,
        start: datetime.datetime,
        end: datetime.datetime,
        papers: list[Paper] = [],
        chairs: list[Person] = [],
        presentation_duration: int = 20,
    ):
        super().__init__(id, name, start, end, papers, chairs)
        self._presentation_duration = presentation_duration

    def add_paper(self, paper: Paper):
        expected_duration = self._presentation_duration * (len(papers) + 1)
        total_duration = (end - start).seconds / 60

        if expected_duration > total_duration:
            raise Exception(
                f"When adding the paper, the total duration would become {expected_duration} minutes but the assigned duration is {total_duration} minutes."
            )


class PosterSession(Session):
    def __init__(
        self,
        id: str,
        name: str,
        start: datetime.datetime,
        end: datetime.datetime,
        papers: list[Paper] = [],
        chairs: list[Person] = [],
    ):
        super().__init__(id, name, start, end, papers, chairs)
