import datetime

from .core import ISCAItem
from .person import Person
from .item import Paper, Presentation


class Room(ISCAItem):
    def __init__(self, name: str, type: str, capacity: int | tuple[int] | list[int] | None):
        super().__init__(name)
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
        expected_duration = self._default_presentation_duration * (len(self.presentations) + 1)
        total_duration = (self.end - self.start).seconds / 60

        if expected_duration > total_duration:
            raise Exception(
                f'When adding the presentation to session "{self.id}", the total duration would become {expected_duration} minutes but the assigned duration is {total_duration} minutes.'
            )
        super().add_presentation(presentation)

    def start_presentation(self, presentation: Presentation | int) -> datetime.datetime:
        if isinstance(presentation, Presentation):
            presentation_idx = self.presentations.index(presentation)
            if presentation_idx < 0:
                raise IndexError(f"{presentation} is not available in the current session")
            presentation = presentation_idx

        offset = presentation * self._default_presentation_duration
        return self.start + datetime.timedelta(minutes=offset)

    def end_presentation(self, presentation: Presentation | int) -> datetime.datetime:
        return self.start_presentation(presentation) + datetime.timedelta(minutes=self._default_presentation_duration)

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
