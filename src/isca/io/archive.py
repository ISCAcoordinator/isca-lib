# Python
from datetime import datetime
import logging
import pathlib

# Data loading
import json

# Model helpers
from ..model.person import Person, Role
from ..model.paper import Paper, PublishedPaper
from ..model.session import Session, OralSession, PosterSession, Room
from ..model.event import Conference


###############################################################################
# Constants
###############################################################################
ARCHIVE_CHAIRS_PREFIX = "Chairs:"
ARCHIVE_CHAIRS_SEP = ", "

###############################################################################
# Core of the module
###############################################################################
class ArchiveSerialiser:
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

    def load(self, metadata_file: pathlib.Path, pdf_root_path: pathlib.Path | None = None) -> Conference:
        with open(metadata_file) as f_meta:
            metadata = json.load(f_meta)

        papers = dict()
        for paper_id, paper in metadata["papers"].items():
            authors = []
            for author in paper["authors"]:
                email = f'{".".join(author)}@none.org' # FIXME: email issue here!
                authors.append(Person(author[0], author[1], email, set([Role.AUTHOR])))

            cur_paper = PublishedPaper(
                paper_id,
                paper["title"],
                authors,
                paper["abstract"],
                None, # TODO: pdf is not yet supported
                paper["original_id"] if "original_id" in paper else None,
                paper["page_count"] if "page_count" in paper else None,
                paper["order"] if "order" in paper else None,
                paper["p1"] if "p1" in paper else None,
                paper["pn"] if "pn" in paper else None,
                paper["doi"] if "doi" in paper else None,
                paper["author_area_id"] if "author_area_id" in paper else None,
                paper["author_area_label"] if "author_area_label" in paper else None,
            )
            papers[paper_id] = cur_paper

        sessions = list()
        for session_idx, session in enumerate(metadata["sessions"]):
            papers_in_session = []
            for paper_id in session["papers"]:
                papers_in_session.append(papers[paper_id])
            cur_session = Session(
                str(session_idx),
                session["title"],
                papers_in_session
            )
            sessions.append(cur_session)

        # Load the conference
        start_date = datetime.strptime(metadata["startDate"], "%d/%m/%Y")
        end_date = datetime.strptime(metadata["endDate"], "%d/%m/%Y")

        chairs = []
        if "chair" in metadata:
            for chair in metadata["chair"].replace(ARCHIVE_CHAIRS_PREFIX, "").split(ARCHIVE_CHAIRS_SEP):
                chair = chair.strip()
                elts = chair.split(" ")
                first_name = " ".join(elts[:-1])
                last_name = elts[-1]
                email = f'{".".join(elts)}@none.org' # FIXME: email issue here!
                chairs.append(Person(first_name, last_name, email, set([Role.CHAIR])))

        conf = Conference(
            metadata_file.stem,
            metadata["title"],
            start_date,
            end_date,
            metadata["series"] if "series" in metadata else None,
            chairs
        )

        for session in sessions:
            conf.add_session(session)

        return conf

    def dump(self, conf: Conference, metadata_file: pathlib.Path, pdf_root_path: pathlib.Path | None = None):

        if len(conf.sessions) == 0:
            raise Exception("The conference should have sessions to be able to saved in the archive")

        chairs = []
        if conf.chairs is not None:
            for chair in conf.chairs:
                cur_chair = f"{chair.firstname} {chair.lastname}"
                chairs.append(cur_chair)
        # Initialise using conference info
        dict_out = {
            "title": conf.name,
            "startDate": conf.start_date.strftime("%d/%m/%Y"),
            "endDate": conf.end_date.strftime("%d/%m/%Y"),
        }
        if len(chairs) > 0:
            dict_out["chair"] = f"{ARCHIVE_CHAIRS_PREFIX} {ARCHIVE_CHAIRS_SEP.join(chairs)}"

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
                if isinstance(paper, PublishedPaper):
                    if paper.original_id is not None:
                        cur_paper["original_id"] = paper.original_id
                    if paper.page_count is not None:
                        cur_paper["page_count"] = paper.page_count
                    if paper.order is not None:
                        cur_paper["order"] = paper.order
                    if paper.start_page is not None:
                        cur_paper["p1"] = paper.start_page
                    if paper.end_page is not None:
                        cur_paper["pn"] = paper.end_page
                    if paper.doi is not None:
                        cur_paper["doi"] = paper.doi
                    if paper.author_area_id is not None:
                        cur_paper["author_area_id"] = paper.author_area_id
                    if paper.author_area_label is not None:
                        cur_paper["author_area_label"] = paper.author_area_label

                dict_out["papers"][paper.id] = cur_paper
            dict_out["sessions"].append(cur_session)


        with open(metadata_file, "w") as f_out:
            f_out.write(json.dumps(dict_out, indent=2))
