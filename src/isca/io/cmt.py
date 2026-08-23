# Python
import re
import pathlib
import traceback

# Data
from openpyxl import load_workbook
import pandas as pd

# Model
from ..model.item import Paper
from ..model.person import Annuary, Person, Affiliation, Role

# IO
from .base import Serialiser
from .utils.pdf import PDFLoader, PDFMetadataException
from .utils.helpers import load_excel


class WordException(Exception):
    pass


class CMTSerialiser(Serialiser):
    CORRESPONDING_AUTHOR_MARKER = "*"
    AUTHOR_NAME_AFFILIATION_SEPARATOR = "); "
    AUTHOR_SEPARATOR = "; "
    AFFILIATION_SEPARATOR = ";"
    AUTHOR_FULL_INFO_REGEXP = re.compile("^([^(]*)\\s*\\((.*)\\)\\s*")
    AUTHOR_ELTS_REGEXP = re.compile("^\\s*(?:([^{}]+)\\s*)?(?:\\[([^{}]+)\\]\\s*)?\\{(.+)\\}\\s*$")
    AFFILIATION_REGEXP = re.compile("^\\s*(?:\\{([^}]+)\\},\\s*)?([^{]+)\\s*(?:,\\s*\\{([^}]+)\\})?\\s*$")
    MAX_ID_NAME_LENGTH = 8

    def __init__(self, metadata_from_pdf: bool = True, debug: bool = False):
        super().__init__()
        self.debug = debug
        self._annuary = Annuary()
        self._pdf_loader = PDFLoader(self._annuary)
        self._id_generator: dict[str, int] = dict()
        self._metadata_from_pdf: bool = metadata_from_pdf
        self._ignored_spreadsheet: set[str] = set(["Changes log"])  # TODO: hardcoded for now

    def load_papers(
        self,
        submission_summary_file: pathlib.Path,
        paper_root_dir: pathlib.Path | None = None,
        updated_paper_root_dir: pathlib.Path | None = None,
        pdf_name_format: str = "{paper_id}.pdf",
    ) -> tuple[dict[str, Paper], Annuary]:

        dict_papers = dict()

        wb = load_workbook(filename=submission_summary_file)
        for worksheet in wb.sheetnames:
            if worksheet in self._ignored_spreadsheet:
                self.logger.info(f'Ignoring spreadsheet "{worksheet}"')
                continue

            df = load_excel(submission_summary_file, sheet_name=worksheet)
            total_papers = df.shape[0]
            failed_papers = 0
            word_papers = 0
            no_pdf = 0

            # Else go through not
            for _, paper_info in df.iterrows():
                paper_id = str(paper_info["Paper ID"])

                # Ignore withdrawn papers
                withdrawn = paper_info.get("Withdrawn", False)
                if withdrawn:
                    self.logger.info(f"[{paper_id}] The paper is withdrawn")
                    continue

                # First use the metadata as "default" information
                cur_paper = self._extract_df_information(paper_info)

                # If expected to have PDF, use the PDF to replace the information
                pdf_path = None
                if paper_root_dir is not None:
                    # FIXME: this is pretty lame as it assumes that the paper id is an int!
                    pdf_file_name = pdf_name_format.format_map({"paper_id": int(paper_id)})
                    paper_id = str(paper_id)
                    pdf_path = paper_root_dir / pdf_file_name

                    if (updated_paper_root_dir is not None) and (updated_paper_root_dir / pdf_file_name).exists():
                        self.logger.debug(
                            f"[{paper_id}] using the updated PDF",
                            extra={
                                "paper_id": paper_id,
                            },
                        )
                        pdf_path = updated_paper_root_dir / pdf_file_name

                if self._metadata_from_pdf:
                    try:
                        if (pdf_path is not None) and pdf_path.exists():
                            pdf = self._pdf_loader.load_pdf(pdf_path, True)
                            cur_paper.title = pdf.title

                            if (pdf.authors is not None) and (len(pdf.authors) > 0):
                                if len(pdf.authors) != len(cur_paper.authors):
                                    self.logger.error(
                                        f"[{paper_id}] The number of authors in the metadata and in the PDF are different (pdf={len(pdf.authors)}, metadata={len(cur_paper.authors)})",
                                        extra={"paper_id": paper_id},
                                    )
                                else:
                                    for i_author in range(len(pdf.authors)):
                                        aff = cur_paper.authors[i_author].get_first_affiliation(paper_id)
                                        if aff is not None:
                                            pdf.authors[i_author].add_paper_affiliation(paper_id, aff)

                                    cur_paper.authors = pdf.authors

                            self.logger.debug(
                                f"[{paper_id}] Metadata extracted from the PDF {pdf_path}",
                                extra={
                                    "paper_id": paper_id,
                                    "metadata_from_pdf": True,
                                    "source": pdf_path,
                                },
                            )
                        else:
                            self.logger.warning(
                                f"[{paper_id}] No PDF attached",
                                extra={"paper_id": paper_id},
                            )
                            no_pdf += 1

                    except WordException:
                        self.logger.warning(
                            f"[{paper_id}] Can't extract the information from a PDF generated by word",
                            extra={
                                "paper_id": paper_id,
                            },
                        )
                        word_papers += 1
                    except (PDFMetadataException, KeyError, IndexError) as ex:  # pyright: ignore[reportUndefinedVariable]
                        if self.debug:
                            raise ex
                        else:
                            self.logger.error(
                                f"[{paper_id}] Extraction of the metadata from the PDF failed, falling back on the excel spreadsheet",
                                extra={
                                    "paper_id": paper_id,
                                    "exception": ex,
                                    "traceback": traceback.format_exc(),
                                },
                            )
                            failed_papers += 1

                # Link PDF
                if (pdf_path is not None) and pdf_path.exists():
                    cur_paper.pdf_file = pdf_path.resolve()

                # Add track
                cur_paper.track = worksheet

                dict_papers[cur_paper.id] = cur_paper
                for cur_author in cur_paper.authors:
                    self._annuary.add(cur_author)

            self.logger.info(
                f"[{worksheet}] total number of submissions {total_papers}: "
                + f"failed_papers={failed_papers} ({failed_papers/total_papers*100:.2f}%), "
                + f"word_papers={word_papers} ({word_papers/total_papers*100:.2f}%), "
                + f"nopdf={no_pdf} ({no_pdf/total_papers*100:.2f}%)"
            )

        return dict_papers, self._annuary

    def _generate_id(self, first_name: str | None, last_name: str) -> str:
        id = last_name.strip().lower().replace(" ", "")[: CMTSerialiser.MAX_ID_NAME_LENGTH]
        id = "".join(char for char in id if char.isalpha())
        if not id:
            id = first_name.strip().lower().replace(" ", "")[: CMTSerialiser.MAX_ID_NAME_LENGTH]
            id = "".join(char for char in id if char.isalpha())

        if id in self._id_generator:
            self._id_generator[id] += 1
            id = id + str(self._id_generator[id])
        else:
            self._id_generator[id] = 0

        assert id, "The id is empty, meaning something is wrong with this authors"
        return id

    def _extract_df_information(self, paper_info: pd.Series) -> Paper:

        paper_id = paper_info["Paper ID"]
        author_names = (
            str(paper_info["Author Names"])
            .replace(CMTSerialiser.CORRESPONDING_AUTHOR_MARKER, "")
            .split(CMTSerialiser.AUTHOR_NAME_AFFILIATION_SEPARATOR)
        )
        author_emails = [
            email.lower().strip() for email in str(paper_info["Author Emails"]).split(CMTSerialiser.AUTHOR_SEPARATOR)
        ]

        # The number of elements should be the same
        if len(author_emails) != len(author_names):
            names = "\n".join(author_names)
            self.logger.error(f"[{paper_id}] author names = {names}")
            self.logger.error(f"[{paper_id}] author emails = {author_emails}")
            raise Exception(
                f"[{paper_id}] The number of authors ({len(author_names)}) does not match the number of emails ({len(author_emails)})"
            )

        paper_authors = list()
        for i_author, cur_author in enumerate(author_names):
            cur_author = cur_author.replace(CMTSerialiser.CORRESPONDING_AUTHOR_MARKER, "").strip()
            if cur_author[-1] != ")":
                cur_author = cur_author + ")"

            match_author_affiliations = CMTSerialiser.AUTHOR_FULL_INFO_REGEXP.match(cur_author)
            if not match_author_affiliations:
                raise Exception(f"[{paper_id}] Impossible to parse the author, please fix the spreadsheet: {cur_author}")

            # Extract author information
            middle_initial = None
            email = author_emails[i_author]
            cur_author = match_author_affiliations.group(1)
            if "{" in cur_author:
                match_author = CMTSerialiser.AUTHOR_ELTS_REGEXP.match(cur_author)
                if match_author:
                    first_name = match_author.group(1)
                    middle_initial = match_author.group(2)
                    last_name = match_author.group(3)
                else:
                    raise Exception(f"[{paper_id}] Impossible to parse the author, please fix the spreadsheet: {cur_author}")
            else:
                author_elts = cur_author.split(" ")
                author_elts = list(filter(None, author_elts))  # NOTE: helpers to ignore empty elements due to multiple space
                last_name = author_elts[-1]
                first_name = " ".join(author_elts[:-1])

            first_name = first_name.strip() if first_name is not None else None
            last_name = last_name.strip()

            # Extract the affiliation part
            list_affiliations = list()
            affiliations = [s.strip() for s in match_author_affiliations.group(2).split(CMTSerialiser.AFFILIATION_SEPARATOR)]
            for f in affiliations:
                match_affiliation = CMTSerialiser.AFFILIATION_REGEXP.match(f)
                if not match_affiliation:
                    raise Exception(f"[{paper_id}] The following affiliation for author {cur_author} is not valid: {f}")

                country = None
                if len(match_affiliation.groups()) > 2:
                    country = match_affiliation.group(3)

                short = match_affiliation.group(2)
                long = f"{match_affiliation.group(1)}, {short}"
                affiliation = Affiliation(short=short, long=long, country=country)
                list_affiliations.append(affiliation)
            assert len(list_affiliations) > 0

            cur_person = self._annuary.find_person_by_email(email)
            if cur_person is None:
                id = self._generate_id(first_name, last_name)
                cur_person = Person(
                    id,
                    first_name,
                    last_name,
                    email=email,
                    default_affiliation=list_affiliations[0],
                    roles=set([Role.AUTHOR]),
                )
                self._annuary.add(cur_person)
            else:
                cur_person.add_role(Role.AUTHOR)
                if cur_person.firstname != first_name:
                    self.logger.debug(
                        f"[{paper_id}] Change the name of {email} from {cur_person.name} to {first_name} {{{last_name}}}"
                    )

                # NOTE: The information from the PDF are likely more reliable
                cur_person.firstname = first_name
                cur_person.lastname = last_name

            # Send a warning if the person name is suspicious
            if (
                ((cur_person.firstname is not None) and (cur_person.firstname.isupper() or cur_person.firstname.islower()))
                or cur_person.lastname.isupper()
                or cur_person.lastname.islower()
            ):
                self.logger.warning(f"[{paper_id}] The current person as an invalid name: {cur_person}")

            for affiliation in list_affiliations:
                cur_person.add_paper_affiliation(str(paper_info["Paper ID"]), affiliation)
            paper_authors.append(cur_person)

        abstract = None
        if "Abstract" in paper_info:
            abstract = str(paper_info["Abstract"])
        elif "Paper Abstract" in paper_info:
            abstract = str(paper_info["Paper Abstract"])
        abstract = re.sub(r"(?<!\n)\n(?=\S)", " ", abstract)  # NOTE: merge consecutive lines

        # Fix title
        title = str(paper_info["Paper Title"])
        if ("\n" in title) or ("\r" in title):
            title = title.replace("\r", "")
            title = " ".join([t.strip() for t in title.split("\n")])

        return Paper(str(paper_info["Paper ID"]), title, paper_authors, abstract=abstract)
