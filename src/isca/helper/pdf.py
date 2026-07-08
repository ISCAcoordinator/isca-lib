from typing import Any
import re
import pymupdf
import unicodedata

from isca.model.core import ISCAObject
from isca.data.pdf import PDF
from isca.model.item import Paper
from .string_helpers import diff_html, has_numbers, norm_abstract

VALID_REFERENCE_PAGE_CONTENT_REGEXP = re.compile(
    r"^([0-9]+[.][ \t]*(reference|acknowledg[e]?ment|generative ai use disclosure)s?[ \t]*|\[[0-9]+\].*)$", flags=re.IGNORECASE
)
LATEX_FONTS = set(
    [
        # "CMR9",
        # "CMMI9",
        "NimbusRomNo9L-Medi",
        "NimbusRomNo9L-ReguItal",
        "NimbusRomNo9L-Regu",
        # "NimbusMonL-Regu",
    ]
)
ANONYMOUS_METADATA_ALLOWED_AUTHOR_INFO = {
    "",
    "author name(s) withheld",
    "steidl",
    "anonymous submission to interspeech",
    "administrator",
    "xx  {};",
    "anonymous",
    "anonymous contribution",
}
ANONYMOUS_PDF_ALLOWED_AUTHOR_INFO = {
    "author",
    "anonymous",
    "abstract",
    "xx",
    "first author",
    "name",
    ". anonymous",
    "s anonymous",
    "*****",
    "*note",
    "blank ",
    "(!)",
    "g anonymous",
}
ANONYMOUS_PDF_JOKERS = {"anonymous submission to interspeech"}
ACCEPTED_FONT_SIZE = 9
ACCEPTED_PAGE_SIZE = (595, 841)


class BaseChecker(ISCAObject):
    def __init__(self):
        super().__init__()

    def validates(
        self, pid: str, pdf: PDF, paper: Paper | None = None
    ) -> tuple[bool, dict[str, bool], dict[str, str]]:  # pyright: ignore[reportUndefinedVariable]
        raise NotImplementedError("This is an abstract class, this method can't be called directly")


