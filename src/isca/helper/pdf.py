import re
import pymupdf
from isca.model.core import ISCAObject
from isca.data.pdf import PDF
from isca.model.item import Paper
import unicodedata

INVALID_SECTION_REGEXP = re.compile(r"^([0-9]+[.][ \t]*([Rr]eference|[Aa]cknowledgement)s?[ \t]*|\[[0-9]+\] .*)$")
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
    "anonymous submission to interspeech 2025",
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
ACCEPTED_FONT_SIZE = 9
ACCEPTED_PAGE_SIZE = (595, 841)


class MinimalPDFChecker(ISCAObject):
    """Minimal PDF Checker which assumes that the PDF is compiled using the ISCA template"""

    def __init__(self, max_nb_pages: int = 6, nb_non_content_pages: int = 2):
        super().__init__()
        self._max_nb_pages = max_nb_pages
        self._nb_non_content_pages = nb_non_content_pages
        self._check_font = True

    def _validate_font(self, first_page) -> None | str:
        report = None
        doc_fonts = set([f[3].split("+")[-1] for f in first_page.get_fonts()])  # NOTE: 4th field is hash+font name
        if not (LATEX_FONTS <= doc_fonts):
            report = f"The following fonts are missing from the first page: {list(LATEX_FONTS - doc_fonts)}"

        return report

    def _validate_title(self, title: str) -> None | str:
        report = None

        if title.isupper():
            return "The title is in full uppercase"
        elif title.islower():
            return "The title is in full lowercase"

        return report

    def _validate_non_content(self, doc: pymupdf.Document) -> None | str:
        start_reference_page = self._max_nb_pages - self._nb_non_content_pages
        lines = doc.load_page(start_reference_page).get_text().split("\n")
        for first_line in lines:
            first_line = first_line.strip()
            if first_line:
                break
        m = INVALID_SECTION_REGEXP.match(first_line.lower())
        if m:
            return None
        else:
            return f"It seems that there is content on the non-content pages: '{first_line}'"

    def validates(self, pid: str, pdf: PDF, paper: Paper | None = None) -> tuple[bool, dict[str, bool], dict[str, str]]:
        status: dict[str, bool] = dict()
        report: dict[str, str] = dict()

        # Ensure the document is valid
        nb_pages = pdf.content.page_count
        if nb_pages > self._max_nb_pages:
            status["nb_pages"] = True
            report[
                "nb_pages"
            ] = f"The number of pages {nb_pages} is above the maximum autorised number of pages {self._max_nb_pages}"

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
                report["page_size"] = f"The computed font size is {pdf.info['page_size']} instead of {ACCEPTED_PAGE_SIZE}"

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
            report_font = self._validate_font(first_page)
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

        # Check that non-content pages do not contains content!
        report_invalid_non_content = self._validate_non_content(pdf.content)
        if report_invalid_non_content is not None:
            status["invalid_non_content"] = True
            report["invalid_non_content"] = report_invalid_non_content

        return (not (len(status.keys()) > 0), status, report)


class AnonymousPDFChecker(MinimalPDFChecker):
    def __init__(self, max_nb_pages: int = 6, nb_non_content_pages: int = 2):
        super().__init__(max_nb_pages, nb_non_content_pages)

    def anonymous_metadata(self, pdf: PDF) -> None | str:
        report = None
        if (pdf.metadata is None) or ("author" not in pdf.metadata):
            return report

        auth = pdf.metadata["author"].lower()
        if auth not in ANONYMOUS_METADATA_ALLOWED_AUTHOR_INFO:
            if not auth.startswith("firstnamea"):  # FIXME: hardcoded
                report = f"Author visible in the metadata: {auth}"
        return report

    def anonymous_pdf(self, title: str, pdf: PDF) -> None | str:
        # Prepare the content of the PDF to be analyzed
        txt = pdf.content[0].get_text().lower().replace("\n", " ")
        txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii")
        txt = txt.replace("  ", " ")

        # Prepare the title to be searched (but be relaxed with the non-letter)
        title = title.lower().strip()
        title = title.replace(" ", "")

        def _generate_regex_elt(s):
            if not re.match("[a-z]", s):
                s = f"[{s}]?"

            return s + "[ ]*"

        title_regexp = "".join([_generate_regex_elt(s) for s in title])

        report = None
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
        assert paper is not None, f"[pid={pid}] For anonymous submission, the paper metadata (not the PDF metdata) is required"
        _, summary, report = super().validates(pid, pdf, paper)

        # TODO: add specific checks
        report_anonymous_metadata = self.anonymous_metadata(pdf)
        if report_anonymous_metadata is not None:
            summary["anonymous_metadata"] = True
            report["anonymous_metadata"] = report_anonymous_metadata

        report_anonymous_pdf = self.anonymous_pdf(paper.title, pdf)
        if report_anonymous_pdf is not None:
            summary["anonymous_pdf"] = True
            report["anonymous_pdf"] = report_anonymous_pdf

        return (len(summary.keys()) > 0, summary, report)


class CameraReadyPDFChecker(MinimalPDFChecker):
    def __init__(self):
        super().__init__()

    def validates(
        self, pid: str, pdf: PDF, paper: Paper | None = None
    ) -> tuple[bool, dict[str, bool], dict[str, str]]:  # pyright: ignore[reportUndefinedVariable]
        assert paper is not None, f"[pid={pid}] For anonymous submission, the paper metadata (not the PDF metdata) is required"
        _, summary, report = super().validates(pid, pdf, paper)

        # TODO: add specific checks

        return (len(summary.keys()) > 0, summary, report)
