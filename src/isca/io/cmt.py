# Python
from datetime import datetime
import traceback
import logging
import re
import pathlib

# Data loading
from ruamel.yaml import YAML
from openpyxl import load_workbook
import pandas as pd

# Model helpers
from ..model.person import Person, Affiliation, Role
from ..model.paper import Paper
from ..model.session import Session, OralSession, PosterSession, Room
from ..model.event import Conference

# IO Utils
from .utils.pdf import load_pdf_information, WordException, PDFMetadataException


###############################################################################
# Constants
###############################################################################
CMT_AUTHOR_SEP = "; "
CMT_FIRST_LAST_STEP = ", "
CMT_CORRESPONDING_MARKER = "*"

CMT_SESSION_TIMESLOTS_SHEET_NAME = "Timeslots"
CMT_SESSION_SESSIONS_SHEET_NAME = "Sessions"
CMT_SESSION_ROOMS_SHEET_NAME = "Rooms"
CMT_SESSION_PAPER_SEPARATOR = ","

CMT_CHAIR_CONF_SEPARATOR = ","

CMT_ROLE_SEP = ";"


###############################################################################
# Core of the module
###############################################################################
class CMTSerialiser:
    def __init__(self, with_camera_ready: bool = False, session_unplanned: bool = False):
        self._logger = logging.getLogger(self.__class__.__name__)
        self.with_camera_ready = with_camera_ready
        self.session_unplanned = session_unplanned
        if not with_camera_ready:
            self._logger.warning(
                "Metadata extracted from the CMT spreadsheet, likely to be highly inconsistent!",
            )

    def _extract_df_information(self, paper_info: pd.Series) -> Paper:
        author_names = str(paper_info["Author Names"]).split(CMT_AUTHOR_SEP)
        author_emails = str(paper_info["Author Emails"]).split(CMT_AUTHOR_SEP)

        # assert len(author_emails) == len(
        #     author_names
        # ), f"The number of authors ({len(author_names)}) does not match the number of emails ({len(author_emails)})"

        paper_authors = list()
        for i_author, cur_author in enumerate(author_names):
            cur_author = cur_author.replace(CMT_CORRESPONDING_MARKER, "").strip()

            # FIXME: check with martin how did he extract the first and last name
            cur_author = re.sub(" \(.*\)", "", cur_author)
            author_elts = cur_author.split(" ")
            last_name = author_elts[-1]
            first_name = " ".join(author_elts[:-1])
            # last_name, first_name = cur_author.split(CMT_FIRST_LAST_STEP)

            # FIXME: back to normal
            first_name = first_name.replace(CMT_CORRESPONDING_MARKER, "")
            if i_author < len(author_emails):
                email = author_emails[i_author].replace(CMT_CORRESPONDING_MARKER, "")
            else:
                email = f'{".".join(author_elts)}@none.org'

            cur_person = Person(first_name, last_name, email)
            paper_authors.append(cur_person)

        return Paper(
            str(paper_info["Paper Title"]),
            paper_authors,
            abstract=str(paper_info["Abstract"]),
            id=str(paper_info["Paper ID"]),
        )

    def load_user(self, user_spreadsheet_file: pathlib.Path) -> dict[str, Person]:
        dict_users = dict()
        wb = load_workbook(filename=user_spreadsheet_file)
        for worksheet in wb.sheetnames:
            df = pd.read_excel(user_spreadsheet_file, engine="openpyxl", sheet_name=worksheet)

            for _, user_row in df.iterrows():
                first_name = str(user_row["# First Name"]).strip()

                middle_initial = ""
                if not pd.isna(user_row["Middle Initial (optional)"]):
                    middle_initial = str(user_row["Middle Initial (optional)"]).strip()

                if pd.isna(user_row["Last Name"]) or (str(user_row["Last Name"]) == ""):
                    last_name = first_name.strip()
                    first_name = ""
                else:
                    last_name = str(user_row["Last Name"])

                affiliation = Affiliation(
                    institute=str(user_row["Organization"]).strip(),
                    country=str(user_row["Country"]).strip(),
                )
                roles = set()
                for r in str(user_row["Roles"]).split(CMT_ROLE_SEP):
                    if r == "Reviewer":
                        roles.add(Role.REVIEWER)
                    elif r == "Author":
                        roles.add(Role.AUTHOR)
                    elif r == "Meta-Reviewer":
                        roles.add(Role.META_REVIEWER)
                    elif r == "Senior Meta-Reviewer":
                        roles.add(Role.SENIOR_META_REVIEWER)
                    elif r == "Proceeding-Editor":
                        roles.add(Role.PROCEEDING_EDITOR)
                    elif r == "Chair":
                        roles.add(Role.CHAIR)
                    elif r == "Track Chair":
                        roles.add(Role.TRACK_CHAIR)
                    elif r == "Setting-Reader":
                        roles.add(Role.SETTING_READER)
                    elif r == "Not in CMT":
                        self._logger.debug(
                            f'User "{str(user_row["Email"]).strip()}" is not part of CMT users, inferred to be an author'
                        )
                        roles.add(Role.AUTHOR)
                    else:
                        raise Exception(f'The role ("{r}") is unknown')

                cur_user = Person(
                    first_name.strip(),
                    last_name.strip(),
                    email=str(user_row["Email"]).strip(),
                    roles=roles,
                    affiliations=set([affiliation]),
                    middle_initial=middle_initial,
                )

                dict_users[cur_user.id] = cur_user
        return dict_users

    def load_submissions(
        self,
        submission_summary_file: pathlib.Path,
        paper_root_dir: pathlib.Path | None = None,
        updated_paper_root_dir: pathlib.Path | None = None,
    ) -> tuple[dict[str, Paper], dict[str, Person]]:
        dict_authors = dict()
        dict_papers = dict()

        wb = load_workbook(filename=submission_summary_file)
        for worksheet in wb.sheetnames:
            df = pd.read_excel(submission_summary_file, engine="openpyxl", sheet_name=worksheet)
            total_papers = df.shape[0]
            failed_papers = 0
            word_papers = 0
            no_pdf = 0
            for _, paper_info in df.iterrows():
                if self.with_camera_ready:
                    try:
                        if paper_root_dir is not None:
                            paper_id = str(paper_info["Paper ID"])
                            pdf_path = paper_root_dir / f"{paper_id}.pdf"

                            if (updated_paper_root_dir is not None) and (
                                updated_paper_root_dir / f"{paper_id}.pdf"
                            ).exists():
                                self._logger.debug(
                                    f"[{paper_info['Paper ID']}] using the updated PDF",
                                    extra={
                                        "paper_id": paper_info["Paper ID"],
                                    },
                                )
                                pdf_path = updated_paper_root_dir / f"{paper_id}.pdf"

                            if pdf_path.exists():
                                cur_paper = load_pdf_information(
                                    str(paper_info["Paper ID"]), pdf_path, str(paper_info["Abstract"])
                                )
                                self._logger.debug(
                                    f"[{paper_info['Paper ID']}] Metadata extracted from the PDF {pdf_path}",
                                    extra={
                                        "paper_id": paper_info["Paper ID"],
                                        "metadata_from_pdf": True,
                                        "source": pdf_path
                                    }
                                )
                            else:
                                cur_paper = self._extract_df_information(paper_info)
                                self._logger.warning(
                                    f"[{paper_info['Paper ID']}] No PDF attached",
                                    extra={"paper_id": paper_info["Paper ID"]},
                                )
                                no_pdf += 1

                        else:
                            cur_paper = self._extract_df_information(paper_info)
                    except WordException:
                        cur_paper = self._extract_df_information(paper_info)
                        self._logger.warning(
                            f"[{paper_info['Paper ID']}] Can't extract the information from a PDF generated by word",
                            extra={
                                "paper_id": paper_info["Paper ID"],
                            },
                        )
                        word_papers += 1
                    except (PDFMetadataException, KeyError, IndexError) as ex:
                        self._logger.error(
                            f"[{paper_info['Paper ID']}] Extraction of the metadata from the PDF failed, falling back on the excel spreadsheet",
                            extra={
                                "paper_id": paper_info["Paper ID"],
                                "exception": ex,
                                "traceback": traceback.format_exc(),
                            },
                        )
                        cur_paper = self._extract_df_information(paper_info)
                        failed_papers += 1
                else:
                    cur_paper = self._extract_df_information(paper_info)

                dict_papers[cur_paper.id] = cur_paper
                for cur_author in cur_paper.authors:
                    dict_authors[cur_author.id] = cur_author

            self._logger.info(
                f"[{worksheet}] total number of submissions {total_papers}: "
                + f"failed_papers={failed_papers} ({failed_papers/total_papers*100:.2f}%), "
                + f"word_papers={word_papers} ({word_papers/total_papers*100:.2f}%), "
                + f"nopdf ={no_pdf} ({no_pdf/total_papers*100:.2f}%)"
            )
        return dict_papers, dict_authors

    def load_sessions(self, session_summary_file: pathlib.Path, dict_papers: dict[str, Paper] = {}) -> list[Session]:

        # Load rooms
        dict_room = dict()
        df = pd.read_excel(session_summary_file, engine="openpyxl", sheet_name=CMT_SESSION_ROOMS_SHEET_NAME)
        for _, room_info in df.iterrows():
            capacity = str(room_info["Capacity"]).strip()
            if (capacity == "") or (capacity == "nan"):
                capacity = None
            elif "-" in capacity:
                capacity = [int(c.strip()) for c in capacity.split("-")]
            else:
                capacity = int(capacity)

            room = Room(str(room_info["Room name"]), str(room_info["Room type"]), capacity)
            dict_room[room.name] = room

        # Now load timeslots
        dict_timeslots = dict()
        df = pd.read_excel(session_summary_file, engine="openpyxl", sheet_name=CMT_SESSION_TIMESLOTS_SHEET_NAME)
        df["Date"] = df["Date"].astype(str)
        for _, timeslot_info in df.iterrows():
            start_time = f"{timeslot_info['Date']} {timeslot_info['Start']}"
            start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            end_time = f"{timeslot_info['Date']} {timeslot_info['End']}"
            end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
            dict_timeslots[timeslot_info["Timeslot name"]] = [start_time, end_time]

        # And finally deal with sessions
        list_sessions = []
        df = pd.read_excel(session_summary_file, engine="openpyxl", sheet_name=CMT_SESSION_SESSIONS_SHEET_NAME)
        for _, session_info in df.iterrows():
            session_id = str(session_info["Session name"])
            session_name = str(session_info["Session title"])

            # Create the sessions
            if self.session_unplanned:
                cur_session = Session(session_id, session_name)
            else:
                # TODO: Get time from the time slots, now this is just a place holder
                cur_time_slot = dict_timeslots[session_info["Timeslot name"]]
                cur_room = dict_room[session_info["Room name"]]

                session_type = str(session_info["Session type"])
                if session_type.lower() == "oral":
                    cur_session = OralSession(session_id, session_name, cur_time_slot[0], cur_time_slot[1], cur_room)
                elif session_type.lower() == "poster":
                    cur_session = PosterSession(session_id, session_name, cur_time_slot[0], cur_time_slot[1], cur_room)
                else:
                    self._logger.error(f'This session type "{session_type}" is not yet supported (ignored)')
                    continue

            # Now deal add the papers
            session_paper_ids = [
                str(id).strip() for id in str(session_info["Papers"]).split(CMT_SESSION_PAPER_SEPARATOR)
            ]
            for paper_id in session_paper_ids:
                if paper_id not in dict_papers:
                    self._logger.error(f"{paper_id} is not an available papers, so ignored")
                    continue
                cur_session.add_paper(dict_papers[paper_id])
            list_sessions.append(cur_session)
        return list_sessions

    def load_conference(
        self,
        conference_info_file: pathlib.Path,
        sessions: dict[str, Session] | None = None,
        papers: dict[str, Paper] | None = None,
    ) -> Conference:

        if (sessions is not None) and (papers is not None):
            raise Exception(
                "Either the sessions OR the papers should be given. The papers will be loaded from the sessions. In case no sessions, the provide the papers."
            )

        conf_info = dict()
        yaml = YAML(typ="rt", pure=True)
        with open(conference_info_file) as f_in:
            conf_info = yaml.load(f_in.read())

        # NOTE: apparently autamtically converted into a date when loading the YAML configuration
        # # Convert the dates to datetime
        # conf_info["startDate"] = datetime.strptime(conf_info["startDate"], "%Y-%m-%d")
        # conf_info["endDate"] = datetime.strptime(conf_info["endDate"], "%Y-%m-%d")

        chairs = None
        if "chairs" in conf_info:
            chairs = []
            for chair in conf_info["chairs"].split(CMT_CHAIR_CONF_SEPARATOR):
                if "{" in chair:
                    raise NotImplementedError("Last name with spaces is not yet supported, but should be")
                else:
                    elts = chair.strip().split(" ")
                    first_name = " ".join(elts[:-1])
                    last_name = elts[-1]
                    chairs.append(
                        Person(first_name, last_name, "noemail@nodomain.org")
                    )  # FIXME: for now the email is slightly forced

        conf = Conference(
            conf_info["id"],
            conf_info["name"],
            conf_info["startDate"],
            conf_info["endDate"],
            conf_info["serie"] if "serie" in conf_info else None,
            chairs,
        )
        if sessions is not None:
            for _, session in sessions.items():
                conf.add_session(session)
        elif papers is not None:
            for _, paper in papers.items():
                conf.add_paper(paper)

        return conf
