"""This module provides the base elements manipulated by any ISCA event"""

import pathlib

from .core import ISCAItem
from .person import Person


class Paper(ISCAItem):
    """Class representing a paper

    The paper is not necessarily a published abstract. It can be at the reviewing stage.
    However, it is expected to be associated to an event.
    This expectation is not enforced to allow the developper to process the paper before associating it to the event.

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
        self._pdf_file: pathlib.Path | None = pathlib.Path(pdf_file) if pdf_file is not None else None
        self.reviewers: list[Person] = reviewers if reviewers is not None else []
        self.metadata_from_pdf: bool = metadata_from_pdf
        self.track: str | None = track
        self.resource: str | None = resource
        self._id: str | None = id

    @property
    def authors(self) -> list[Person]:
        """Get the authors of the paper(readonly)

        Returns
        -------
        list[Person]
            The list of authors of the paper

        """

        return self._authors

    @authors.setter
    def authors(self, authors: list[Person]):
        """Set the list of authors of the paper

        Parameters
        ----------
        authors : list[Person]
            The list of authors of the paper
        """
        self._authors = authors

    @property
    def pdf_file(self) -> pathlib.Path | None:
        """Get the path to the PDF file of the paper

        Returns
        -------
        pathlib.Path | None
            The path to the PDF file if there is one, else None

        """
        return self._pdf_file

    @pdf_file.setter
    def pdf_file(self, pdf_file: pathlib.Path | str):
        """Associate a PDF file to the paper

        Parameters
        ----------
        pdf_file : pathlib.Path | str
            the path to the PDF file

        """

        # Just make sure the PDF exists
        if isinstance(pdf_file, str):
            pdf_file = pathlib.Path(pdf_file)

        if not pdf_file.exists():
            raise FileNotFoundError(f"[{self.id}] The given PDF file doesn't exist: {pdf_file}")

        self._pdf_file = pdf_file

    def replace_author(self, current_author: Person | int, new_author: Person) -> Person:
        """Replace one author of the paper by a new one

        Parameters
        ----------
        current_author : Person | int
            The author to be replaced
        new_author : Person
            The new author replacing the previous one

        Returns
        -------
        Person
            The replaced author

        Raises
        ------
        Exception
            if the author to be replaced doesn't exist
        """

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

        return current_author

    def __repr__(self) -> str:
        """Get a string representation of the paper

        Returns
        -------
        str
            The string representation of the paper
        """
        paper = f"[{self.id}] {self.title}\n"
        for author in self.authors:
            paper += f"  - {author}\n"

        return paper

    def __str__(self) -> str:
        """Get a string representation of the paper

        Returns
        -------
        str
            The string representation of the paper
        """
        return repr(self)


class PublishedPaper(Paper):
    """Class representing a paper which is published in the ISCA Archive

    Attributes
    ----------
    original_id: str
        The original identifier of the paper (it can come fro CMT, ..)
    order: int
    first_page: int
        The first page of the paper
    last_page: int
        The last page of the paper
    doi: str, optional
        The DOI of the paper, if it exists
    author_area_id: int, optional
        The primary area ID of the paper as defined by the author
    author_area_label: str, optional
        The primary area label of the paper as defined by author
    """

    def __init__(
        self,
        id: str,
        title: str,
        authors: list[Person],
        abstract: str | None,
        pdf_file: pathlib.Path | str | None,
        original_id: str,
        order: int,
        first_page: int,
        last_page: int,
        doi: str | None = None,
        author_area_id: int | None = None,
        author_area_label: str | None = None,
    ):
        """Initialisation method

        Parameters
        ----------
        id : str
            The identifier of the paper (as stored in the ISCA
            Archive)
        title : str
            the title of the paper
        authors : list[Person]
            the authors of the paper
        abstract : str, optional
            the abstract associated to the paper [optional, but
            preferred to a PDF if possible]
        pdf_file : pathlib.Path | str, optional
            the PDF file associated to the paper
        original_id : str, optional
            the original identifier of the paper as provided by the
            publication chairs
        order : int, optional
            ???
        first_page : int, optional
            the first page of the paper
        last_page : int, optional
            the last page f the paper
        doi : str, optional
            the DOI of the paper if available
        author_area_id : int, optional
            the ID of the primary area as defined by the authors
        author_area_label : str, optional
            the label of the primary area as defined by the authors

        """
        super().__init__(id, title, authors, abstract, pdf_file)

        self.original_id: str | None = original_id
        self.order: int | None = order
        self.first_page: int | None = first_page
        self.last_page: int | None = last_page
        self.doi: str | None = doi
        self.author_area_id: int | None = author_area_id
        self.author_area_label: str | None = author_area_label


class Session(ISCAItem):
    """Class representing a session of an event

    Attributes
    ----------
    id: str
        The identifier of the session
    name: str
        The name of the session
    """

    def __init__(self, id: str, name: str):
        """Initialisation method

        Parameters
        ----------
        id : str
            The identifier of the session
        name : str
            The name of the session
        """
        super().__init__(id)
        self.name = name

    def sort_criterion(self) -> str:
        """Use the identifier as a sorting criterion

        FIXME: where is this method used?
        Returns
        -------
        str
            the value of the identifier
        """
        return self.id

    def __repr__(self) -> str:
        """Get a string representation of a session

        Returns
        -------
        str
            The string representation of the session
        """
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def str(self) -> str:
        """Get a string representation of a session

        Returns
        -------
        str
            The string representation of the session
        """
        return self.__repr__()


class ScientificSession(Session):
    """Class representing a scientific session

    A scientific session is a session with associated papers

    Attributes
    ----------
    papers:
        The list of the papers of the session
    """

    def __init__(self, id: str, name: str, papers: list[Paper] | None = None):
        """Initialisation method

        Parameters
        ----------
        id : str
            The identifier of the session
        name : str
            The name of the session
        papers : list[Paper], optional
            The papers associated to the session, None if papers are
            added later
        """
        super().__init__(id, name)
        self._papers: list[Paper] = papers if papers is not None else []

    @property
    def papers(self) -> list[Paper]:
        """Get a reference to the list of the papers of the session

        Returns
        -------
        list[Paper]
            The reference to the list of the papers of the session
        """
        return self._papers
