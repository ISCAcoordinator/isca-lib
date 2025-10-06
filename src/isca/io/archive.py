# Python
from typing import Any
from datetime import datetime
import logging
import pathlib
import re
import shutil

# Data loading
import json
from isca.model.core import ISCAObject
from isca.model.program import KeynoteSession, PresentationSession
import pandas as pd

# Model helpers
from ..model.person import Person, Role
from ..model.item import Paper, PublishedPaper, ScientificSession
from ..model.event import Conference


###############################################################################
# Constants
###############################################################################
ARCHIVE_CHAIRS_PREFIX = "Chairs:"
ARCHIVE_CHAIRS_SEP = ", "
ARCHIVE_CONF_SEPARATOR = "="
ARCHIVE_INPUT_DATA_SEP = "|"
ARCHIVE_INPUT_DATA_AUTHOR_SEP = ", "
ARCHIVE_INPUT_DATA_PAPER_SEP = ", "
ARCHIVE_INPUT_AUTHOR_REGEXP = re.compile("([^{]*) {([^}]*)}")


###############################################################################
# Core of the module
###############################################################################
class PublishedArchiveSerialiser(ISCAObject):
    def load(self, metadata_file: pathlib.Path, pdf_root_path: pathlib.Path | None = None) -> Conference:
        with open(metadata_file) as f_meta:
            metadata = json.load(f_meta)

        papers = dict()
        for paper_id, paper in metadata["papers"].items():
            authors = []
            for author in paper["authors"]:
                email = f'{".".join(author)}@none.org'  # FIXME: email issue here!
                authors.append(Person(author[0], author[1], email, set([Role.AUTHOR])))

            cur_paper = PublishedPaper(
                paper_id,
                paper["title"],
                authors,
                paper["abstract"],
                None,  # TODO: pdf is not yet supported
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
            cur_session = ScientificSession(str(session_idx), session["title"], papers_in_session)
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
                email = f'{".".join(elts)}@none.org'  # FIXME: email issue here!
                chairs.append(Person(first_name, last_name, email, set([Role.CHAIR])))

        conf = Conference(
            metadata_file.stem,
            metadata["title"],
            start_date,
            end_date,
            metadata["location"] if "location" in metadata else None,
            metadata["URL"] if "URL" in metadata else None,
            metadata["series"] if "series" in metadata else None,
            chairs,
            metadata["ISSN"] if "ISSN" in metadata else None,
            True if ("generateDOIs" in metadata) and (metadata["generateDOIs"].lower() == "yes") else False,
        )

        for session in sessions:
            conf.add_session(session)

        return conf

    def dump(self, conf: Conference, metadata_file: pathlib.Path, pdf_root_path: pathlib.Path | None = None):

        if len(conf.sessions) == 0:
            raise Exception("The conference should have sessions to be able to saved in the archive")

        # Fill conference meta information
        dict_out: dict[str, Any] = {
            "title": conf.name,
            "startDate": conf.start_date.strftime("%d/%m/%Y"),
            "endDate": conf.end_date.strftime("%d/%m/%Y"),
        }
        if conf.url is not None:
            dict_out["URL"] = conf.url
        if conf.location is not None:
            dict_out["location"] = conf.location
        if conf.generate_doi:
            dict_out["generateDOIs"] = "yes"
        if conf.issn is not None:
            dict_out["ISSN"] = conf.issn

        if conf.chairs is not None:
            chairs = []
            for chair in conf.chairs:
                cur_chair = f"{chair.firstname} {chair.lastname}"
                chairs.append(cur_chair)
            dict_out["chair"] = f"{ARCHIVE_CHAIRS_PREFIX} {ARCHIVE_CHAIRS_SEP.join(chairs)}"

        if conf.serie is not None:
            dict_out["series"] = conf.serie

        # Add conference content
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
                cur_paper = {"authors": authors, "title": paper.title, "abstract": paper.abstract}
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

        # Finally dump
        with open(metadata_file, "w") as f_out:
            f_out.write(json.dumps(dict_out, indent=2))


class ArchiveInputSerialiser(ISCAObject):
    def load(self, metadata_conf_file: pathlib.Path) -> Conference:
        # Load papers
        papers_metadata = pd.read_csv(metadata_conf_file.parent / "papers.txt", sep=ARCHIVE_INPUT_DATA_SEP)
        papers = dict()
        for _, paper in papers_metadata.iterrows():
            authors = []
            for author in paper.authors.split(ARCHIVE_INPUT_DATA_AUTHOR_SEP):
                author = author.strip()
                m = ARCHIVE_INPUT_AUTHOR_REGEXP.match(author)
                if m:
                    first_name = m.group(1)
                    last_name = m.group(2)
                else:
                    author_elts = author.split(" ")
                    first_name = " ".join(author_elts[:-1])
                    last_name = author_elts[-1]

                authors.append(Person(first_name, last_name, None, set([Role.AUTHOR])))

            abstract = ""
            with open(metadata_conf_file.parent / f"abstracts/{paper.id}.txt") as f_abstract:
                abstract = str(f_abstract.read()).strip()

            cur_paper = Paper(
                paper.title,
                authors,
                abstract,
                (metadata_conf_file.parent / f"pdfs/{paper.id}.pdf").resolve(),
                id=paper.id,
            )
            papers[paper.id] = cur_paper

        # Load sessions
        sessions_metadata = pd.read_csv(metadata_conf_file.parent / "sessions.txt", sep=ARCHIVE_INPUT_DATA_SEP)
        sessions = list()
        for session_idx, session in sessions_metadata.iterrows():
            papers_in_session = []
            for paper_id in session.papers.split(ARCHIVE_INPUT_DATA_PAPER_SEP):
                papers_in_session.append(papers[paper_id])
            cur_session = ScientificSession(str(session_idx), session.title, papers_in_session)
            sessions.append(cur_session)

        # Load the conference
        metadata_conf = dict()
        with open(metadata_conf_file) as f_conf:
            for l in f_conf.readlines():
                elts = [e.strip() for e in l.split(ARCHIVE_CONF_SEPARATOR)]
                metadata_conf[elts[0]] = elts[1]

        start_date = datetime.strptime(metadata_conf["startDate"], "%d/%m/%Y")
        end_date = datetime.strptime(metadata_conf["endDate"], "%d/%m/%Y")

        chairs = []
        if "chair" in metadata_conf:
            for chair in metadata_conf["chair"].replace(ARCHIVE_CHAIRS_PREFIX, "").split(ARCHIVE_CHAIRS_SEP):
                chair = chair.strip()
                elts = chair.split(" ")
                first_name = " ".join(elts[:-1])
                last_name = elts[-1]
                chairs.append(Person(first_name, last_name, None, set([Role.CHAIR])))

        conf = Conference(
            metadata_conf_file.stem,
            metadata_conf["title"],
            start_date,
            end_date,
            metadata_conf["location"] if "location" in metadata_conf else None,
            metadata_conf["URL"] if "URL" in metadata_conf else None,
            metadata_conf["series"] if "series" in metadata_conf else None,
            chairs,
            metadata_conf["ISSN"] if "ISSN" in metadata_conf else None,
            True if ("generateDOIs" in metadata_conf) and (metadata_conf["generateDOIs"].lower() == "yes") else False,
        )

        for session in sessions:
            conf.add_session(session)

        return conf

    def dump(self, conf: Conference, output_dir: pathlib.Path, booklet_path: pathlib.Path | None = None):
        # Prepare directory
        abstracts_dir = output_dir / "abstracts"
        abstracts_dir.mkdir(exist_ok=True, parents=True)
        pdfs_dir = output_dir / "pdfs"
        pdfs_dir.mkdir(exist_ok=True, parents=True)

        # Create session file
        seen_papers = []
        keynotes = []
        with open(output_dir / "sessions.txt", "w") as f_sessions:
            f_sessions.write(ARCHIVE_INPUT_DATA_SEP.join(["title", "papers"]))
            f_sessions.write("\n")

            for session in conf.sessions:
                if isinstance(session, ScientificSession) and session.papers:
                    session_papers = []
                    for paper in session.papers:
                        session_papers.append(str(paper.id))
                    seen_papers += session_papers
                    papers = ARCHIVE_INPUT_DATA_PAPER_SEP.join(session_papers)
                    f_sessions.write(ARCHIVE_INPUT_DATA_SEP.join([session.name, papers]))
                    f_sessions.write("\n")
                elif isinstance(session, KeynoteSession):
                    presentations = []
                    for keynote_presentation in session.presentations:
                        presentations.append(str(keynote_presentation.id))
                        keynotes.append(keynote_presentation)
                    presentations = ARCHIVE_INPUT_DATA_PAPER_SEP.join(presentations)
                    f_sessions.write(ARCHIVE_INPUT_DATA_SEP.join([str(session.id) + " - " + session.name, presentations]))
                    f_sessions.write("\n")

        # Create paper file
        with open(output_dir / "papers.txt", "w") as f_papers:
            f_papers.write(ARCHIVE_INPUT_DATA_SEP.join(["id", "title", "authors"]))
            f_papers.write("\n")

            for paper_id, paper in conf.papers.items():

                if str(paper_id) not in seen_papers:
                    self.logger.warning(f'The paper "{paper_id}" is not part of any sessions, check if it has been withdrawn')
                    continue

                list_authors = []
                for author in paper.authors:

                    cur_author = ""
                    if author.firstname:
                        cur_author += author.firstname + " "

                    if author.middle_initial:
                        cur_author += author.middle_initial + " "

                    cur_author += f"{{{author.lastname}}}"
                    list_authors.append(cur_author)

                authors = ARCHIVE_INPUT_DATA_AUTHOR_SEP.join(list_authors)
                f_papers.write(ARCHIVE_INPUT_DATA_SEP.join([str(paper_id), paper.title, authors]))
                f_papers.write("\n")

                # Save abstract
                if paper.abstract is None:
                    raise Exception(f"{paper_id} doesn't have any abstract, this is incompatible with the ISCA archive")

                with open(abstracts_dir / f"{paper_id}.txt", "w") as f_abstract:
                    f_abstract.write(paper.abstract)

                # Save PDF
                if paper.pdf_file is not None:
                    shutil.copy(paper.pdf_file.resolve(), pdfs_dir / f"{paper_id}.pdf")

            for keynote in keynotes:
                presenter_names = []
                for presenter in keynote.presenters:

                    cur_presenter = ""
                    if presenter.firstname:
                        cur_presenter += presenter.firstname + " "

                    if presenter.middle_initial:
                        cur_presenter += presenter.middle_initial + " "

                    cur_presenter += f"{{{presenter.lastname}}}"
                    presenter_names.append(cur_presenter)

                presenters = ARCHIVE_INPUT_DATA_PAPER_SEP.join(presenter_names)
                f_papers.write(ARCHIVE_INPUT_DATA_SEP.join([str(keynote.id), keynote.title, presenters]))
                f_papers.write("\n")

                # Save abstract
                if keynote.abstract is None:
                    raise Exception(f"{keynote.id} doesn't have any abstract, this is incompatible with the ISCA archive")

                with open(abstracts_dir / f"{keynote.id}.txt", "w") as f_abstract:
                    abstract_content = "<h4>Abstract</h4>\n"
                    abstract_content += f"<p>\n{keynote.abstract}</p>\n"
                    abstract_content += "<h4>Biography</h4>\n"

                    abstract_content += "<p>\n"
                    abstract_content += "</p>\n<p>\n".join([p.biography for p in keynote.presenters])
                    abstract_content += "</p>\n"
                    f_abstract.write(abstract_content)

        # Initialise using conference info
        dict_out = {
            "title": conf.name,
            "startDate": conf.start_date.strftime("%d/%m/%Y"),
            "endDate": conf.end_date.strftime("%d/%m/%Y"),
        }
        if conf.url is not None:
            dict_out["URL"] = conf.url
        if conf.location is not None:
            dict_out["location"] = conf.location
        if conf.generate_doi:
            dict_out["generateDOIs"] = "yes"
        if conf.issn is not None:
            dict_out["ISSN"] = conf.issn

        if conf.chairs is not None:
            chairs = []
            for chair in conf.chairs:
                cur_chair = f"{chair.firstname} {chair.lastname}"
                chairs.append(cur_chair)
            dict_out["chair"] = f"{ARCHIVE_CHAIRS_PREFIX} {ARCHIVE_CHAIRS_SEP.join(chairs)}"

        if conf.serie is not None:
            dict_out["series"] = conf.serie

        if (booklet_path is not None) and booklet_path.is_file():
            shutil.copy(booklet_path.resolve(), output_dir / "booklet.pdf")
            dict_out["intro"] = "./booklet.pdf"

        with open(output_dir / "conference.txt", "w") as f_conf:
            for k, v in dict_out.items():
                f_conf.write(f" {ARCHIVE_CONF_SEPARATOR} ".join([k, v]))
                f_conf.write("\n")
