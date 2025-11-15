"""This module provides all the components to represent any events organised by ISCA"""

# Meta-information
from abc import ABC
from typing_extensions import Callable

# Python core
import copy
import datetime

# Current package requirements
from .core import ISCAItem
from .item import Paper, ScientificSession, Session
from .person import Person, Annuary
from .program import Program, PresentationSession, Room, Timeslot


class Event(ISCAItem, ABC):
    """This class represents any ISCA organised event. (abstract class)

    Attributes
    ----------
    name : str
        the name of the event (human readable)
    start_date : datetime.date
        the starting date of the event
    end_date : datetime.date
        the ending date of the event
    location : str | None
        the location of the event, or None if not defined
    url : str | None
        the URL of the website of the event, or None if not defined
    theme : dict[str, object] | None
        the theme -- the branding information like the list of colors, or None if not defined
    """

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
        """Initialize the event

        Parameters
        ----------
        id : str
            the identifier of the event (software information)
        name : str
            the name of the event (human readable)
        start_date : datetime.date
            the starting date of the event
        end_date : datetime.date
            the ending date of the event
        location : str, optional
            the location of tdhe event (None, if not defined)
        url : str, optional
            the URL of the event's website (None, if not defined)
        theme : dict[str, object], optional
            the theme of the event (None, if not defined)
        """

        super(ISCAItem, self).__init__(id)
        super(ABC).__init__()

        self.name: str = name
        self.start_date: datetime.date = start_date
        self.end_date: datetime.date = end_date
        self.location: str | None = location
        self.url: str | None = url
        self.theme: dict[str, object] | None = theme

    @property
    def str_dates(self) -> str:
        """Generate the date range of the event using the starting and ending date

        Returns
        -------
        str
            the date range of the event (e.g., 24/08/2025 -- 26/08/2025)
        """
        if self.start_date == self.end_date:
            return self.start_date.strftime("%d/%m/%Y")

        if self.start_date.month == self.end_date.month:
            return self.start_date.strftime("%d") + "-" + self.end_date.strftime("%d/%m/%Y")

        if self.start_date.year == self.end_date.year:
            return self.start_date.strftime("%d/%m") + "-" + self.end_date.strftime("%d/%m/%Y")

        return self.start_date.strftime("%d/%m/%Y") + " -- " + self.end_date.strftime("%d/%m/%Y")


