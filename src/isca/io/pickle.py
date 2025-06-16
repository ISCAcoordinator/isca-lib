# Python
import logging
import pathlib
import pickle

# Model helpers
from ..model.event import Conference

###############################################################################
# Core of the module
###############################################################################
class PickleSerialiser:
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

    def load_conference(self, input_file: pathlib.Path) -> Conference:
        with open(input_file, "rb") as f_structure:
            conf = pickle.load(f_structure)
        return conf

    def dump_conference(self, conf: Conference, input_file: pathlib.Path):
        with open(input_file, "wb") as f_structure:
            pickle.dump(conf, f_structure)
