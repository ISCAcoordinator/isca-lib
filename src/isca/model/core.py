import logging


class ISCAObject:
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

    @property
    def logger(self) -> logging.Logger:
        return self._logger


class ISCAItem(ISCAObject):
    def __init__(self, id: str):
        super().__init__()
        self._id = id

    @property
    def id(self) -> str:
        return self._id
