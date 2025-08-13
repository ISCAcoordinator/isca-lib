import pathlib

from .core import ISCAItem
from .person import Affiliation, Person


class Paper(ISCAItem):
    """A paper part of the ISCA process

    The paper is not necessarily a published abstract. It can be in a
    review stage. However, it is required to be associated to an event

    Attributes
    ----------
    title: str
        The title of the paper
    authors: list[Person]
        The authors of the paper
    abstract: str, optional
        The abstract of the paper (no abstract if None) [default: None]
    pdf_file: pahtlib.Path | str, optional
        The path to the PDF file (no corresponding file if None) [default: None]
    reviewers: list[Person]
        The reviewers of the paper for the given conference [default: empty list]
    alternative_affiliations: dict[Person, Affiliation]
        The alternative affiliations of some authors.[default: empty dictionnary]

    """

    def __init__(
        self,
        id: str,
        title: str,
        authors: list[Person],
        abstract: str | None = None,
        pdf_file: pathlib.Path | str | None = None,
        reviewers: list[Person] | None = None,
        track: str | None = None,
        metadata_from_pdf: bool = False,
        resource: str | None = None,
    ):
        """Initialisation method

        Parameters
        ----------
        title : str
            The identifier of the paper
        authors : list[Person]
            The authors of the paper
        abstract : str, optional
            The abstract of the paper (None, if no abstract) [default: None]
        pdf_file : pathlib.Path | str, optional
            The path to the PDF file of the paper (None, if not PDF) [default: None]
        reviewers : list[Person], optional
            The list of reviewers [default: empty list]
        """
        super().__init__(id)

        self.title: str = title
        self._authors: list[Person] = authors
        self.abstract = abstract.strip() if abstract is not None else None
        self._pdf_file: pathlib.Path | None = None
        self.reviewers: list[Person] = reviewers if reviewers is not None else []
        self.metadata_from_pdf: bool = metadata_from_pdf
        self.track: str | None = track
        self.resource: str | None = resource
        self._id: str | None = id

        self.pdf_file = pdf_file

    @property
    def authors(self) -> list[Person]:
        return self._authors

    @property
    def pdf_file(self) -> pathlib.Path | None:
        return self._pdf_file

    @pdf_file.setter
    def pdf_file(self, pdf_file: pathlib.Path | str | None):

        # Just make sure the PDF exists
        if (pdf_file is not None) and isinstance(pdf_file, str):
            pdf_file = pathlib.Path(pdf_file)

        if (pdf_file is not None) and (not pdf_file.exists()):
            self.logger.warning(f"[{self.id}] The given PDF file doesn't exist, revert to None: {pdf_file}")
            pdf_file = None

        self._pdf_file = pdf_file

    def replace_authors(self, authors: list[Person]):
        self._authors = authors

    def replace_author(self, current_author: Person | int, new_author: Person):

        # Ensure the provided person is an actual author
        if isinstance(current_author, Person):
            idx_author = self.authors.index(current_author)
            if idx_author < 0:
                raise Exception(f'The wanted person "{current_author}" is not an author of the paper "{self.id}"')
        else:
            if current_author >= len(self._authors):
                raise Exception(
                    f'"{self.id}" only have {len(self._authors)} authors and author index {current_author} has been asked'
                )
            idx_author = current_author

        # Replace the actual author in the list of authors
        current_author = self._authors[idx_author]
        self._authors[idx_author] = new_author

    def __str__(self):
        paper = f"[{self.id}] {self.title}\n"
        for author in self.authors:
            paper += f"  - {author}\n"

        return paper


class PublishedPaper(Paper):
    def __init__(
        self,
        id: str,
        title: str,
        authors: list[Person],
        abstract: str | None = None,
        pdf_file: pathlib.Path | str | None = None,
        original_id: str | None = None,
        page_count: int | None = None,
        order: int | None = None,
        start_page: int | None = None,
        end_page: int | None = None,
        doi: str | None = None,
        author_area_id: str | None = None,
        author_area_label: str | None = None,
    ):
        super().__init__(id, title, authors, abstract, pdf_file, None, dict())

        self.original_id: str | None = original_id
        self.page_count: int | None = page_count
        self.order: int | None = order
        self.start_page: int | None = start_page
        self.end_page: int | None = end_page
        self.doi: str | None = doi
        self.author_area_id: str | None = author_area_id
        self.author_area_label: str | None = author_area_label


class Session(ISCAItem):
    def __init__(self, id: str, name: str):
        super().__init__(id)
        self.name = name

    def sort_criterion(self) -> str:
        return self.id

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def str(self) -> str:
        return self.__repr__()


class ScientificSession(Session):
    def __init__(self, id: str, name: str, papers: list[Paper] | None = []):
        super().__init__(id, name)
        self._papers: list[Paper] = papers if papers is not None else []

    @property
    def papers(self) -> list[Paper]:
        return self._papers
