"""This module provides the core elements used by any other code pieces of the ISCA library
"""

from abc import ABC
import logging


class ISCAObject(ABC):
    """Default ISCA object (abstract class)

    An ISCA object is the baseline for any ISCA specific classes.
    Its goal is to ensure a common debugging management.

    For now, it mainly consists of instanciating a logger of the class name
    """

    def __init__(self):
        """Initialise the ISCA object by creating its logger"""

        super().__init__()
        self._logger = logging.getLogger(self.__class__.__name__)

    @property
    def logger(self) -> logging.Logger:
        """Get the logger associated to the ISCA object

        Returns
        -------
        logging.Logger
            the logger
        """

        return self._logger


class ISCAItem(ISCAObject, ABC):
    """ISCA Item (abstract class)


    It implies that an ISCA item can be serialized
    """

    def __init__(self, id: str):
        """Initialise the ISCA item by providing its identifier

        Parameters
        ----------
        id : str
            the identifier of the item
        """

        super().__init__()
        # super(ABC, self).__init__()
        # super(ISCAObject, self).__init__()
        self._id = id

    @property
    def id(self) -> str:
        """Get the identifier of the item

        Returns
        -------
        str
            the identifier of the item
        """

        return self._id
