# Python
import logging
import pathlib

# Data loading
import json

# Model helpers
from ..model.person import Person
from ..model.paper import Paper
from ..model.session import Session, OralSession, PosterSession, Room
from ..model.event import Conference


###############################################################################
# Core of the module
###############################################################################
class ArchiveSerialiser:
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

    def load(self, metadata_file: pathlib.Path, pdf_root_path: pathlib.Path | None = None):
        pass

    def dump(self, conf: Conference, metadata_file: pathlib.Path, pdf_root_path: pathlib.Path | None = None):

        if len(conf.sessions) == 0:
            raise Exception("The conference should have sessions to be able to saved in the archive")

        # Initialise using conference info
        dict_out = {
            "title": conf.name,
            "startDate": conf.start_date.strftime("%d/%m/%Y"),
            "endDate": conf.end_date.strftime("%d/%m/%Y"),
        }

        if conf.serie is not None:
            dict_out["series"] = conf.serie

        # Conference part
        dict_out["papers"] = {}
        dict_out["sessions"] = []
        for session in conf.sessions:
            cur_session = {}
            cur_session["title"] = session.name
            cur_session["papers"] = []
            for paper in session.papers:
                cur_session["papers"].append(paper.id)
                authors = []
                for author in paper.authors:
                    authors.append([author.firstname, author.lastname])
                cur_paper = {
                    "authors": authors,
                    "title": paper.title,
                    "abstract": paper.abstract
                }
                dict_out["papers"][paper.id] = cur_paper
            dict_out["sessions"].append(cur_session)


        with open(metadata_file, "w") as f_out:
            f_out.write(json.dumps(dict_out, indent=2))
