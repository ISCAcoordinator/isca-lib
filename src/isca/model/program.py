"""Module to manipulate the program of an event

This module provides all the helpers to manipulate the program of an event.
This imples:
   - timeslots which are simply allocated times
   - presentations which can be oral, poster, keynotes, ...
   - sessions which can vary from different scientific sessions (oral, poster, keynotes) to social sessions
   - program components (room and the actual program)

If the program is used, the entry point should be an instance of the class Program.
While not defined as a singleton to allow temporary programs, it is recommended to only associate one program to one event
"""
from typing_extensions import Callable

from enum import Enum
import copy
import datetime
import numpy as np
import numpy.typing as npt

from .core import ISCAObject, ISCAItem
from .item import Paper, ScientificSession, Session
from .person import Person


#########################################################################################################
### Timeslot classes
#########################################################################################################


class TimeslotType(Enum):
    "Enumeration to distinguish the different types of timeslot"
    CEREMONY = 0
    KEYNOTE = 1
    COFFEE_BREAK = 2
    LUNCH_BREAK = 3
    ASSEMBLY = 4
    SCIENCE = 5
    TUTORIAL = 6
    GENERAL_ASSEMBLY = 7
    SOCIAL = 8

    def __str__(self) -> str:
        """Return the string representation of the role

        Returns
        -------
        str
            the (uppercase) name of the role
        """
        return f'{self.name.replace("TimeslotType.", "")}'


class AnonymousTimeslot:
    """Class representing an anonymous timeslot

    An anonymous timeslot is defined only by start and end time.
    ***The start and end date should be the same!***

    This is not only used as a super class, but can also be used to represent buffer slots.

    Attributes
    ----------
    start: datetime
       The starting date and time of the timeslot
    end: datetime
       The finishing date and time of the timeslot
    """

    def __init__(
        self,
        start: datetime.datetime,
        end: datetime.datetime,
    ):
        """Initialisation method

        Parameters
        ----------
        start : datetime.datetime
            The starting date and time of the timeslot
        end : datetime.datetime
            The finishing date and time of the timeslot
        """

        self.start: datetime.datetime = start
        self.end: datetime.datetime = end

        assert (
            self.start.date() == self.end.date()
        ), f"The starting date ({self.start.strftime('%Y-%m-%d')}) and the finishing date ({self.end.strftime('%Y-%m-%d')}) are not the same"

    @property
    def date(self) -> datetime.date:
        """Return the date of the timeslot

        Returns
        -------
        datetime.date
            The date of the timeslot
        """
        return self.start.date()

    @property
    def duration(self) -> int:
        """Returns the duration of the timeslot in number of minutes

        It is assumed that a timeslot lasts at least one minute....

        Returns
        -------
        int
            The duration of the timeslot in minutes

        """
        duration = self.end - self.start
        return duration.seconds // 60

    def __repr__(self) -> str:
        """Generate a string representation of the timeslot

        Returns
        -------
        str
            The string representation of the timeslot
        """

        date = self.date.strftime("%Y-%m-%d")
        start = self.start.strftime("%H:%M")
        end = self.end.strftime("%H:%M")
        return f"AnonymousTimeslot(date={date}, start={start}, end={end})"

    def __str__(self) -> str:
        """Generate a string representation of the timeslot

        Returns
        -------
        str
            The string representation of the timeslot
        """
        return repr(self)

    def timeslot_without_date(self) -> str:
        """Generate a string to represent the time slot of the timeslot (ignoring the date)

        Returns
        -------
        str
            The string representation of the timeslot of the timeslot
        """
        start = self.start.strftime("%H:%M")
        end = self.end.strftime("%H:%M")
        return f"{start} -- {end}"


