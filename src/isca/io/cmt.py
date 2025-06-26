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
CMT_AFFILIATION_SEPARATOR = "; "

CMT_AUTHOR_REGEXP = re.compile(r"^([^(]*) \((.*)\)")


###############################################################################
# Core of the module
###############################################################################
class CMTSerialiser:
    def __init__(self, with_camera_ready: bool = False, ignore_sessions: bool = False):
        self._logger = logging.getLogger(self.__class__.__name__)
        self.with_camera_ready = with_camera_ready
        self.ignore_sessions = ignore_sessions
        if not with_camera_ready:
            self._logger.warning(
                "Metadata extracted from the CMT spreadsheet, likely to be highly inconsistent!",
            )

    def _extract_df_information(self, paper_info: pd.Series) -> Paper:
        author_names = str(paper_info["Author Names"]).split(CMT_AUTHOR_SEP)
        author_emails = str(paper_info["Author Emails"]).split(CMT_AUTHOR_SEP)

        assert len(author_emails) == len(
            author_names
        ), f"[{paper_info.id}] The number of authors ({len(author_names)}) does not match the number of emails ({len(author_emails)})"

        paper_authors = list()
        for i_author, cur_author in enumerate(author_names):
            cur_author = cur_author.replace(CMT_CORRESPONDING_MARKER, "").strip()

            match_author = CMT_AUTHOR_REGEXP.match(cur_author)
            if not match_author:
                raise Exception(
                    f"It seems that the authors used a semi-colon to separate their different affiliation. For now this needs to be fixed manually in the spreadsheet: {cur_author}"
                )

            # Extract author information
            cur_author = match_author.group(1)
            author_elts = cur_author.split(" ")
            author_elts = list(
                filter(None, author_elts)
            )  # NOTE: helpers to ignore empty elements due to multiple space
            last_name = author_elts[-1]
            first_name = " ".join(author_elts[:-1])
            email = author_emails[i_author]
            # FIXME: As for now, we dunno how to extract the affiliation component, just consider an institute
            affiliation = Affiliation(match_author.group(2), None, None)

            cur_person = Person(first_name, last_name, email=email, affiliations=set([affiliation]))
            paper_authors.append(cur_person)

        return Paper(
            str(paper_info["Paper Title"]),
            paper_authors,
            abstract=str(paper_info["Abstract"]),
            id=str(paper_info["Paper ID"]),
        )

    def load(self, conf_metadata_file: pathlib.Path) -> Conference:
        yaml = YAML(typ="rt", pure=True)
        with open(conf_metadata_file) as f_in:
            conf_info = yaml.load(f_in.read())

        if conf_info["input_data"]["root_dir"].startswith("/"):
            input_root_dir = conf_info["input_data"]["root_dir"]
        else:
            input_root_dir = conf_metadata_file.parent / conf_info["input_data"]["root_dir"]

        if conf_info["input_data"]["pdfs_dir"].startswith("/"):
            pdfs_path = pathlib.Path(conf_info["input_data"]["pdfs_dir"])
        else:
            pdfs_path = input_root_dir / conf_info["input_data"]["pdfs_dir"]

        if conf_info["input_data"]["updated_pdfs_dir"].startswith("/"):
            updated_pdfs_path = pathlib.Path(conf_info["input_data"]["updated_pdfs_dir"])
        else:
            updated_pdfs_path = input_root_dir / conf_info["input_data"]["updated_pdfs_dir"]

        if conf_info["input_data"]["metadata_spreadsheet"].startswith("/"):
            metadata_file = pathlib.Path(conf_info["input_data"]["metadata_spreadsheet"])
        else:
            metadata_file = input_root_dir / conf_info["input_data"]["metadata_spreadsheet"]

        if conf_info["input_data"]["users_spreadsheet"].startswith("/"):
            user_file = pathlib.Path(conf_info["input_data"]["users_spreadsheet"])
        else:
            user_file = input_root_dir / conf_info["input_data"]["users_spreadsheet"]

        if conf_info["input_data"]["sessions_spreadsheet"].startswith("/"):
            session_file = pathlib.Path(conf_info["input_data"]["sessions_spreadsheet"])
        else:
            session_file = input_root_dir / conf_info["input_data"]["sessions_spreadsheet"]

        annuary = self.load_users(user_file)
        papers, annuary = self.load_papers(metadata_file, pdfs_path, updated_pdfs_path, annuary)

        if self.ignore_sessions:
            return self.load_conference(conf_metadata_file, papers=papers, annuary=annuary)
        else:
            sessions = self.load_sessions(session_file, papers)
            return self.load_conference(conf_metadata_file, sessions=sessions, annuary=annuary)

    def load_users(self, user_spreadsheet_file: pathlib.Path) -> set[Person]:
        users = set()
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

                users.add(cur_user)

        return users

    def load_papers(
        self,
        submission_summary_file: pathlib.Path,
        paper_root_dir: pathlib.Path | None = None,
        updated_paper_root_dir: pathlib.Path | None = None,
        annuary: set[Person] | None = None,
    ) -> tuple[dict[str, Paper], set[Person]]:
        if annuary is None:
            annuary = set()

        dict_papers = dict()

        wb = load_workbook(filename=submission_summary_file)
        for worksheet in wb.sheetnames:
            df = pd.read_excel(submission_summary_file, engine="openpyxl", sheet_name=worksheet)
            total_papers = df.shape[0]
            failed_papers = 0
            word_papers = 0
            no_pdf = 0
            for _, paper_info in df.iterrows():
                pdf_path = None
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
                                        "source": pdf_path,
                                    },
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

                # Link PDF
                if pdf_path is not None:
                    cur_paper.pdf_file = pdf_path.resolve()

                # Add track
                cur_paper.track = worksheet

                dict_papers[cur_paper.id] = cur_paper
                for cur_author in cur_paper.authors:
                    annuary.add(cur_author)

            self._logger.info(
                f"[{worksheet}] total number of submissions {total_papers}: "
                + f"failed_papers={failed_papers} ({failed_papers/total_papers*100:.2f}%), "
                + f"word_papers={word_papers} ({word_papers/total_papers*100:.2f}%), "
                + f"nopdf ={no_pdf} ({no_pdf/total_papers*100:.2f}%)"
            )

        return dict_papers, annuary

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
            if pd.isna(session_info["Session name"]):
                continue

            session_id = str(session_info["Session name"])
            session_name = str(session_info["Session title"])

            # Create the sessions
            # TODO: Get time from the time slots, now this is just a place holder
            cur_time_slot = dict_timeslots[session_info["Timeslot name"]]
            cur_room = dict_room[session_info["Room name"]]

            session_type = str(session_info["Session type"])
            if session_type.lower() == "oral":
                cur_session = OralSession(session_id, session_name, cur_time_slot[0], cur_time_slot[1], cur_room)
            elif session_type.lower() == "poster":
                cur_session = PosterSession(session_id, session_name, cur_time_slot[0], cur_time_slot[1], cur_room)
            else:
                self._logger.error(
                    f'[{session_id}] This session type "{session_type}" is not yet supported (ignored)',
                    extra={"session_id": session_id, "session_name": session_name},
                )
                continue

            # Now deal add the papers
            session_paper_ids = [
                str(id).strip() for id in str(session_info["Papers"]).split(CMT_SESSION_PAPER_SEPARATOR)
            ]
            for paper_id in session_paper_ids:
                if paper_id not in dict_papers:
                    self._logger.error(
                        f"[{session_id}] {paper_id} is not an available papers, so ignored",
                        extra={"session_id": session_id, "session_name": session_name},
                    )
                    continue
                cur_session.add_paper(dict_papers[paper_id])
            list_sessions.append(cur_session)
        return list_sessions

    def load_conference(
        self,
        conference_info_file: pathlib.Path,
        sessions: list[Session] | None = None,
        papers: dict[str, Paper] | None = None,
        annuary: set[Person] | None = None,
    ) -> Conference:

        if (sessions is not None) and (papers is not None):
            raise Exception(
                "Either the sessions OR the papers should be given. The papers will be loaded from the sessions. In case no sessions, the provide the papers."
            )

        if annuary is None:
            annuary = set()

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
                    # FIXME: for now the email is slightly forced
                    cur_chair = Person(first_name, last_name, "noemail@nodomain.org")
                    cur_chair.add_role(Role.CHAIR)
                    chairs.append(cur_chair)

        conf = Conference(
            conf_info["id"],
            conf_info["name"],
            conf_info["startDate"],
            conf_info["endDate"],
            conf_info["location"] if "location" in conf_info else None,
            conf_info["URL"] if "URL" in conf_info else None,
            conf_info["series"] if "series" in conf_info else None,
            chairs,
            conf_info["ISSN"] if "ISSN" in conf_info else None,
            conf_info["generateDOIs"] if "generateDOIs" in conf_info else False,
        )
        if sessions is not None:
            for session in sessions:
                conf.add_session(session)
        elif papers is not None:
            for _, paper in papers.items():
                conf.add_paper(paper)

        return conf

    def dump_papers(self, papers: dict[str, Paper], output_file: pathlib.Path):
        list_papers = []
        for paper_id, cur_paper in papers.items():
            author_emails = []
            author_names = []
            for author in cur_paper.authors:
                author_emails.append(author.email)
                author_str = f"{author.firstname} "
                if author.middle_initial != "":
                    author_str += f"{author.middle_initial} "
                author_str += f"{{{author.lastname}}}"

                # TODO: add affiliations
                list_aff = []
                for aff in author.affiliations:
                    list_aff.append(str(aff))
                author_str += f"({CMT_AFFILIATION_SEPARATOR.join(list_aff)})"

                author_names.append(author_str)

            paper_info = {
                "Paper ID": int(paper_id),
                "Paper Title": cur_paper.title,
                "Paper Abstract": cur_paper.abstract,
                # "Author Emails": CMT_AUTHOR_SEP.join(author_emails),
                "Author Names": CMT_AUTHOR_SEP.join(author_names),
            }
            list_papers.append(paper_info)
        df = pd.DataFrame(list_papers)
        df.sort_values("Paper ID", inplace=True)

        with pd.ExcelWriter(output_file, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            df.to_excel(writer, sheet_name="papers", index=False)
