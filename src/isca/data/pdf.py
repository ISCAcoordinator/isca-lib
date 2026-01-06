import pathlib
import pymupdf


from isca.model.core import ISCAItem
from isca.model.person import Person


class PDF(ISCAItem):
    """Class representing the information related to a PDF article

    For a PDF file to be processed by this class, it should be generated using the Interspeech LaTeX template.
    The Interspeech LaTeX template is available on overleaf:

    Attributes
    ----------
    pdf_file: pathlib.Path
        the path to the PDF file
    pdf_content: pymupdf.Document
        the pymupdf document to access the PDF file data
    metadata: dict[str, str]
        The (extended) metadata extracted from the PDF
    title: str
        The title extracted from the PDF
    authors: list[Person]
        The list of authors extracted from the PDF
    """

    def __init__(
        self,
        pdf_file: pathlib.Path,
        pdf_content: pymupdf.Document,
        pdf_metadata: dict[str, str] | None,
        title: str | None,
        authors: list[Person] | None,
    ):
        """Initialisation method

        Parameters
        ----------
        pdf_file : pathlib.Path
            The path to the PDF file
        pdf_content : pymupdf.Document
            the reference to the content of the PDF as parsed by
            pymupdf
        pdf_metadata : dict[str, str], optional
            The metadata contained in the PDF file
        title : str, optional
            the title of the PDF (None, if not defined)
        authors : list[Person], optional
            The list of authors (None if not available - e.g., during
            the submission process)

        """

        super().__init__(str(pdf_file.resolve()))
        self._pdf_file: pathlib.Path = pdf_file
        self._content = pdf_content
        self._metadata = pdf_metadata
        self._title = title
        self._authors = authors

    @property
    def content(self) -> pymupdf.Document:
        return self._content

    @property
    def metadata(self) -> dict[str, str] | None:
        return self._metadata

    @property
    def title(self) -> str | None:
        return self._title

    @property
    def authors(self) -> list[Person] | None:
        return self._authors

    def __repr__(self) -> str:
        """Get a string representation of the PDF object

        Returns
        -------
        str
            The string representation of the PDF object
        """
        return str(self._metadata)

    def __str__(self) -> str:
        """Get a string representation of the PDF object

        Returns
        -------
        str
            The string representation of the PDF object
        """
        if self._authors is not None:
            authors = f"({', '.join([str(s) for s in self._authors])})"
            return f"{self._title} {authors}"
        elif self.title is not None:
            return self.title
        else:
            return super().__str__()
