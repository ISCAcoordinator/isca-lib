from enum import Enum
import copy
import datetime
import numpy as np

from .core import ISCAObject
from .item import ISCAItem, Paper, Session
from .person import Person


#########################################################################################################
### Presentation classes
#########################################################################################################
class Presentation(ISCAItem):
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
        return self._duration

    @property
    def presented_paper(self) -> Paper | None:
        return self._presented_paper

    def __str__(self):
        talk_info = f"[{self.__class__.__name__} - {self.id}] {self.title}\n"
        if self.presenters is not None:
            for presenter in self.presenters:
                talk_info += f"  - {presenter}\n"

        return talk_info


class OralPresentation(Presentation):
    def __init__(
        self,
        id: str,
        title: str,
        presenters: list[Person] | None,
        duration: int,
        abstract: str | None = None,
        presented_paper: Paper | None = None,
    ):
        super().__init__(id, title, presenters, duration, abstract, presented_paper)

    @property
    def duration(self) -> int:
        assert self._duration is not None
        return self._duration


class PosterPresentation(Presentation):
    def __init__(
        self,
        id: str,
        title: str,
        presenters: list[Person] | None,
        abstract: str | None = None,
        presented_paper: Paper | None = None,
    ):
        super().__init__(id, title, presenters, None, abstract, presented_paper)


class SurveyTalk(OralPresentation):
    def __init__(
        self,
        id: str,
        title: str,
        presenters: list[Person] | None,
        duration: int,
        abstract: str | None = None,
    ):
        super().__init__(id, title, presenters, duration, abstract, None)


class Keynote(OralPresentation):
    def __init__(
        self,
        id: str,
        title: str,
        presenters: list[Person] | None,
        duration: int,
        abstract: str | None = None,
    ):
        super().__init__(id, title, presenters, duration, abstract, None)


class SpecialPresentation(Presentation):
    def __init__(
        self,
        id: str,
        title: str,
        presenters: list[Person] | None,
        abstract: str | None = None,
        presented_paper: Paper | None = None,
    ):
        super().__init__(id, title, presenters, None, abstract, presented_paper)


class ShowAndTellPresentation(Presentation):
    def __init__(
        self,
        id: str,
        title: str,
        presenters: list[Person] | None,
        abstract: str | None = None,
        presented_paper: Paper | None = None,
    ):
        super().__init__(id, title, presenters, None, abstract, presented_paper)


class BlueSkyPresentation(OralPresentation):
    def __init__(
        self,
        id: str,
        title: str,
        presenters: list[Person] | None,
        duration: int,
        abstract: str | None = None,
        presented_paper: Paper | None = None,
    ):
        super().__init__(id, title, presenters, duration, abstract, presented_paper)


#########################################################################################################
### Sessions
#########################################################################################################


class PresentationSession(Session):
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
        self._presentations = presentations if presentations is not None else []
        self.chairs = chairs if chairs is not None else []

        # For now, start/end can't be modified to avoid side effects!
        self._start = start
        self._end = end

    @property
    def start(self) -> datetime.datetime:
        return self._start

    @property
    def end(self) -> datetime.datetime:
        return self._end

    @property
    def presentations(self) -> list[Presentation]:
        return self._presentations.copy()

    def add_presentation(self, presentation: Presentation):
        self._presentations.append(presentation)

    def is_in_session(self, presentation: Presentation) -> bool:
        return presentation in self._presentations

    def remove_presentation(self, presentation: Presentation):
        if self.is_in_session(presentation):
            self._presentations.remove(presentation)

    def replace_presentation(self, presentation_out: Presentation, presentation_in: Presentation):
        idx = self._presentations.index(presentation_out)
        if idx < 0:
            raise ValueError(f'"{presentation_out.id}" is not part of the session, so it can\'t be replaced')
        self._presentations[idx] = presentation_in

    def start_presentation(self, _: Presentation | int) -> datetime.datetime:
        return self.start

    def end_presentation(self, _: Presentation | int) -> datetime.datetime:
        return self.end

    def sort_criterion(self) -> str:
        return "_".join([str(s) for s in (self.start, self._end, self.id, self.name)])


