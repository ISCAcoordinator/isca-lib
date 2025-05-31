import datetime

from .paper import Paper
from .person import Person
from .session import Session, PresentationSession


class Event:
    def __init__(self, id: str, name: str, start_date: datetime.date, end_date: datetime.date, serie: str | None):
        self._id: str = id
        self._name: str = name
        self._serie: str | None = serie
        self.start_date: datetime.date = start_date
        self.end_date: datetime.date = end_date


class Conference(Event):
    def __init__(
        self,
        id: str,
        name: str,
        start_date: datetime.date,
        end_date: datetime.date,
        serie: str | None = None,
        chairs: list[Person] | None = None,
    ):
        super().__init__(id, name, start_date, end_date, serie)
        self.chairs: list[Person] | None = chairs
        self._papers: dict[str, Paper] = dict()
        self._sessions: list[Session] = list()

    def add_paper(self, paper: Paper, force_replace: bool = True):
        if (paper.id in self._papers) and (not force_replace):
            raise ValueError(f'The paper "{paper.id}" is already part of the conference')
        self._papers[paper.id] = paper

    def remove_paper(self, paper_id: str) -> Paper:
        if paper_id not in self._papers:
            print(f'The paper "{paper_id}" is not part of this conference')
        paper = self._papers[paper_id]
        return paper

    def get_paper(self, paper_id: str) -> Paper:
        if paper_id not in self._papers:
            raise KeyError(f'The paper "{paper_id}" is not part of this conference')
        return self._papers[paper_id]

    def update_paper(self, paper: Paper):
        self.add_paper(paper, force_replace=True)

    def add_session(self, session: Session, force_replace: bool = True):
        if (session.id in self._sessions) and (not force_replace):
            raise ValueError(f'The session "{session.id}" is already part of the conference')

        # If the session is the presentation, need to adds the papers to the overall access
        if isinstance(session, PresentationSession):
            for paper in session.papers:
                self.add_paper(paper, force_replace=False)

        self._sessions.append(session)
        self._sessions = sorted(self._sessions, key=lambda x: x.sort_criterion())  # Sort sessions by starting time

    def remove_session(self, session: Session):
        if session.id not in self._sessions:
            raise ValueError(f'The session "{session.id}" is already part of the conference')

        if isinstance(session, PresentationSession):
            for paper in session.papers:
                self.add_paper(paper, force_replace=False)

        self._sessions.remove(session)

    @property
    def papers(self) -> dict[str, Paper]:
        return self._papers.copy()