class MinimalPDFChecker(BaseChecker):
    """Minimal PDF Checker which assumes that the PDF is compiled using the ISCA template"""

    def __init__(self, max_nb_pages: int = 6, nb_non_content_pages: int = 2, check_font: bool = True):
        """Initialisation

        Parameters
        ----------
        max_nb_pages : int
            The maximum number of pages authorized for the publication
        nb_non_content_pages : int
            The maximum number of content pages authorized for the publication
        check_font : bool
            Should we check the fonts or simply ignore them
        """

        super().__init__()
        self._max_nb_pages = max_nb_pages
        self._nb_non_content_pages = nb_non_content_pages
        self._check_font = check_font

    def _detect_suspicious_nb_pages(self, doc: pymupdf.Document) -> None | str:
        """Check if the number of pages is suspiciously low (< nb content pages / 2)

        Parameters
        ----------
        doc : pymupdf.Document
            The PDF document

        Returns
        -------
        None | str
            None if the number of pages is valid, else the failing report

        """

        if doc.page_count < ((self._max_nb_pages - self._nb_non_content_pages) // 2):
            return f"Suspicious number of pages: {doc.page_count}"
        return None

    def _validate_fonts(self, first_page: pymupdf.Page) -> None | str:
        """Validate if the fonts of the first page are the ones required by the template

        Parameters
        ----------
        first_page : pymupdf.Page
            The first page of the PDF document

        Returns
        -------
        None | str
            None if the fonts are valid, else the failing report
        """

        report = None
        doc_fonts = set([f[3].split("+")[-1] for f in first_page.get_fonts()])  # NOTE: 4th field is hash+font name
        if not (LATEX_FONTS <= doc_fonts):
            report = f"The following fonts are missing from the first page: {list(LATEX_FONTS - doc_fonts)}"

        return report

    def _validate_title(self, title: str) -> None | str:
        """Validate if the title follows the guidelines

        Parameters
        ----------
        title : str
            The title of the article

        Returns
        -------
        None | str
            None if the title follows the guideline, else the failing report
        """
        report = None

        if title.isupper():
            return "The title is in full uppercase"
        elif title.islower():
            return "The title is in full lowercase"

        return report

    def _validate_non_content(self, doc: pymupdf.Document) -> None | str:
        """Validate if the non content page do not have content

        Parameters
        ----------
        doc : pymupdf.Document
            The PDF document of the submission

        Returns
        -------
        None | str
            None if the last pages are valid, else the failing report

        """
        start_reference_page = self._max_nb_pages - self._nb_non_content_pages
        if start_reference_page >= doc.page_count:
            return None

        lines = doc.load_page(start_reference_page).get_text().split("\n")
        for first_line in lines:
            first_line = first_line.strip()
            if first_line:
                break
        m = VALID_REFERENCE_PAGE_CONTENT_REGEXP.match(first_line.lower())
        if m:
            return None
        else:
            return f"It seems that there is content on the non-content pages: '{first_line}'"

    def validates(
        self, pid: str, pdf: PDF, paper: Paper | None = None
    ) -> tuple[bool, dict[str, bool], dict[str, str]]:  # pyright: ignore[reportUndefinedVariable]
        """Validate the PDF of a given submission

        Parameters
        ----------
        pid : str
            The paper identifier
        pdf : PDF
            the PDF document of the submission
        paper : Paper, optional
            The Paper object containing the metadata of the submission. None if no metadata is available

        Returns
        -------
        tuple[bool, dict[str, bool], dict[str, str]]
            a tuple indicating: the overall status (fail=False, pass=True), the detailed status and the detailed report)
        """
        status: dict[str, bool] = dict()
        report: dict[str, str] = dict()

        # Ensure the document is valid
        nb_pages = pdf.content.page_count
        if nb_pages > self._max_nb_pages:
            status["nb_pages"] = True
            report[
                "nb_pages"
            ] = f"The number of pages {nb_pages} is above the maximum autorised number of pages {self._max_nb_pages}"
        else:
            suspicious_report = self._detect_suspicious_nb_pages(pdf.content)
            if suspicious_report is not None:
                status["nb_pages"] = True
                report["nb_pages"] = suspicious_report

        if pdf.metadata is None:
            status["no_metadata"] = True
            return (False, status, report)

        if pdf.info is not None:
            if not "font_size" in pdf.info:
                status["font_size"] = True
                report["font_size"] = "Could not extract the font size"
            elif pdf.info["font_size"] != ACCEPTED_FONT_SIZE:
                status["font_size"] = True
                report["font_size"] = f"The computed font size is {pdf.info['font_size']} instead of {ACCEPTED_FONT_SIZE}"

            if not "page_size" in pdf.info:
                status["page_size"] = True
                report["page_size"] = "Could not extract the font size"
            elif (abs(int(pdf.info["page_size"][0]) - ACCEPTED_PAGE_SIZE[0]) > 1) or (
                abs(int(pdf.info["page_size"][1]) - ACCEPTED_PAGE_SIZE[1]) > 1
            ):
                status["page_size"] = True
                report["page_size"] = f"The computed page size is {pdf.info['page_size']} instead of {ACCEPTED_PAGE_SIZE}"

        # Check if document is latex of word
        is_latex = False
        creator = "Unknown"
        if "creator" in pdf.metadata:
            creator = pdf.metadata["creator"].lower()
            is_latex = (creator == "latex with hyperref") or (creator.startswith("tex")) or (creator.startswith(" tex"))
        if not is_latex:
            status["not_latex_template"] = True
            report["not_latex_template"] = f"The document creator is {creator}"

        # Check that the title page is parseable
        first_page = pdf.content.load_page(0)
        first_page_text = first_page.get_text()
        if not first_page_text:
            status["first_page_not_text"] = True

        # Validate fonts of the first page01
        if self._check_font and is_latex:
            report_font = self._validate_fonts(first_page)
            if report_font is not None:
                status["font"] = True
                report["font"] = report_font

        # Check the title
        if is_latex:
            metadata_pdf_title = pdf.title
            if metadata_pdf_title is None:
                status["pdf_title"] = True
                report["pdf_title"] = "There is no title in the metadata of the PDF"
            else:
                metadata_pdf_title = " ".join(metadata_pdf_title.split())
                report_title = self._validate_title(metadata_pdf_title)
                if report_title is not None:
                    status["pdf_title"] = True
                    report["pdf_title"] = report_title

        # Check the title
        if paper is not None:
            metadata_title = paper.title
            metadata_title = " ".join(metadata_title.split())
            report_title = self._validate_title(metadata_title)
            if report_title is not None:
                status["metadata_title"] = True
                report["metadata_title"] = report_title

        # Check that non-content pages do not contains content! (TODO: disabled for now)
        if False:
            report_invalid_non_content = self._validate_non_content(pdf.content)
            if report_invalid_non_content is not None:
                status["invalid_non_content"] = True
                report["invalid_non_content"] = report_invalid_non_content

        return (not (len(status.keys()) > 0), status, report)


class AnonymousPDFChecker(MinimalPDFChecker):
    """PDF Checker to validate if that an anonymous submission validates the requirements of the PDF format AND the anonymity requirements"""

    def __init__(self, max_nb_pages: int = 6, nb_non_content_pages: int = 2, check_fonts: bool = True, strict: bool = True):
        """Initialisation

        Parameters
        ----------
        max_nb_pages : int
            The maximum number of pages authorized for the publication
        nb_non_content_pages : int
            The maximum number of content pages authorized for the publication
        check_font : bool
            Should we check the fonts or simply ignore them
        strict : bool
            If True, do not let anything pass, else be more tolerant (see the method validates to know the conditions)
        """
        super().__init__(max_nb_pages, nb_non_content_pages, check_fonts)
        self._strict = strict

    def _anonymous_metadata(self, pdf: PDF) -> None | str:
        """Validate if the PDF metadata does not leak information

        Parameters
        ----------
        pdf : PDF
            The PDF object to validate

        Returns
        -------
        None | str
            None if no information is leaked, a string report if some information has been found
        """

        report = None
        if (pdf.metadata is None) or ("author" not in pdf.metadata):
            return report

        auth = pdf.metadata["author"].lower()
        if auth not in ANONYMOUS_METADATA_ALLOWED_AUTHOR_INFO:
            if not auth.startswith("firstnamea"):  # FIXME: hardcoded
                report = f"Author visible in the metadata: {auth}"
        return report

    def _anonymous_pdf(self, title: str, pdf: PDF, strict: bool = True) -> None | str:
        """Validate if the visible part of the PDF does not leak information

        Parameters
        ----------
        title: str
            The title used as a reference to detect the author area
        pdf : PDF
            The PDF object to validate
        strict: bool
            The validation is strict if True, if False - if some tokens (see ANONYMOUS_PDF_JOKERS) are detected, the PDF is defacto considered valid!

        Returns
        -------
        None | str
            None if no information is leaked, a string report if some information has been found
        """
        report = None

        # Prepare the content of the PDF to be analyzed
        txt = pdf.content[0].get_text().lower().replace("\n", " ")
        txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii")
        txt = txt.replace("  ", " ")

        # Joker strings which qualified the paper to defacto be anonymous (!Dangerous!!!!)
        if not strict:
            valid = False
            for joker in ANONYMOUS_PDF_JOKERS:
                if re.match(f".*{joker.lower()}.*", txt):
                    valid = True
                    break
            if valid:
                return None

        # Prepare the title to be searched (but be relaxed with the non-letter)
        title = title.lower().strip()
        title = title.replace(" ", "")

        def _generate_regex_elt(s):
            if not re.match("[a-z]", s):
                s = f"[{s}]?"

            return s + "[ ]*"

        title_regexp = "".join([_generate_regex_elt(s) for s in title])

        authstr = re.sub(title_regexp, "", txt).strip()

        valid = False
        for ok in ANONYMOUS_PDF_ALLOWED_AUTHOR_INFO:
            if authstr.startswith(ok):
                valid = True
                break

        if not valid:
            return f'PDF Not anonymous, beginning of the "author part" : {authstr[:100]}'

        return report

    def validates(
        self, pid: str, pdf: PDF, paper: Paper | None = None
    ) -> tuple[bool, dict[str, bool], dict[str, str]]:  # pyright: ignore[reportUndefinedVariable]
        """Validate the PDF of a given submission

        Parameters
        ----------
        pid : str
            The paper identifier
        pdf : PDF
            the PDF document of the submission
        paper : Paper, optional
            The Paper object containing the metadata of the submission. None if no metadata is available

        Returns
        -------
        tuple[bool, dict[str, bool], dict[str, str]]
            a tuple indicating: the overall status (fail=False, pass=True), the detailed status and the detailed report)
        """
        assert paper is not None, f"[pid={pid}] For anonymous submission, the paper metadata (not the PDF metdata) is required"
        _, summary, report = super().validates(pid, pdf, paper)

        # TODO: add specific checks
        report_anonymous_metadata = self._anonymous_metadata(pdf)
        if report_anonymous_metadata is not None:
            summary["anonymous_metadata"] = True
            report["anonymous_metadata"] = report_anonymous_metadata

        report_anonymous_pdf = self._anonymous_pdf(paper.title, pdf, self._strict)
        if report_anonymous_pdf is not None:
            summary["anonymous_pdf"] = True
            report["anonymous_pdf"] = report_anonymous_pdf

        return (len(summary.keys()) > 0, summary, report)


class CameraReadyPDFChecker(MinimalPDFChecker):
    def __init__(self, max_nb_pages: int = 6, nb_non_content_pages: int = 2, check_font: bool = True):
        super().__init__(max_nb_pages, nb_non_content_pages, check_font)

    def _validate_authors(self, paper: Paper) -> str | None:
        report = []
        for author in paper.authors:
            lastname = author.lastname
            firstname = author.firstname
            slow = lastname.lower()

            if lastname.isupper():
                report.append(f'The lastname "{lastname}" is in full uppercase')
            if lastname.islower():
                report.append(f'The lastname "{lastname}" is in full lowercase')
            if lastname.isupper():
                report.append(f'The lastname "{lastname}" is in full uppercase')
            if lastname.islower():
                report.append(f'The lastname "{lastname}" is in full lowercase')
            if "_" in lastname:
                report.append(f"underscore in lastname {lastname} for")
            if len(lastname) == 1:
                report.append(f'length 1 lastname "{lastname}')
            if lastname in {
                "1",
                "(1)",
                "(2)",
                "I.",
                "II",
                "IV",
                "El",
                "Jr",
                "[NO",
                "Jr.",
                "III",
            }:
                report.append(f"Undefined error in {lastname}")
            if has_numbers(lastname):
                report.append(f"lastname may contain numbers {n1} {n2}")
            if "." in lastname:
                if len(slow.split()) > 1 and lastname.split()[-1] == "Jr.":
                    pass
                else:
                    report.append(f"period in lastname {lastname}")
            if lastname[0] == lastname[0].lower():
                if slow.startswith("d'"):
                    pass
                elif len(slow.split()) > 1 and slow.split()[0] in {"de", "van", "ten"}:
                    pass
                else:
                    report.append(f"lastname case? {lastname}")

            if lastname in {"d'Alessandro", "Matsu'ura", "N'Guyen"}:
                pass
            elif "'" in lastname:
                if not slow.startswith("o'") and not slow.startswith("d'") and not slow.startswith("prud'"):
                    report.append(f"quote in lastname? {lastname}")

            if "}" in lastname:
                report.append(f"brace in lastname? {lastname}")

        if not report:
            return None
        else:
            return "\n".join(report)

    def _validate_abstract(self, first_page: pymupdf.Page, abstract: str) -> str | None:
        first_page_content = str(first_page.get_text())
        report = None
        # didn't find the exact abstract, try more permissive search
        ab_st = first_page_content.lower().find("abstract")
        if ab_st > -1:
            # Search indexed terms or keywords first
            res = re.search("(index terms[ ]*|keywords[ ]*:)", first_page_content.lower())
            ab_fin = res.start() if res is not None else -1
            # If not working try to find the introduction
            if ab_fin == -1:
                res = re.search(r"(1.? )?introduction", first_page_content.lower())
                ab_fin = res.start() if res is not None else -1

            # found abstract so generate diff
            if ab_st > -1 and ab_fin > -1:
                abstract_cand = first_page_content[ab_st + 8 : ab_fin].strip()
                abstract_cand = norm_abstract(abstract_cand)
                # dlist = find_diffs(abstract, abstract_cand, METADATA_DIFF_HEADER, PDF_DIFF_HEADER)
                diff_latex = diff_html(abstract, abstract_cand)
                if diff_latex != "":
                    report = diff_latex
            else:
                report = "manual check required"
        else:
            report = "manual check required"

        return report

    def validates(
        self, pid: str, pdf: PDF, paper: Paper | None = None
    ) -> tuple[bool, dict[str, bool], dict[str, str]]:  # pyright: ignore[reportUndefinedVariable]
        assert paper is not None, f"[pid={pid}] For anonymous submission, the paper metadata (not the PDF metdata) is required"
        _, summary, report = super().validates(pid, pdf, paper)

        # Check authors
        authors_report = self._validate_authors(paper)
        if authors_report is not None:
            summary["authors"] = True
            report["authors"] = authors_report

        # Check abstract
        first_page = pdf.content.load_page(0)
        abstract_report = self._validate_abstract(first_page, paper.abstract if paper.abstract is not None else "")
        if abstract_report is not None:
            summary["abstract"] = True
            report["abstract"] = abstract_report

        return (len(summary.keys()) > 0, summary, report)


class ValidateAuthors(BaseChecker):
    def __init__(self):
        super().__init__()

    def validates(
        self, pid: str, pdf: PDF, paper: Paper | None = None
    ) -> tuple[bool, dict[str, bool], dict[str, str]]:  # pyright: ignore[reportUndefinedVariable]
        summary = {}
        report = {}

        if len(paper.authors) != len(pdf.authors):
            summary["diff_nb_authors"] = True
            summary[
                "diff_nb_authors"
            ] = f"The PDF file has {len(pdf.authors)} while the metadata has {len(paper.authors)} authors"

        return (len(summary.keys()) > 0, summary, report)