class Timeslot(AnonymousTimeslot, ISCAItem):
    """Class representing a timeslot in an event

    Any timeslots should use this class in priority and fall back to
    AnonymousTimeslot only if required

    Attributes
    ----------
    name: str
        The name of the timeslot
    type: TimeslotType
        The type of the timeslot (see TimeslotType for the different types of timeslots)
    """

    def __init__(
        self,
        id: str,
        name: str,
        type: TimeslotType,
        start: datetime.datetime,
        end: datetime.datetime,
    ):
        """Initialisation method

        Parameters
        ----------
        id : str
            The identifier of the timeslot
        name : str
            The name of the timeslot
        type : TimeslotType (see TimeslotType for the different types of timeslots)
            The type of the timeslot
        start : datetime.datetime
            The starting time of the timeslot
        end : datetime.datetime
            The finishing time of the timeslot
        """

        AnonymousTimeslot.__init__(self, start, end)
        ISCAItem.__init__(self, id)
        self.name: str = name
        self.type: TimeslotType = type

    def __hash__(self) -> int:
        """Helper to generate a hash to identify the timeslot

        The hash is basically "hash(id)"
        FIXME: see where it is used

        Returns
        -------
        int
            the hash identifying the session
        """

        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Helper to compare two timeslots

        Parameters
        ----------
        other : object
            the other object to be compared to the current timeslot

        Returns
        -------
        bool
            True if the other object is the same timeslot, False else

        """
        if not isinstance(other, Timeslot):
            return False

        return self.id == other.id

    def __repr__(self) -> str:
        """Get a string representation of the timeslot

        Returns
        -------
        str
            The string representation of the timeslot
        """
        date = self.date.strftime("%Y-%m-%d")
        start = self.start.strftime("%H:%M")
        end = self.end.strftime("%H:%M")
        return f"Timeslot(id={self.id}, name={self.name}, type={self.type}, date={date}, start={start}, end={end})"

    def __str__(self) -> str:
        """Get a string representation of the timeslot

        Returns
        -------
        str
            The string representation of the timeslot
        """
        return repr(self)


#########################################################################################################
### Presentation classes
#########################################################################################################
class Presentation(ISCAItem):
    """Class representing a presentation which will take place in a session

    Attributes
    ----------
    title: str
        The title of the presentation
    presenters: list[Person], optional
        The presenters of the presentation, None if not **yet** defined
    abstract: str, optional
        The abstract of the presentation
    _duration: int, optional
        The duration of the presentation (in minutes),
    _presented_paper: Paper, optional
        The paper associated to the presentation (if any)
    """

    def __init__(
        self,
        id: str,
        title: str,
        presenters: list[Person] | None,
        duration: int | None,
        abstract: str | None = None,
        presented_paper: Paper | None = None,
    ):
        super().__init__(id)

        self.title: str = title
        self.presenters: list[Person] | None = presenters
        self.abstract: str | None = abstract
        self._duration: int | None = duration
        self._presented_paper: Paper | None = presented_paper

    @property
    def duration(self) -> int | None:
        """Get the duration of the session

        Returns
        -------
        int | None
            The duration of the session, None if no duration (poster)
        """
        return self._duration

    @property
    def presented_paper(self) -> Paper | None:
        """Get the paper associated to the presentation

        Returns
        -------
        Paper | None
            The presented paper, None if no paper is associated to the presentation (e.g., keynote)

        """
        return self._presented_paper

    def __repr__(self) -> str:
        """Return the string representation of the presentation

        Returns
        -------
        str
            The string representation of the presentation
        """
        talk_info = f"[{self.__class__.__name__} - {self.id}] {self.title}"
        if self.presenters is not None:
            talk_info += "\n"
            talk_info += "presenter(s): "
            presenters = []
            for presenter in self.presenters:
                presenters.append(str(presenter))
            talk_info += "; ".join(presenters)

        return talk_info

    def __str__(self) -> str:
        """Return the string representation of the presentation

        Returns
        -------
        str
            The string representation of the presentation
        """
        return repr(self)


class OralPresentation(Presentation):
    """Class representing an oral presentation"""

    def __init__(
        self,
        id: str,
        title: str,
        presenters: list[Person] | None,
        duration: int,
        abstract: str | None = None,
        presented_paper: Paper | None = None,
    ):
        """Initialisation method

        Parameters
        ----------
        id : str
            The identifier of the presentation
        title : str
            The title of the presentation
        presenters : list[Person], optional
            The list of presenters
        duration : int
            The duration of the presentation
        abstract : str, optional
            The abstract of the presentation
        presented_paper : Paper, optional
            The paper associated to the presentation
        """

        super().__init__(id, title, presenters, duration, abstract, presented_paper)

    @property
    def duration(self) -> int:
        """Get the duration of the presentation in number of minutes

        Returns
        -------
        int
            The duration of the presentation in number of minutes
        """

        assert self._duration is not None, "The duration of an oral presentation is required"
        return self._duration


class PosterPresentation(Presentation):
    """Class representing an oral presentation"""

    def __init__(
        self,
        id: str,
        title: str,
        presenters: list[Person] | None,
        abstract: str | None = None,
        presented_paper: Paper | None = None,
    ):
        """Initialisation method

        Parameters
        ----------
        id : str
            The identifier of the presentation
        title : str
            The title of the presentation
        presenters : list[Person], optional
            The list of presenters
        abstract : str, optional
            The abstract of the presentation
        presented_paper : Paper, optional
            The paper associated to the presentation
        """
        super().__init__(id, title, presenters, None, abstract, presented_paper)


class Keynote(OralPresentation):
    """Class representing a keynote presentation"""

    def __init__(
        self,
        id: str,
        title: str,
        presenters: list[Person] | None,
        duration: int,
        abstract: str | None = None,
    ):
        """Initialisation method

        Parameters
        ----------
        id : str
            The identifier of the keynote
        title : str
            The title of the keynote
        presenters : list[Person], optional
            The list of presenters
        duration : int
            The duration of the keynote
        abstract : str, optional
            The abstract of the keynote
        """
        super().__init__(id, title, presenters, duration, abstract, None)


#########################################################################################################
### Sessions
#########################################################################################################
class SocialSession(Session):
    """Class representing a social session"""

    def __init__(self, id: str, name: str):
        """Initialisation method

        Parameters
        ----------
        id : str
            The identifier of the session
        name : str
            The name of the session
        """

        super().__init__(id, name)


class PresentationSession(ScientificSession):
    """Class representing a session which contains presentations

    Attributes
    ----------
    chairs: list[Person], optional
        The list of the chairs of the session
    _presentations: list[Presentation]
        The list of presentations taking place in the session
    """

    def __init__(
        self,
        id: str,
        name: str,
        start: datetime.datetime,
        end: datetime.datetime,
        presentations: list[Presentation] | None = None,
        chairs: list[Person] | None = None,
    ):
        super().__init__(id, name)
        self._presentations: list[Presentation] = presentations if presentations is not None else []
        self.chairs: list[Person] = chairs if chairs is not None else []

        # For now, start/end can't be modified to avoid side effects!
        self._start: datetime.datetime = start
        self._end: datetime.datetime = end

    @property
    def start(self) -> datetime.datetime:
        return self._start

    @property
    def end(self) -> datetime.datetime:
        return self._end

    @property
    def presentations(self) -> list[Presentation]:
        """Returns a *copy* of the list of presentations

        Returns
        -------
        list[Presentation]
            A copy of the list of presentations
        """

        return self._presentations.copy()

    @property
    def papers(self) -> list[Paper]:
        """Returns the list of presented papers

        Returns
        -------
        list[Paper]
            The list of presented papers
        """

        papers = []
        for p in self._presentations:
            if p.presented_paper is not None:
                papers.append(p.presented_paper)
        return papers

    def add_presentation(self, presentation: Presentation):
        """Add a presentation to the session

        Parameters
        ----------
        presentation : Presentation
            The presentation to add to the session
        """
        self._presentations.append(presentation)

    def is_in_session(self, presentation: Presentation) -> bool:
        """Check if a presentation is in the session

        Parameters
        ----------
        presentation : Presentation
            The presentation

        Returns
        -------
        bool:
            True if the presentation is part of the session, else False

        Examples
        --------
        FIXME: Add docs.


        """
        return presentation in self._presentations

    def remove_presentation(self, presentation: Presentation):
        """Remove a given presentation from the session

        Parameters
        ----------
        presentation : Presentation
            The presentation to remove
        """
        if self.is_in_session(presentation):
            self._presentations.remove(presentation)
        else:
            self._logger.warning(f"The presentation {presentation} is not part of the session {self}")

    def replace_presentation(self, presentation_out: Presentation, presentation_in: Presentation):
        idx = self._presentations.index(presentation_out)
        if idx < 0:
            raise ValueError(f'"{presentation_out.id}" is not part of the session, so it can\'t be replaced')
        self._presentations[idx] = presentation_in

    def start_presentation(self, _: Presentation | int) -> datetime.datetime:
        raise NotImplementedError("this method should be implemented in the subclass")
        # return self.start

    def end_presentation(self, _: Presentation | int) -> datetime.datetime:
        raise NotImplementedError("this method should be implemented in the subclass")
        # return self.end

    def sort_criterion(self) -> str:
        """Generates the criterion used to sort different sessions

        The criterion is based in order:
            1. the start time
            2. the end time
            3. the identifier

        Returns
        -------
        str:
            the sorting criterion


        """
        return "_".join([str(s) for s in (self.start, self._end, self.id)])


class OralSession(PresentationSession):
    """Class representing an oral session

    An oral session can only contains *oral* presentations

    Attributes
    ----------
    _default_presentation_duration: int
        The duration assigned by default to a presentation (if no duration is specified)
    """

    def __init__(
        self,
        id: str,
        name: str,
        start: datetime.datetime,
        end: datetime.datetime,
        presentations: list[Presentation] | None = None,
        chairs: list[Person] | None = None,
        default_presentation_duration: int = 20,
    ):
        """Initialisation method

        Parameters
        ----------
        id : str
            the identifier of the session
        name : str
            The name of the session
        start : datetime.datetime
            The start of the session
        end : datetime.datetime
            The end of the session
        presentations : list[Presentation], optional
            The initial list of *oral* presentations of the sessions
        chairs : list[Person], optional
            The list of the chairs of the session
        default_presentation_duration : int  [20]
            The default duration (in minutes) of a presentation in the session

        """

        super().__init__(id, name, start, end, None, chairs)

        if presentations is not None:
            for p in presentations:
                self.add_presentation(p)

        self._default_presentation_duration: int = default_presentation_duration

    def add_presentation(self, presentation: Presentation):
        """Add an oral presentation to the session

        Parameters
        ----------
        presentation : Presentation
            The *oral* presentation

        Raises
        ------
        Exception
            If the presentation is not an instance of OralPresentation
        """
        if not isinstance(presentation, OralPresentation):
            raise Exception(f"[{self.id}] The presentation ({presentation.id}) should be an Oral Presentation")

        total_duration = (self.end - self.start).seconds / 60
        expected_duration = 0
        for cur_presentation in self.presentations:
            expected_duration += cur_presentation.duration
        expected_duration += presentation.duration

        expected_duration = self._default_presentation_duration * (len(self.presentations) + 1)

        if expected_duration > total_duration:
            raise Exception(
                f'[{self.id}] When adding the presentation to session "{self.id}", the total duration would become {expected_duration} minutes but the assigned duration is {total_duration} minutes.'
            )
        super().add_presentation(presentation)

    def start_presentation(self, presentation: Presentation | int) -> datetime.datetime:
        """Get the starting time of a presentation of the sessession

        Parameters
        ----------
        presentation : Presentation | int
            The presentation for which we want the starting time

        Returns
        -------
        datetime.datetime
            The starting time of the presentation

        Raises
        --------
        AssertError
            if the presentation is not part of the session
        """

        start = self.start

        if isinstance(presentation, int):
            assert presentation < len(
                self.presentations
            ), f"[{self.id}] There are not enough presentation in the session ({len(self.presentations)} < {presentation})"

            for pres_idx, cur_presentation in enumerate(self.presentations):
                if pres_idx >= presentation:
                    break

                assert cur_presentation.duration is not None
                start += datetime.timedelta(minutes=cur_presentation.duration)
        else:
            found = False
            for cur_presentation in self.presentations:
                if presentation == cur_presentation:
                    found = True
                    break

                assert cur_presentation.duration is not None
                start += datetime.timedelta(minutes=cur_presentation.duration)

            assert found, f"{presentation} is not part of the session"

        return start

    def end_presentation(self, presentation: Presentation | int) -> datetime.datetime:
        """Get the starting time of a presentation of the sessession

        Parameters
        ----------
        presentation : Presentation | int
            The presentation for which we want the starting time

        Returns
        -------
        datetime.datetime
            The starting time of the presentation

        Raises
        --------
        AssertError
            if the presentation is not part of the session
        """

        if isinstance(presentation, int):
            presentation = self.presentations[presentation]

        assert presentation.duration is not None
        return self.start_presentation(presentation) + datetime.timedelta(minutes=presentation.duration)

    def timeslot_presentation(self, presentation: Presentation | int) -> AnonymousTimeslot:
        """Retrieve the time related information of a presentation as a timeslot

        Parameters
        ----------
        presentation : Presentation | int
            The presentation

        Returns
        -------
        AnonymousTimeslot
            An anonymous timeslot associated to the presentation
        """

        return AnonymousTimeslot(self.start_presentation(presentation), self.end_presentation(presentation))

    @property
    def default_duration(self) -> int:
        """Helper to get he default duration of a presentation in the session

        Returns
        -------
        int
            The default duration
        """
        return self._default_presentation_duration


class KeynoteSession(OralSession):
    """Class representing a keynote session

    A keynote session only contains keynotes.
    For now, multiple keynotes are supported but this could change in the future.

    """

    def __init__(
        self,
        id: str,
        name: str,
        start: datetime.datetime,
        end: datetime.datetime,
        presentations: list[Presentation] | None = None,
        chairs: list[Person] | None = None,
        default_presentation_duration: int = 60,
    ):
        """Initialisation method

        Parameters
        ----------
        id : str
            the identifier of the session
        name : str
            The name of the session
        start : datetime.datetime
            The start of the session
        end : datetime.datetime
            The end of the session
        presentations : list[Presentation], optional
            The initial list of keynote presentations of the sessions
        chairs : list[Person], optional
            The list of the chairs of the session
        default_presentation_duration : int  [60]
            The default duration (in minutes) of a presentation in the session

        """
        super().__init__(id, name, start, end, None, chairs, default_presentation_duration)

        if presentations is not None:
            for p in presentations:
                self.add_presentation(p)

        self._default_presentation_duration: int = default_presentation_duration

    def add_presentation(self, presentation: Presentation):
        if not isinstance(presentation, Keynote):
            raise Exception(f"[{self.id}] The presentation ({presentation.id}) should be a Keynote")

        super().add_presentation(presentation)


class PosterSession(PresentationSession):
    """Class representing a poster session

    A poster session doesn't have a default duration as all presentations are taking the full sessions.
    All presentations are assumed to be instances of Poster
    """

    def __init__(
        self,
        id: str,
        name: str,
        start: datetime.datetime,
        end: datetime.datetime,
        presentations: list[Presentation] | None = None,
        chairs: list[Person] | None = None,
    ):
        """Initialisation method

        Parameters
        ----------
        id : str
            the identifier of the session
        name : str
            The name of the session
        start : datetime.datetime
            The start of the session
        end : datetime.datetime
            The end of the session
        presentations : list[Presentation], optional
            The initial list of *oral* presentations of the sessions
        chairs : list[Person], optional
            The list of the chairs of the session
        """
        super().__init__(id, name, start, end, None, chairs)

        if presentations is not None:
            for p in presentations:
                self.add_presentation(p)

    def add_presentation(self, presentation: Presentation):
        if not isinstance(presentation, PosterPresentation):
            raise Exception(f"[{self.id}] The presentation ({presentation.id}) should be a Poster")

        super().add_presentation(presentation)


#########################################################################################################
### Program
#########################################################################################################


class Room(ISCAItem):
    """Class representing a room where a (or multiple) session(s) will take place

    Multiple sessions can take place in one room.
    In this case, the room should be divided in multiple zones.
    Only one session can be associated to one zone.

    Attributes
    ----------
    name : str
        The name of the room
    type : str
        The type of the room
    _zones : list[str]
        The zones composing the room
    """

    def __init__(self, id: str, name: str, type: str, nb_zones: int | None = 1, zones: list[str] | None = None):
        """Initialisation method

        Parameters
        ----------
        id : str
            The identifier of the room
        name : str
            The name of the room
        type : str
            The type of the room
        nb_zones : int, optional
            The number of zones in the room. If None, only one zone or the zones to be defined using the "zones" parameter
        zones : list[str], optional
            the list of zone names. If None, use the number of zones, or only the room is composed of only one zone

        Raises
        ------
        Exception
            Both the number of zones and the list of zones are given
        """
        super().__init__(id)
        self.name: str = name
        self.type: str = type
        self._zones: list[str] = ["Z1"]
        if (zones is not None) and (nb_zones is not None):
            raise Exception(f"[{id}] either the number of zones OR the list of zones should be given but not both")
        elif (nb_zones is not None) and (nb_zones > 1):
            self._zones = [f"Z{i_zone}" for i_zone in range(1, nb_zones + 1)]
        elif zones is not None:
            self._zones = zones

    @property
    def nb_zones(self) -> int:
        """Get the number of zones composing the room

        Returns
        -------
        int
            The number of zones of the room
        """
        return len(self._zones)

    @property
    def zones(self) -> list[str]:
        """Get the names of the zones composing the room

        Returns
        -------
        list[str]
            The list of zone names
        """
        return self._zones.copy()

    def __hash__(self) -> int:
        """Hashing method to get a unique identifier of the room

        Returns
        -------
        int
            hash(self._id)
        """
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Helper to compare two rooms

        Parameters
        ----------
        other : object
            the other object to be compared to the current room

        Returns
        -------
        bool
            True if the other object is the same room, False else

        """
        if not isinstance(other, Room):
            return False

        return self.id == other.id

    def __str__(self) -> str:
        """Generate a string representation of the room

        Returns
        -------
        str
            The string representation of the room
        """
        str = f"{self.name}"
        str += f" (zones={self.zones})"

        return str + f" [{self.type}]"

    def __repr__(self) -> str:
        """Generate a string representation of the room

        Returns
        -------
        str
            The string representation of the room
        """
        return f"Room(id={self.id}, name={self.name}, nb_zones={self.nb_zones})"


