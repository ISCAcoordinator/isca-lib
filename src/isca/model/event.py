from typing_extensions import Callable

import copy
import datetime

from .core import ISCAItem
from .item import Paper, ScientificSession, Session
from .person import Person, Annuary
from .program import Program, PresentationSession, Room, Timeslot


class Event(ISCAItem):
    def __init__(
        self,
        id: str,
        name: str,
        start_date: datetime.date,
        end_date: datetime.date,
        location: str | None = None,
        url: str | None = None,
        theme: dict[str, object] | None = None,
    ):
        super().__init__(id)
        self.name: str = name
        self.start_date: datetime.date = start_date
        self.end_date: datetime.date = end_date
        self.location: str | None = location
        self.url: str | None = url
        self.theme: dict[str, object] | None = theme

    @property
    def str_dates(self) -> str:
        if self.start_date == self.end_date:
            return self.start_date.strftime("%d/%m/%Y")

        if self.start_date.month == self.end_date.month:
            return self.start_date.strftime("%d") + "-" + self.end_date.strftime("%d/%m/%Y")

        if self.start_date.year == self.end_date.year:
            return self.start_date.strftime("%d/%m") + "-" + self.end_date.strftime("%d/%m/%Y")

        return self.start_date.strftime("%d/%m/%Y") + " -- " + self.end_date.strftime("%d/%m/%Y")


class Conference(Event):
    def __init__(
        self,
        id: str,
        name: str,
        start_date: datetime.date,
        end_date: datetime.date,
        papers: dict[str, Paper],
        program: Program | None = None,
        sessions: list[ScientificSession] | None = None,
        location: str | None = None,
        url: str | None = None,
        serie: str | None = None,
        chairs: list[Person] | None = None,
        issn: str | None = None,
        generate_doi: bool = False,
        theme: dict[str, object] | None = None,
        annuary: Annuary | None = None,
    ):
        super().__init__(id, name, start_date, end_date, location, url, theme)
        self.serie: str | None = serie
        self.issn: str | None = issn
        self.generate_doi: bool = generate_doi
        self.chairs: list[Person] | None = chairs
        self._papers: dict[str, Paper] = papers
        self._sessions: list[ScientificSession] = sessions if sessions is not None else list()
        self._program: Program | None = program
        self._authors2papers: dict[Person, list[Paper]] = dict()
        self._annuary: Annuary = copy.copy(annuary) if annuary is not None else Annuary()

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

    @property
    def program(self) -> Program | None:
        return self._program

    def get_timeslots(self, day: datetime.date | None = None) -> list[Timeslot]:
        assert self._program is not None
        return self._program.get_timeslots(day)

    def add_session(self, session: ScientificSession, force_replace: bool = True):
        if self._program is not None:
            raise NotImplementedError(
                "The conference has a proper program (accessible through the property program), do not use the current method"
            )

        if (session.id in self._sessions) and (not force_replace):
            raise ValueError(f'The session "{session.id}" is already part of the conference')

        # If the session is the presentation, need to adds the papers to the overall access
        if isinstance(session, PresentationSession):
            for presentation in session.presentations:
                if presentation.presented_paper is not None:
                    self.add_paper(presentation.presented_paper, force_replace=False)

        self._sessions.append(session)
        self._sessions = sorted(self._sessions, key=lambda x: x.sort_criterion())  # Sort sessions by starting time

    def remove_session(self, session: ScientificSession):
        if self._program is not None:
            raise NotImplementedError(
                "The conference has a proper program (accessible through the property program), do not use the current method"
            )

        if session.id not in self._sessions:
            raise ValueError(f'The session "{session.id}" is already part of the conference')

        if isinstance(session, PresentationSession):
            for presentation in session.presentations:
                if presentation.presented_paper is not None:
                    self.remove_paper(presentation.presented_paper.id)

        self._sessions.remove(session)

    def resolve_author_paper_association(self):
        for paper in self._papers.values():
            for author in paper.authors:
                if author not in self._authors2papers:
                    self._authors2papers[author] = []
                self._authors2papers[author].append(paper)

    def list_papers(self, author: Person) -> list[Paper]:
        if author not in self._authors2papers:
            return []

        return self._authors2papers[author]

    def compress_annuary(self, select_criterion: Callable[[Person], bool] | None = None):
        if select_criterion is not None:
            self._annuary = self._annuary.compress(select_criterion)
        else:
            self._annuary = self._annuary.compress()

    @property
    def reviewers(self) -> set[Person]:
        return set(self._annuary.reviewers)

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
        if self._program is not None:
            return [s[0] for s in self._program.sessions]
        else:
            return self._sessions.copy()

    @property
    def rooms(self) -> list[Room]:
        if self._program is None:
            raise Exception("The program is not defined, so we can't access to the rooms")
        return self._program.rooms

    def __repr__(self) -> str:
        return f"Conference({self.name}, start={self.start_date}, end={self.end_date}, chairs={self.chairs}, nb_papers={len(self.papers.keys())}, nb_sessions={len(self.sessions)})"
