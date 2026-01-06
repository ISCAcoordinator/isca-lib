import re
import pymupdf
from isca.model.core import ISCAObject
from isca.data.pdf import PDF

INVALID_SECTION_REGEXP = re.compile(r"^[0-9]+[.] (reference|acknowledgements?)$")
LATEX_FONTS = set(
    [
        # "CMR9",
        # "CMMI9",
        "NimbusRomNo9L-Medi",
        "NimbusRomNo9L-ReguItal",
        "NimbusRomNo9L-Regu",
        "NimbusMonL-Regu",
    ]
)


class MinimalPDFChecker(ISCAObject):
    def __init__(self, max_nb_pages: int = 5, nb_non_content_pages: int = 1):
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
        first_line = doc.load_page(start_reference_page).get_text().split("\n")[0]
        m = INVALID_SECTION_REGEXP.match(first_line.lower())
        if m:
            return None
        else:
            return f"It seems that there is content on the non-content pages: {first_line}"

    def validates(self, pid: str, pdf: PDF) -> tuple[bool, dict[str, bool], dict[str, str]]:
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
            metadata_pdf_title = pdf.metadata["title"]
            metadata_pdf_title = " ".join(metadata_pdf_title.split())
            report_title = self._validate_title(metadata_pdf_title)
            if report_title is not None:
                status["title"] = True
                report["title"] = report_title

        # Check that non-content pages do not contains content!
        report_invalid_non_content = self._validate_non_content(pdf.content)
        if report_invalid_non_content is not None:
            status["invalid_non_content"] = True
            report["invalid_non_content"] = report_invalid_non_content

        return (not (len(status.keys()) > 0), status, report)


class CameraReadyPDFChecker(MinimalPDFChecker):
    def __init__(self):
        super().__init__()

    def validates(self, pid: str, pdf: PDF) -> tuple[bool, dict[str, bool], dict[str, str]]:
        (_, summary, report) = super().validates(pid, pdf)

        # TODO: add specific checks

        return (len(summary.keys()) > 0, summary, report)
