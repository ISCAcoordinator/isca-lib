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
    def __init__(
        self,
        start: datetime.datetime,
        end: datetime.datetime,
    ):
        self.start: datetime.datetime = start
        self.end: datetime.datetime = end

    @property
    def date(self) -> datetime.date:
        return self.start.date()

    @property
    def duration(self) -> int:
        duration = self.end - self.start
        return duration.seconds // 60

    def __repr__(self) -> str:
        date = self.date.strftime("%Y-%m-%d")
        start = self.start.strftime("%H:%M")
        end = self.end.strftime("%H:%M")
        return f"AnonymousTimeslot(date={date}, start={start}, end={end})"

    def timeslot_without_date(self) -> str:
        start = self.start.strftime("%H:%M")
        end = self.end.strftime("%H:%M")
        return f"{start} -- {end}"

    def __str__(self) -> str:
        return repr(self)


class Timeslot(AnonymousTimeslot, ISCAItem):
    def __init__(
        self,
        id: str,
        name: str,
        type: TimeslotType,
        start: datetime.datetime,
        end: datetime.datetime,
    ):
        AnonymousTimeslot.__init__(self, start, end)
        ISCAItem.__init__(self, id)
        self.name: str = name
        self.type: TimeslotType = type

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Timeslot):
            return False

        return self.id == other.id

    def __repr__(self) -> str:
        date = self.date.strftime("%Y-%m-%d")
        start = self.start.strftime("%H:%M")
        end = self.end.strftime("%H:%M")
        return f"Timeslot(id={self.id}, name={self.name}, type={self.type}, date={date}, start={start}, end={end})"

    def __str__(self) -> str:
        return repr(self)


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
        talk_info = f"[{self.__class__.__name__} - {self.id}] {self.title}"
        if self.presenters is not None:
            talk_info += "\n"
            talk_info += "presenter(s): "
            presenters = []
            for presenter in self.presenters:
                presenters.append(str(presenter))
            talk_info += "; ".join(presenters)

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


#########################################################################################################
### Sessions
#########################################################################################################
class SocialSession(Session):
    def __init__(self, id: str, name: str):
        super().__init__(id, name)


class PresentationSession(ScientificSession):
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
        return self._presentations.copy()

    @property
    def papers(self) -> list[Paper]:
        papers = []
        for p in self._presentations:
            if p.presented_paper is not None:
                papers.append(p.presented_paper)
        return papers

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
        self._default_presentation_duration: int = default_presentation_duration

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

    def timeslot_presentation(self, presentation: Presentation | int) -> AnonymousTimeslot:
        return AnonymousTimeslot(self.start_presentation(presentation), self.end_presentation(presentation))

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


#########################################################################################################
### Program
#########################################################################################################


class Room(ISCAItem):
    def __init__(self, id: str, name: str, type: str, nb_zones: int | None = 1, zones: list[str] | None = None):
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
        return len(self._zones)

    @property
    def zones(self) -> list[str]:
        return self._zones.copy()

    def __str__(self) -> str:
        str = f"{self.name}"
        str += f" (zones={self.zones})"

        return str + f" [{self.type}]"

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Room):
            return False

        return self.id == other.id

    def __repr__(self) -> str:
        return f"Room(id={self.id}, name={self.name}, nb_zones={self.nb_zones})"


class Program(ISCAObject):
    def __init__(self, timeslots: list[Timeslot], rooms: list[Room]):
        super().__init__()
        self._timeslots: list[Timeslot] = sorted(timeslots, key=lambda x: x.start)
        self._rooms: list[Room] = rooms
        self._program_matrix: npt.NDArray[list[Session]] = np.full((len(self._timeslots), len(self._rooms)), None)

    @property
    def timeslots(self) -> list[Timeslot]:
        return copy.deepcopy(self._timeslots)

    @property
    def rooms(self) -> list[Room]:
        return copy.deepcopy(self._rooms)

    @property
    def sessions(self) -> list[tuple[Session, Timeslot, Room, int]]:
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
        if day is None:
            return self._timeslots

        timeslots = []
        for timeslot in self._timeslots:
            if timeslot.start.date() == day:
                timeslots.append(timeslot)

        return sorted(timeslots, key=lambda x: x.start)

    def get_day_sessions(self, day: datetime.date) -> list[tuple[Session, Timeslot, Room, int]]:
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
        raise NotImplementedError("not avilable yet")
        session = self.remove_session(src_timeslot, src_room)
        if session is None:
            return None
        self.add_session(dest_timeslot, dest_room, session)

    def select_sessions(
        self, criterion: Callable[[Session, Timeslot, Room, int], bool] | None
    ) -> list[tuple[Session, Timeslot, Room, int]]:
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

    def __str__(self):
        return str(self._program_matrix)