class Program(ISCAObject):
    """Class representing the program of an event

    A program can be seen as a matrix associating timeslots to rooms.
    For each zone of each room a session is associated to a given timeslot


    """

    def __init__(self, timeslots: list[Timeslot], rooms: list[Room]):
        """Initialisation method

        It just allocates the matrix with empty sessions.
        Sessions have to be added using the dedicated method.


        Parameters
        ----------
        timeslots : list[Timeslot]
            the list of timeslots
        rooms : list[Room]
            the list of rooms
        """
        super().__init__()
        self._timeslots: list[Timeslot] = sorted(timeslots, key=lambda x: x.start)
        self._rooms: list[Room] = rooms
        self._program_matrix: npt.NDArray[list[Session]] = np.full((len(self._timeslots), len(self._rooms)), None)

    @property
    def timeslots(self) -> list[Timeslot]:
        """Returns a copy of the list of timeslots

        Returns
        -------
        list[Timeslot]
            The list of timeslots
        """
        return copy.deepcopy(self._timeslots)

    @property
    def rooms(self) -> list[Room]:
        """Returns a copy of the list of rooms

        Returns
        -------
        list[Room]
            The list of rooms
        """
        return copy.deepcopy(self._rooms)

    @property
    def sessions(self) -> list[tuple[Session, Timeslot, Room, int]]:
        """Get all the sessions

        Returns
        -------
        list[tuple[Session, Timeslot, Room, int]]
            All the information related to a session (the session, the
            timeslot, the room and index of the zone of the session in
            the room)
        """
        sessions = []
        for timeslot_idx, timeslot in enumerate(self._timeslots):
            timeslot_content = self._program_matrix[timeslot_idx]
            for room_idx, room in enumerate(self._rooms):
                if timeslot_content[room_idx] is not None:
                    for zone_idx, session in enumerate(timeslot_content[room_idx]):
                        if session is not None:
                            sessions.append((session, timeslot, room, zone_idx))

        return sessions

    def get_timeslots(self, day: datetime.date | None = None) -> list[Timeslot]:
        """Returns all the timeslots of a given day sorted by starting time.

        Parameters
        ----------
        day : datetime.date, optional
            The day for which we want the timeslots of (or None to get
            all the timeslots)

        Returns
        -------
        list[Timeslot]
            The list of timeslots
        """
        if day is None:
            return self._timeslots

        timeslots = []
        for timeslot in self._timeslots:
            if timeslot.start.date() == day:
                timeslots.append(timeslot)

        return sorted(timeslots, key=lambda x: x.start)

    def get_day_sessions(self, day: datetime.date) -> list[tuple[Session, Timeslot, Room, int]]:
        """Returns all the sessions of a given day sorted by starting time.

        Parameters
        ----------
        day : datetime.date, optional
            The day for which we want the sessions of

        Returns
        -------
        list[tuple[Session, Timeslot, Room, int]]
            The list of sessions (a session is composed of the session  itself, the
            timeslot, the room and index of the zone of the session in
            the room)
        """
        sessions = []
        timeslots = self.get_timeslots(day)
        for timeslot in timeslots:
            timeslot_idx = self._timeslots.index(timeslot)  # NOTE: could be improved to be faster
            timeslot_content = self._program_matrix[timeslot_idx]
            for room_idx, room in enumerate(self._rooms):
                if timeslot_content[room_idx] is not None:
                    for zone_idx, session in enumerate(timeslot_content[room_idx]):
                        if session is not None:
                            sessions.append((session, timeslot, room, zone_idx))

        return sorted(sessions, key=lambda x: str(x[1].start) + "_" + str(x[0].id))

    def get_timeslot_sessions(self, timeslot: Timeslot | int) -> dict[Room, dict[int, Session]]:
        """Get all the sessions taking place at a given timeslot

        Parameters
        ----------
        timeslot : Timeslot | int
            the timeslot or the index of the timeslot in the list of
            timeslots of the program

        Returns
        -------
        dict[Room, dict[int, Session]]
            the sessions organized by rooms (and zones)
        """
        sessions = dict()
        if isinstance(timeslot, Timeslot):
            timeslot_idx = self._timeslots.index(timeslot)  # NOTE: could be improved to be faster
        else:
            timeslot_idx = timeslot

        timeslot_content = self._program_matrix[timeslot_idx]
        for room_idx, room in enumerate(self._rooms):
            if timeslot_content[room_idx] is None:
                continue

            for zone_idx, session in enumerate(timeslot_content[room_idx]):
                if session is not None:
                    if room not in sessions:
                        sessions[room] = dict()
                    sessions[room][zone_idx] = session

        return sessions

    def get_session(self, timeslot: Timeslot | int, room: Room | int, zone: int | str = 0) -> Session:
        """Get the corresponding session taking place in a given zone of a given room at a given timeslot

        Parameters
        ----------
        timeslot : Timeslot | int
            The timeslot (or the index of the timeslot) of the session
        room : Room | int
            The room (or the index of the room) of the session
        zone : int | str
            The index or the name of the zone [default=0]

        Returns
        -------
        Session
            The session

        Raises
        ------
        Exception
            there is an inconsistency between the wanted zone and the
            wanted room
        """
        if isinstance(timeslot, int):
            timeslot_idx = timeslot
        else:
            timeslot_idx = self._timeslots.index(timeslot)

        if isinstance(room, int):
            room_idx = room
            room = self._rooms[room]
        else:
            room_idx = self._rooms.index(room)

        if isinstance(zone, int) and (zone >= room.nb_zones):
            raise Exception(f'There are not enough zones (nb_zones={room.nb_zones}) in the room as you asked for zone "{zone}"')
        elif isinstance(zone, str):
            zone_idx = room.zones.index(zone)
            if zone_idx == -1:
                raise Exception(f'The zone "{zone}" is not in the room {room}')
            zone = zone_idx

        return self._program_matrix[timeslot_idx, room_idx][zone]

    def add_session(
        self, timeslot: Timeslot | int, room: Room | int, session: Session, zone: int | str | None = None
    ) -> Session | None:
        """Add a session to the program

        The session is added at a given timeslot in a give room in a
        potential given zone

        Parameters
        ----------
        timeslot : Timeslot | int
            The timeslot (or the index of the timeslot) of the session
        room : Room | int
            The room (or the index of the room) of the session
        session : Session
            The session to add
        zone : int | str, optional
            The zone of the session (if None, append the session to the current room)

        Returns
        -------
        Session | None
            the session previously taking place at the same time in
            the same place, or None

        Raises
        ------
        Exception
            There is an issue with appending the session to the
            program (i.e., no available space) or there is an
            inconsistency between the zone and the room

        """
        if isinstance(timeslot, int):
            timeslot_idx = timeslot
        else:
            timeslot_idx = self._timeslots.index(timeslot)

        if isinstance(room, int):
            room_idx = room
            room = self._rooms[room]
        else:
            room_idx = self._rooms.index(room)

        #
        if self._program_matrix[timeslot_idx, room_idx] is None:
            self._program_matrix[timeslot_idx, room_idx] = []

        if zone is None:
            prev_session = None

            if len(self._program_matrix[timeslot_idx, room_idx]) >= room.nb_zones:
                raise Exception(f'All the slots of the room "{room}" are occupied, don\'t know where to add the session')

            allocated = False
            for i_zone in range(len(self._program_matrix[timeslot_idx, room_idx])):
                if self._program_matrix[timeslot_idx, room_idx][i_zone] is None:
                    self._program_matrix[timeslot_idx, room_idx][i_zone] = session
                    allocated = True
                    break

            if not allocated:
                self._program_matrix[timeslot_idx, room_idx].append(session)

        else:
            if isinstance(zone, str):
                zone_idx = room.zones.index(zone)
                if zone_idx == -1:
                    raise Exception(f'The zone "{zone}" is not in the room {room}')
                zone = zone_idx
            elif zone >= room.nb_zones:
                raise Exception("The room doesn't have any zones")

            if len(self._program_matrix[timeslot_idx, room_idx]) <= zone:
                prev_session = None
                for _ in range(len(self._program_matrix[timeslot_idx, room_idx]), zone):
                    self._program_matrix[timeslot_idx, room_idx].append(None)
                self._program_matrix[timeslot_idx, room_idx].append(session)
            else:
                prev_session = self._program_matrix[timeslot_idx, room_idx][zone]
                self._program_matrix[timeslot_idx, room_idx][zone] = session

        return prev_session

    def remove_session(self, timeslot: Timeslot, room: Room, zone: int | str | None = None) -> Session | None:
        """Remove a session from the program based on its timeslot and its location (***This method is not yet available***)

        Parameters
        ----------
        timeslot : Timeslot
            The timeslot of the session to remove
        room : Room
            The room of the session to remove
        zone : int | str, optional
            The zone of the session to remove

        Returns
        -------
        Session | None
            The removed session, None if no session was taking place
            at this specific time and place

        Raises (***This method is not yet available***)
        ------
        Exception
            There is an inconsistency between the room an the zone
        NotImplementedError
            This method is not yet available
        """

        raise NotImplementedError("Not yet available")
        if (room.nb_zones > 1) and (zone is None):
            raise Exception(f"The room {room} has multiple zones, please indicate in which one the session your to remove is")

        timeslot_idx = self._timeslots.index(timeslot)
        room_idx = self._rooms.index(room)
        slots = self._program_matrix[timeslot_idx, room_idx]

        self._program_matrix[timeslot_idx, room_idx] = None
        return slots

    def move_session(
        self,
        src_timeslot: Timeslot,
        src_room: Room,
        dest_timeslot: Timeslot,
        dest_room: Room,
        src_zone: int | str | None = None,
        dest_zone: int | str | None = None,
    ) -> PresentationSession | None:
        """Move the session in the program (***This method is not yet available***)

        Parameters
        ----------
        src_timeslot : Timeslot
            The timeslot of the session to move
        src_room : Room
            The room of the session to move
        dest_timeslot : Timeslot
            The timeslot where to move the session
        dest_room : Room
            The room where to move the session
        src_zone : int | str, optional
            The zone of the session to move (if None, assume only one
            zone in the room)
        dest_zone : int | str, optional
            The zone where to move the session (if None, assume only
            one zone in the room)

        Returns
        -------
        PresentationSession | None
            the session which was taking place where the session has
            been moved into

        Raises
        ------
        NotImplementedError
            This method is not yet available
        """
        raise NotImplementedError("not avilable yet")
        session = self.remove_session(src_timeslot, src_room)
        if session is None:
            return None
        self.add_session(dest_timeslot, dest_room, session)

    def select_sessions(
        self, criterion: Callable[[Session, Timeslot, Room, int], bool] | None
    ) -> list[tuple[Session, Timeslot, Room, int]]:
        """List all the sessions matching a given criterion

        Parameters
        ----------
        criterion : Callable[[Session, Timeslot, Room, int], bool], optional
            a function which encodes the criterion

        Returns
        -------
        list[tuple[Session, Timeslot, Room, int]]

            The list of sessions validating the criterion (a session is composed of the session  itself, the
            timeslot, the room and index of the zone of the session in
            the room)

        """
        if criterion is None:
            return self.sessions

        sessions = []
        for timeslot_idx, timeslot in enumerate(self._timeslots):
            timeslot_content = self._program_matrix[timeslot_idx]
            for room_idx, room in enumerate(self._rooms):
                if timeslot_content[room_idx] is not None:
                    for zone_idx, session in enumerate(timeslot_content[room_idx]):
                        if session is not None:
                            if criterion(session, timeslot, room, zone_idx):
                                sessions.append((session, timeslot, room, zone_idx))

        return sessions

    def get_information(self, wanted_presentation: Presentation) -> tuple[Timeslot, Room, int]:
        """Get the tima and place of a given presentation

        Parameters
        ----------
        wanted_presentation : Presentation
            The presentation we want the information for

        Returns
        -------
        tuple[Timeslot, Room, int]
            The information (the timeslot, the room and the zone
            index)

        Raises
        ------
        Exception
            The presentation is not part of the program
        """
        info = None
        for timeslot_idx, timeslot in enumerate(self._timeslots):
            timeslot_content = self._program_matrix[timeslot_idx]
            for room_idx, room in enumerate(self._rooms):
                if timeslot_content[room_idx] is not None:
                    for slots in timeslot_content[room_idx]:
                        for zone_idx in range(slots):
                            if not isinstance(slots[zone_idx], PresentationSession):
                                continue

                            for cur_presentation in slots[zone_idx].presentations:
                                if cur_presentation == wanted_presentation:
                                    info = (timeslot, room, zone_idx)
                                    break

                            if info is not None:
                                break

                        if info is not None:
                            break

                if info is not None:
                    break

            if info is not None:
                break

        if info is None:
            raise Exception(f"The following presentation is not part of the program: {repr(wanted_presentation)}")

        return info

    def authors2presentations(self) -> dict[Person, list[Presentation]]:
        """Get all the presentations of all the authors

        Returns
        -------
        dict[Person, list[Presentation]]
            The association of each author to all their presentations
        """
        authors2presentations = dict()
        sessions = self.sessions
        for session_info in sessions:
            session, _, _, _ = session_info
            if not isinstance(session, PresentationSession):
                continue

            for presentation in session.presentations:
                if presentation.presented_paper is None:
                    continue

                for author in presentation.presented_paper.authors:
                    if author not in authors2presentations:
                        authors2presentations[author] = list()
                    authors2presentations[author].append(presentation)
        return authors2presentations

    def __repr__(self):
        """Generate a string representation of the program

        Returns
        -------
        str
            The string representation of the program
        """
        return str(self._program_matrix)

    def __str__(self):
        """Generate a string representation of the program

        Returns
        -------
        str
            The string representation of the program
        """
        return str(self._program_matrix)