class OralSession(PresentationSession):
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
        super().__init__(id, name, start, end, presentations, chairs)
        self._default_presentation_duration = default_presentation_duration

    def add_presentation(self, presentation: Presentation):
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
        start = self.start

        if isinstance(presentation, int):
            assert presentation < len(
                self.presentations
            ), f"[{self.id}] There are not enough presentation in the session ({len(self.presentations)} < {presentation})"

            for pres_idx, cur_presentation in enumerate(self.presentations):
                if pres_idx >= presentation:
                    break

                start += datetime.timedelta(minutes=cur_presentation.duration)
        elif isinstance(presentation, Presentation):
            for cur_presentation in self.presentations:
                if presentation == cur_presentation:
                    break

                start += datetime.timedelta(minutes=cur_presentation.duration)

        return start

    def end_presentation(self, presentation: Presentation | int) -> datetime.datetime:
        if isinstance(presentation, int):
            presentation = self.presentations[presentation]

        return self.start_presentation(presentation) + datetime.timedelta(minutes=presentation.duration)

    @property
    def default_duration(self) -> int:
        return self._default_presentation_duration


class KeynoteSession(OralSession):
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
        super().__init__(id, name, start, end, presentations, chairs, default_presentation_duration)


class PosterSession(PresentationSession):
    def __init__(
        self,
        id: str,
        name: str,
        start: datetime.datetime,
        end: datetime.datetime,
        presentations: list[Presentation] | None = None,
        chairs: list[Person] | None = None,
    ):
        super().__init__(id, name, start, end, presentations, chairs)


class SpecialSession(PresentationSession):
    def __init__(
        self,
        id: str,
        name: str,
        start: datetime.datetime,
        end: datetime.datetime,
        presentations: list[Presentation] | None = None,
        chairs: list[Person] | None = None,
    ):
        super().__init__(id, name, start, end, presentations, chairs)


class ShowAndTellSession(PresentationSession):
    def __init__(
        self,
        id: str,
        name: str,
        start: datetime.datetime,
        end: datetime.datetime,
        presentations: list[Presentation] | None = None,
        chairs: list[Person] | None = None,
    ):
        super().__init__(id, name, start, end, presentations, chairs)


#########################################################################################################
### Program
#########################################################################################################


class TimeslotType(Enum):
    CEREMONY = 0
    KEYNOTE = 1
    COFFEE_BREAK = 2
    LUNCH_BREAK = 3
    ASSEMBLY = 4
    SCIENCE = 5

    def __str__(self) -> str:
        """Return the string representation of the role

        Returns
        -------
        str
            the (uppercase) name of the role
        """
        return f'{self.name.replace("TimeslotType.", "")}'


class Timeslot(ISCAItem):
    def __init__(
        self,
        id: str,
        name: str,
        type: TimeslotType,
        start: datetime.datetime,
        end: datetime.datetime,
    ):
        super().__init__(id)
        self.name: str = name
        self.type: TimeslotType = type
        self.start: datetime.datetime = start
        self.end: datetime.datetime = end

    @property
    def date(self) -> datetime.date:
        return self.start.date()

    def __repr__(self) -> str:
        date = self.date.strftime("%Y-%m-%d")
        start = self.start.strftime("%H:%M")
        end = self.end.strftime("%H:%M")
        return f"Timeslot(id={self.id}, name={self.name}, type={self.type}, date={date}, start={start}, end={end})"

    def timeslot_without_date(self) -> str:
        start = self.start.strftime("%H:%M")
        end = self.end.strftime("%H:%M")
        return f"{start} -- {end}"

    def __str__(self) -> str:
        return repr(self)


class Room(ISCAItem):
    def __init__(self, id: str, name: str, type: str, nb_zones: int = 1):
        super().__init__(id)
        self.name: str = name
        self.type: str = type
        self._nb_zones: int = nb_zones

    @property
    def nb_zones(self) -> int:
        return self._nb_zones

    def __str__(self) -> str:
        str = f"{self.name}"
        if self.nb_zones is not None:
            str += f" (nb_zones={self._nb_zones})"

        return str + f" [{self.type}]"

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Room):
            return False

        return self.id == other.id


