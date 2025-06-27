import logging
import pathlib

from .person import Affiliation, Person


class Paper:
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
    presenters: list[Person]
        The presenters of the paper at the given conference [default: empty list]
    reviewers: list[Person]
        The reviewers of the paper for the given conference [default: empty list]
    alternative_affiliations: dict[Person, Affiliation]
        The alternative affiliations of some authors.[default: empty dictionnary]

    """

    def __init__(
        self,
        title: str,
        authors: list[Person],
        abstract: str | None = None,
        pdf_file: pathlib.Path | str | None = None,
        presenters: list[Person] | None = None,
        reviewers: list[Person] | None = None,
        alternative_affiliations: dict[Person, Affiliation] | None = None,
        track: str | None = None,
        metadata_from_pdf: bool = False,
        id: str | None = None,
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
        presenters : list[Person], optional
            The list of presenters [default: empty list]
        reviewers : list[Person], optional
            The list of reviewers [default: empty list]
        alternative_affiliations : dict[Person, Affiliation], optional
            The alternative affiliations for the authors of the paper [default: empty dict]
        """
        self._logger = logging.getLogger(self.__class__.__name__)
        self.title: str = title
        self.authors: list[Person] = authors
        self.abstract = abstract
        self._pdf_file: pathlib.Path | None = None
        self.presenters: list[Person] = presenters if presenters is not None else []
        self.reviewers: list[Person] = reviewers if reviewers is not None else []
        self.alternative_affiliations: dict[Person, Affiliation] = (
            alternative_affiliations if alternative_affiliations is not None else dict()
        )
        self.metadata_from_pdf: bool = metadata_from_pdf
        self.track: str | None = track

        self._id: str | None = id

        self.pdf_file = pdf_file


    @property
    def id(self) -> str:
        if self._id is None:
            return self.title
        else:
            return self._id

    @property
    def pdf_file(self) -> pathlib.Path | None:
        return self._pdf_file

    @pdf_file.setter
    def pdf_file(self, pdf_file: pathlib.Path | str | None):

        # Just make sure the PDF exists
        if (pdf_file is not None) and isinstance(pdf_file, str):
            pdf_file = pathlib.Path(pdf_file)

        if (pdf_file is not None) and (not pdf_file.exists()):
            self._logger.warning(f"[{self.id}] The given PDF file doesn't exist, revert to None: {pdf_file}")
            pdf_file = None

        self._pdf_file = pdf_file

    def __str__(self):
        paper = f"[{self.id}] {self.title}\n"
        print(self.authors)
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
        author_area_label: str | None = None
    ):
        super().__init__(title, authors, abstract, pdf_file, None, None, dict(), id)

        self.original_id:  str | None  = original_id
        self.page_count:  int | None  = page_count
        self.order:  int | None  = order
        self.start_page:  int | None  = start_page
        self.end_page:  int | None  = end_page
        self.doi:  str | None  = doi
        self.author_area_id:  str | None  = author_area_id
        self.author_area_label:  str | None  = author_area_label

class SurveyTalk:
    def __init__(
        self,
        id: str,
        title: str,
        abstract: str | None = None,
        presenters: list[Person] | None = None,
    ):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._id = id
        self.title: str = title
        self.abstract = abstract
        self.presenters: list[Person] = presenters if presenters is not None else []

    @property
    def id(self) -> str:
        return self._id

    def __str__(self):
        talk_info = f"[{self.id}] {self.title}\n"
        for presenter in self.presenters:
            talk_info += f"  - {presenter}\n"

        return talk_info