class Conference(Event):
    """A Conference is the main type of Event that ISCA organise

    Attributes
    ----------
    serie : str, optional
        the serie of the conference if available, else None
    chairs : list[Person], optional
        the list of chairs of the conference if already known, else None
    issn : str, optional
        the ISSN associated to the conference serie if available, else None
    generate_doi : bool
        flag to determine the DOIs should be generated
    """

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
        """Initialise the conference

        Parameters
        ----------
        id : str
            the identifier of the conference (software information)
        name : str
            the name of the conference (human readable)
        start_date : datetime.date
            the starting date of the conference
        end_date : datetime.date
            the ending date of the conference
        papers : dict[str, Paper]
            the papers submitted (and potentially accepted) to the conference
        program : Program, optional
            the program of the conference, if already defined else None
        sessions : list[ScientificSession], optional
            the list of sessions of the conference if already available, else None
        location : str, optional
            the location of the conference
        url : str, optional
            the URL of the website of the conference, None if not
        serie : str, optional
            the serie of the conference if available, else None
        chairs : list[Person], optional
            the list of chairs of the conference if already known, else None
        issn : str, optional
            the ISSN associated to the conference serie if available, else None
        generate_doi : bool
            flag to determine the DOIs should be generated
        theme : dict[str, object], optional
             the theme -- the branding information like the list of colors, or None if not defined
        annuary : Annuary, optional
            the annuary of of available persons, None if not available yet

        """

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

    ###########################################################################################################
    ## Paper operations
    ###########################################################################################################

    def add_paper(self, paper: Paper, force_replace: bool = True):
        """Add a paper to the conference

        Parameters
        ----------
        paper : Paper
            the paper to add to the conference
        force_replace : bool
            flag to indicate if the the paper should be replaced if it is already part of the confernece

        Raises
        ------
        ValueError
            if the paper already exists and the force flag is not set to True

        """
        if (paper.id in self._papers) and (not force_replace):
            raise ValueError(f'The paper "{paper.id}" is already part of the conference')
        self._papers[paper.id] = paper

    def remove_paper(self, paper: str | Paper) -> Paper | None:
        """Remove a paper from the conference

        Parameters
        ----------
        paper : Paper | str
            the paper to be removed

        Returns
        -------
        Paper | None
            the previously stored paper if available, else None
        """

        if isinstance(paper, Paper):
            paper_id = paper.id
        else:
            paper_id = paper

        if paper_id not in self._papers:
            self.logger.warning(f'The paper "{paper_id}" is not part of this conference')
            return None

        return self._papers[paper_id]

    def get_paper(self, paper_id: str) -> Paper:
        """Retrieve the paper given its identifier

        Parameters
        ----------
        paper_id : str
            the identifier of the paper to retrieve

        Returns
        -------
        Paper
            the paper corresponding to the identifier

        Raises
        ------
        KeyError
            the identifier doesn't point to any existing paper

        """

        if paper_id not in self._papers:
            raise KeyError(f'The paper "{paper_id}" is not part of this conference')
        return self._papers[paper_id]

    def update_paper(self, paper: Paper):
        """Update the paper

        Parameters
        ----------
        paper : Paper
            the paper to be updated

        """

        self.add_paper(paper, force_replace=True)

    @property
    def papers(self) -> dict[str, Paper]:
        """Get the list of papers

        The list of papers is given in the form of a dictionary [paper_id, Paper]

        Returns
        -------
        dict[str, Paper]
            the papers in the form of a dictionary [paper_id, Paper]

        """

        return self._papers.copy()

    ###########################################################################################################
    ## Program and session operations
    ###########################################################################################################

    def add_session(self, session: ScientificSession, force_replace: bool = True):
        """Add a session to the list of sessions (should not be used if the program is defined)

        This method should only be used if the program is not defined

        Parameters
        ----------
        session : ScientificSession
            the session to add
        force_replace : bool
            flag to force the replacement of the session if the session ID already exists in the conference

        Raises
        ------
        ValueError
            if the session already exists and the force flag is not set to True
        NotImplementedError
            if the conference contains a program
        """

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

    def remove_session(self, session: ScientificSession | str):
        """Remove the session from the list of sessions (should be used if the program is defined)

        Parameters
        ----------
        session : ScientificSession | str
            the session to remove

        Raises
        ------
        NotImplementedError
            if the conference contains a program
        """

        if self._program is not None:
            raise NotImplementedError(
                "The conference has a proper program (accessible through the property program), do not use the current method"
            )

        if isinstance(session, str):
            session_id = session
        else:
            session_id = session.id

        if session_id not in self._sessions:
            self.logger.warning(f'The session "{session_id}" is not part of the list of sessions, so we ignore this')
            return

        cur_session = self._sessions[session_id]
        if isinstance(cur_session, PresentationSession):
            for presentation in cur_session.presentations:
                if presentation.presented_paper is not None:
                    self.remove_paper(presentation.presented_paper.id)

        self._sessions.remove(cur_session)

    def get_timeslots(self, day: datetime.date | None = None) -> list[Timeslot]:
        """Get the timeslots of a given day, or all the timeslots

        This method requires the program to be defined

        Parameters
        ----------
        day : datetime.date, optional
            the given day, if None assumes all the timeslots should be
            provided

        Returns
        -------
        list[Timeslot]
            the list of timeslots

        """

        assert self._program is not None, "The program is not defined for the current conference"
        return self._program.get_timeslots(day)

    @property
    def sessions(self) -> list[Session]:
        """Get the list of sessions composing the conference

        if the program is defined, extract the list of sessions from the program, else it simply provides
        a copy of the list of sessions

        Returns
        -------
        list[Session]
            the list of sessions composing the conference

        """
        if self._program is not None:
            sessions = list(set([(s[1], s[0]) for s in self._program.sessions]))
            sessions = sorted(sessions, key=lambda x: str(x[0].start) + "_" + str(x[0].id))
            return [s[1] for s in sessions]
        else:
            return self._sessions.copy()

    @property
    def program(self) -> Program | None:
        """Get the program

        Returns
        -------
        list[Session]
            the program or None if there is no program
        """
        return self._program

    @property
    def rooms(self) -> list[Room]:
        """Get the rooms required by the conference (requires the program to be defined)

        Returns
        -------
        list[Room]
            the list of rooms used by the conference

        Raises
        ------
        NotImplementedError
            if the program is not defined
        """
        if self._program is None:
            raise NotImplementedError("The program is not defined, so we can't access to the rooms")

        return self._program.rooms

    ###########################################################################################################
    ## Annuary, person related operations
    ###########################################################################################################

    def compress_annuary(self, select_criterion: Callable[[Person], bool] | None = None):
        """Compress the annuary by removing all the authors not fitting the criterion

        Parameters
        ----------
        select_criterion : Callable[[Person], bool], optional
            the criterion to select the person to keep in the annuary,
            xx

        """

        if select_criterion is not None:
            self._annuary = self._annuary.compress(select_criterion)
        else:
            self._annuary = self._annuary.compress()

    def list_papers(self, author: Person) -> list[Paper]:
        """List the papers of a given author

        Parameters
        ----------
        author : Person
            the author for which the papers have to be listed

        Returns
        -------
        list[Paper]
            the list of papers from the given author

        """
        if author not in self._authors2papers:
            return []

        return self._authors2papers[author]

    def _resolve_author_paper_association(self):
        """Update the authors/papers associations using the dataset of papers of the conference"""
        self._authors2papers = dict()
        for paper in self._papers.values():
            for author in paper.authors:
                if author not in self._authors2papers:
                    self._authors2papers[author] = []
                self._authors2papers[author].append(paper)

    @property
    def reviewers(self) -> set[Person]:
        """Get the reviewers

        Returns
        -------
        set[Person]
            the reviewers of the conference

        """

        return set(self._annuary.reviewers)

    @property
    def authors(self) -> set[Person]:
        """Get the authors

        Returns
        -------
        set[Person]
            the authors of the conference

        Examples
        --------
        FIXME: Add docs.

        """
        return set(self.authors_with_papers.keys())

    @property
    def authors_with_papers(self) -> dict[Person, list[Paper]]:
        """Get the authors and their papers

        Returns
        -------
        dict[Person, list[Paper]]
            the authors of the conference with the list of their
            papers

        """
        if not self._authors2papers.keys():
            self._resolve_author_paper_association()

        return self._authors2papers

    ###########################################################################################################
    ## Class helpers
    ###########################################################################################################
    def __repr__(self) -> str:
        """return repr(self)"""
        return f"Conference({self.name}, start={self.start_date}, end={self.end_date}, chairs={self.chairs}, nb_papers={len(self.papers.keys())}, nb_sessions={len(self.sessions)})"