class Program(ISCAObject):
    def __init__(self, timeslots: list[Timeslot], rooms: list[Room]):
        super().__init__()
        self._timeslots = sorted(timeslots, key=lambda x: x.start)
        self._rooms = rooms
        self._program_matrix = np.full((len(self._timeslots), len(self._rooms)), None)

    def get_timeslots(self, day: datetime.date | None = None) -> list[Timeslot]:
        if day is None:
            return self._timeslots

        timeslots = []
        for timeslot in self._timeslots:
            if timeslot.start.date() == day:
                timeslots.append(timeslot)

        return sorted(timeslots, key=lambda x: x.start)

    def get_day_sessions(self, day: datetime.date) -> list[tuple[PresentationSession, Timeslot, Room]]:
        sessions = []
        timeslots = self.get_timeslots(day)
        for timeslot in timeslots:
            timeslot_idx = self._timeslots.index(timeslot)  # NOTE: could be improved to be faster
            timeslot_content = self._program_matrix[timeslot_idx]
            for room_idx, room in enumerate(self._rooms):
                if timeslot_content[room_idx] is not None:
                    for session in timeslot_content[room_idx]:
                        sessions.append((session, timeslot, room))

        return sorted(sessions, key=lambda x: x[0].start)

    def get_timeslot_sessions(self, timeslot: Timeslot | int) -> dict[Room, list[PresentationSession]]:
        sessions = dict()
        if isinstance(timeslot, Timeslot):
            timeslot_idx = self._timeslots.index(timeslot)  # NOTE: could be improved to be faster
        else:
            timeslot_idx = timeslot

        timeslot_content = self._program_matrix[timeslot_idx]
        for room_idx, room in enumerate(self._rooms):
            if timeslot_content[room_idx] is not None:
                sessions[room] = timeslot_content[room_idx]

        return sessions

    def get_session(self, timeslot: Timeslot | int, room: Room | int, zone_idx: int = 0):
        if isinstance(timeslot, int):
            timeslot_idx = timeslot
        else:
            timeslot_idx = self._timeslots.index(timeslot)

        if isinstance(room, int):
            room_idx = room
            room = self._rooms[room]
        else:
            room_idx = self._rooms.index(room)

        if zone_idx >= room.nb_zones:
            raise Exception(
                f'There are not enough zones (nb_zones={room.nb_zones}) in the room as you asked for zone "{zone_idx}"'
            )

        return self._program_matrix[timeslot_idx, room_idx][zone_idx]

    def add_session(self, timeslot: Timeslot | int, room: Room | int, session: PresentationSession) -> PresentationSession | None:
        if isinstance(timeslot, int):
            timeslot_idx = timeslot
        else:
            timeslot_idx = self._timeslots.index(timeslot)

        if isinstance(room, int):
            room_idx = room
            room = self._rooms[room]
        else:
            room_idx = self._rooms.index(room)

        cur_session = [session]
        prev_sessions = self._program_matrix[timeslot_idx, room_idx]
        if prev_sessions is not None:
            if len(prev_sessions) >= room.nb_zones:
                raise Exception(
                    f"There is already a session for the timeslot {timeslot} in the room {room} and replace was not forced. Here is the session: {prev_sessions}"
                )
            else:
                cur_session = prev_sessions.copy()
                cur_session.append(session)

        self._program_matrix[timeslot_idx, room_idx] = cur_session
        return prev_sessions

    def remove_session(self, timeslot: Timeslot, room: Room) -> PresentationSession | None:
        timeslot_idx = self._timeslots.index(timeslot)
        room_idx = self._rooms.index(room)

        session = self._program_matrix[timeslot_idx, room_idx]
        self._program_matrix[timeslot_idx, room_idx] = None
        return session

    def move_session(
        self, src_timeslot: Timeslot, src_room: Room, dest_timeslot: Timeslot, dest_room: Room
    ) -> PresentationSession | None:
        session = self.remove_session(src_timeslot, src_room)
        if session is None:
            return None
        self.add_session(dest_timeslot, dest_room, session)

    @property
    def timeslots(self) -> list[Timeslot]:
        return copy.deepcopy(self._timeslots)

    @property
    def rooms(self) -> list[Room]:
        return copy.deepcopy(self._rooms)

    @property
    def sessions(self) -> list[tuple[Timeslot, Room, PresentationSession]]:
        sessions = []
        for timeslot_idx, timeslot in enumerate(self._timeslots):

            timeslot_content = self._program_matrix[timeslot_idx]
            for room_idx, room in enumerate(self._rooms):
                if timeslot_content[room_idx] is not None:
                    for session in timeslot_content[room_idx]:
                        sessions.append((timeslot, room, session))

        return sessions

    def authors2presentations(self) -> dict[Person, list[Presentation]]:
        authors2presentations = dict()
        sessions = self.sessions
        for session_info in sessions:
            _, _, session = session_info
            for presentation in session.presentations:
                if presentation.presented_paper is None:
                    continue

                for author in presentation.presented_paper.authors:
                    if author not in authors2presentations:
                        authors2presentations[author] = list()
                    authors2presentations[author].append(presentation)
        return authors2presentations

    def __str__(self):
        return str(self._program_matrix)
