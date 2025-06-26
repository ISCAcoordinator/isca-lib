import datetime

from .paper import Paper
from .person import Person
from .session import Session, PresentationSession, Room


class Event:
    def __init__(
        self,
        id: str,
        name: str,
        start_date: datetime.date,
        end_date: datetime.date,
        location: str | None = None,
        url: str | None = None,
    ):
        self._id: str = id
        self.name: str = name
        self.start_date: datetime.date = start_date
        self.end_date: datetime.date = end_date
        self.location: str | None = location
        self.url: str | None = url


class Conference(Event):
    def __init__(
        self,
        id: str,
        name: str,
        start_date: datetime.date,
        end_date: datetime.date,
        location: str | None = None,
        url: str | None = None,
        serie: str | None = None,
        chairs: list[Person] | None = None,
        issn: str | None = None,
        generate_doi: bool = False,
    ):
        super().__init__(id, name, start_date, end_date, location, url)
        self.serie: str | None = serie
        self.issn: str | None = issn
        self.generate_doi: bool = generate_doi
        self.chairs: list[Person] | None = chairs
        self._papers: dict[str, Paper] = dict()
        self._sessions: list[Session] = list()
        self._authors2papers: dict[Person, list[Paper]] = dict()
        self._annuary: dict[str, Person] = dict()

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

    def resolve_author_paper_association(self):
        for paper in self._papers.values():
            for author in paper.authors:
                if author not in self._authors2papers:
                    self._authors2papers[author] = []
                self._authors2papers[author].append(paper)

    def list_papers(self, author: Person) -> list[Paper]:
        if (author not in self._authors2papers):
            return []

        return self._authors2papers[author]

    @property
    def authors(self) -> set[Person]:
        return set(self.authors_with_papers.keys())

    @property
    def authors_with_papers(self) -> dict[Person, list[Paper]]:
        if not self._authors2papers.keys():
            self.resolve_author_paper_association()

        return self._authors2papers

    @property
    def papers(self) -> dict[str, Paper]:
        return self._papers.copy()

    @property
    def sessions(self) -> list[Session]:
        return self._sessions.copy()

    @property
    def rooms(self) -> set[Room]:
        rooms = set()
        for cur_session in self.sessions:
            if isinstance(cur_session, PresentationSession):
                rooms.add(cur_session.room)
        return rooms

    def __repr__(self) -> str:
        return f"Conference({self.name}, start={self.start_date}, end={self.end_date}, chairs={self.chairs}, nb_papers={len(self.papers.keys())}, nb_sessions={len(self.sessions)})"
