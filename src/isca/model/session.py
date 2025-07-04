from enum import Enum
import datetime

from .core import ISCAItem
from .person import Person
from .item import Presentation, PosterPresentation, OralPresentation


class Room(ISCAItem):
    def __init__(self, id: str, name: str, type: str, capacity: int | tuple[int] | list[int] | None):
        super().__init__(id)
        self.name: str = name
        self.type: str = type
        self.capacity: int | tuple[int] | list[int] | None = capacity

    def __str__(self) -> str:
        str = f"{self.name}"
        if self.capacity is not None:
            str += f" (capacity={self.capacity})"

        return str + f" [{self.type}]"

class Session(ISCAItem):
    def __init__(
        self,
        id: str,
        name: str,
        presentations: list[Presentation] | None = None,
    ):
        super().__init__(id)
        self.name = name
        self._presentations = presentations if presentations is not None else []

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
        presentations: list[Presentation] | None = None,
        chairs: list[Person] | None = None,
    ):
        super().__init__(id, name, presentations)
        self.chairs = chairs if chairs is not None else []
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

    def start_presentation(self, presentation: Presentation | int) -> datetime.datetime:
        return self.start

    def end_presentation(self, presentation: Presentation | int) -> datetime.datetime:
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
        room: Room | None = None,
        presentations: list[Presentation] | None = None,
        chairs: list[Person] | None = None,
        default_presentation_duration: int = 20,
    ):
        super().__init__(id, name, start, end, room, presentations, chairs)
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
        room: Room | None = None,
        presentations: list[Presentation] | None = None,
        chairs: list[Person] | None = None,
        default_presentation_duration: int = 60,
    ):
        super().__init__(id, name, start, end, room, presentations, chairs, default_presentation_duration)


class PosterSession(PresentationSession):
    def __init__(
        self,
        id: str,
        name: str,
        start: datetime.datetime,
        end: datetime.datetime,
        room: Room | None = None,
        presentations: list[Presentation] | None = None,
        chairs: list[Person] | None = None,
    ):
        super().__init__(id, name, start, end, room, presentations, chairs)

class SpecialSession(PresentationSession):
    def __init__(
        self,
        id: str,
        name: str,
        start: datetime.datetime,
        end: datetime.datetime,
        room: Room | None = None,
        presentations: list[Presentation] | None = None,
        chairs: list[Person] | None = None,
    ):
        super().__init__(id, name, start, end, room, presentations, chairs)

class ShowAndTellSession(PresentationSession):
    def __init__(
        self,
        id: str,
        name: str,
        start: datetime.datetime,
        end: datetime.datetime,
        room: Room | None = None,
        presentations: list[Presentation] | None = None,
        chairs: list[Person] | None = None,
    ):
        super().__init__(id, name, start, end, room, presentations, chairs)


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
        sessions: list[PresentationSession] | None = None
    ):
        super().__init__(id)
        self.name: str = name
        self.type: TimeslotType = type
        self.start: datetime.datetime = start
        self.end: datetime.datetime = end
        self.sessions: list[PresentationSession] | None = sessions

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

    def add_session(self, session: PresentationSession):
        if self.sessions is None:
            self.sessions = list()
        self.sessions.append(session)

    def get_session_in_room(self, room: Room) -> PresentationSession | None:
        wanted_session = None
        if self.sessions is not None:
            for session in self.sessions:
                if session.room == room:
                    wanted_session = session
                    break

        return wanted_session

    def __str__(self) -> str:
        return repr(self)
