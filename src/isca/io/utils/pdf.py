"""Module providing PDF related helpers

This module mainly contains the main routines to determine if a given PDF file validates the ISCA requirements
"""

import re
from pathlib import Path
import pymupdf

from isca.model.core import ISCAObject
from isca.model.person import Annuary, Person
from isca.data.pdf import PDF

from collections import Counter


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


PDF_WORD_KEYWORD_SUFFIX = "_WORD_TEMPLATE"
PDF_AUTHOR_KEY = "author"
PDF_TITLE_KEY = "title"
PDF_AUTHOR_RE = r"([^{]+) \{([^}]+)\}(?: \{([0-9, ]+)\})?"


class PDFMetadataException(Exception):
    """Exception found in the metadata extracted from the PDF"""

    pass


class PDFLoader(ISCAObject):
    """PDF File loader

    Attributes
    ----------
    _annuary : Annuary | None
       If not None, the annuary to be used to avoid duplicating authors
    """

    def __init__(self, annuary: Annuary | None = None):
        """Initialisation method

        Parameters
        ----------
        annuary : Annuary, optional
            The annuary to look for existing/add authors

        """

        super().__init__()
        self._annuary = annuary

    def load_pdf(self, pdf_file: Path, camera_ready: bool = True) -> PDF:
        """Helper to load the PDF file

        Parameters
        ----------
        pdf_file : Path
            The path to the PDF file
        camera_ready : bool
            Is the PDF a camera ready version?

        Returns
        -------
        PDF
            the PDF object loaded from the PDF file

        """

        # Parse metadata
        pdf_document: pymupdf.Document = pymupdf.open(pdf_file)
        metadata = self._load_extended_metadata(pdf_document)
        pdf_info = self._extract_additional_info(pdf_document)

        # Check if it is a word document
        title = ""
        if PDF_TITLE_KEY in metadata:
            title = metadata[PDF_TITLE_KEY].replace("\n", " ")

        if not title:
            raise KeyError("The PDF is not valid as there is no title")

        authors = None
        if camera_ready:
            authors = self._get_authors(metadata)

        return PDF(pdf_file, pdf_document, metadata, pdf_info, title, authors)

    def _load_extended_metadata(self, pdf_document: pymupdf.Document) -> dict[str, str]:
        """Load the metadata from the PDF file (including the extended keys)

        Parameters
        ----------
        pdf_content: pymupdf.Document
            the PDF document object

        Returns
        -------
        dict[str, str]
            the dictionnary containing the metadata

        """

        metadata = {}  # make my own metadata dict
        what, value = pdf_document.xref_get_key(-1, "Info")  # /Info key in the trailer
        if what != "xref":
            pass  # PDF has no metadata
        else:
            xref = int(value.replace("0 R", ""))  # extract the metadata xref
            for key in pdf_document.xref_get_keys(xref):
                metadata[key.lower()] = pdf_document.xref_get_key(xref, key)[1]

        return metadata

    def _get_authors(self, metadata: dict[str, str]) -> list[Person]:
        """Retrieve the authors from the metadata

        Parameters
        ----------
        metadata : dict[str, str]
            The metadata containing the authors' information

        Returns
        -------
        list[Person]
            The list of parsed authors

        Raises
        ------
        PDFMetadataException
            The PDF is either not using the Interspeech template, or is not the camera ready version
        """

        list_authors = []
        authors_meta = metadata[PDF_AUTHOR_KEY].split(";")
        for cur_author in authors_meta:
            cur_author = cur_author.strip()
            if not cur_author:
                continue

            m = re.match(PDF_AUTHOR_RE, cur_author)
            if m:
                first_name = m.group(1)
                last_name = m.group(2)
                if (not last_name) and first_name:
                    if " " in first_name:
                        last_name = first_name.split(" ")[-1]
                        first_name = " ".join(first_name.split(" ")[:-1])
                    else:
                        last_name = first_name
                        first_name = ""

                matching_authors = set()
                if self._annuary is not None:
                    matching_authors = self._annuary.find_persons_by_name(first_name, last_name, ignore_middle_initial=True)

                if len(matching_authors) == 1:
                    cur_author = matching_authors.pop()
                else:
                    if len(matching_authors) > 1:
                        self.logger.debug(
                            f"Multiple authors available for ({first_name} {last_name}), do not select any but solves this for later"
                        )

                    try:
                        cur_author = Person(
                            None,
                            first_name,
                            last_name,
                        )
                    except Exception:
                        raise PDFMetadataException(f'Can\'t parse authors: "{cur_author}"')

                list_authors.append(cur_author)
            else:
                raise PDFMetadataException(f'Can\'t parse authors: "{cur_author}"')

        return list_authors

    def _extract_additional_info(self, pdf_document: pymupdf.Document) -> dict[str, str]:
        pdf_info = dict()

        # Get the first page size
        page1 = pdf_document[0].get_text("dict")
        pdf_info["page_size"] = (int(page1["width"]), int(page1["height"]))

        # Get the first page font size (majority)
        blocks = pdf_document[0].get_text("dict", flags=11)["blocks"]
        fsizes = []
        for b in blocks:  # iterate through the text blocks
            for l in b["lines"]:  # iterate through the text lines
                for s in l["spans"]:  # iterate through the text spans
                    fsizes += [round(s["size"])]

        if len(fsizes) == 0:
            pdf_info["font_size"] = 0
        else:
            most_common = Counter(fsizes).most_common()
            # don't count line numbers
            if most_common[0][0] == 5:
                pdf_info["font_size"] = most_common[1][0]
            else:
                pdf_info["font_size"] = most_common[0][0]

        return pdf_info
