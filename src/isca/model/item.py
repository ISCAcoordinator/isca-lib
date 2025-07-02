import logging
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
        alternative_affiliations: dict[Person, Affiliation] | None = None,
        track: str | None = None,
        metadata_from_pdf: bool = False,
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
        alternative_affiliations : dict[Person, Affiliation], optional
            The alternative affiliations for the authors of the paper [default: empty dict]
        """
        super().__init__(id)

        self.title: str = title
        self.authors: list[Person] = authors
        self.abstract = abstract
        self._pdf_file: pathlib.Path | None = None
        self.reviewers: list[Person] = reviewers if reviewers is not None else []
        self.alternative_affiliations: dict[Person, Affiliation] = (
            alternative_affiliations if alternative_affiliations is not None else dict()
        )
        self.metadata_from_pdf: bool = metadata_from_pdf
        self.track: str | None = track

        self._id: str | None = id

        self.pdf_file = pdf_file

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


class Presentation(ISCAItem):
    def __init__(
        self,
        id: str,
        title: str,
        presenters: list[Person] | None,
        duration: int | None,
        abstract: str | None = None,
        presented_paper: Paper | None = None,
    ):
        super().__init__(id)

        self.title: str = title
        self.presenters: list[Person] | None = presenters
        self.abstract: str | None = abstract
        self._duration: int | None = duration
        self._presented_paper: Paper | None = presented_paper

    @property
    def duration(self) -> int | None:
        return self._duration

    @property
    def presented_paper(self) -> Paper | None:
        return self._presented_paper

    def __str__(self):
        talk_info = f"[{self.id}] {self.title}\n"
        if self.presenters is not None:
            for presenter in self.presenters:
                talk_info += f"  - {presenter}\n"

        return talk_info


class OralPresentation(Presentation):
    def __init__(
        self,
        id: str,
        title: str,
        presenters: list[Person] | None,
        duration: int,
        abstract: str | None = None,
        presented_paper: Paper | None = None,
    ):
        super().__init__(id, title, presenters, duration, abstract, presented_paper)

    @property
    def duration(self) -> int:
        assert self._duration is not None
        return self._duration


class PosterPresentation(Presentation):
    def __init__(
        self,
        id: str,
        title: str,
        presenters: list[Person] | None,
        abstract: str | None = None,
        presented_paper: Paper | None = None,
    ):
        super().__init__(id, title, presenters, None, abstract, presented_paper)

class SurveyTalk(OralPresentation):
    def __init__(
        self,
        id: str,
        title: str,
        presenters: list[Person] | None,
        duration: int,
        abstract: str | None = None,
    ):
        super().__init__(id, title, presenters, duration, abstract, None)

class SpecialPresentation(Presentation):
    def __init__(
        self,
        id: str,
        title: str,
        presenters: list[Person] | None,
        abstract: str | None = None,
        presented_paper: Paper | None = None,
    ):
        super().__init__(id, title, presenters, None, abstract, presented_paper)

class ShowAndTellPresentation(Presentation):
    def __init__(
        self,
        id: str,
        title: str,
        presenters: list[Person] | None,
        abstract: str | None = None,
        presented_paper: Paper | None = None,
    ):
        super().__init__(id, title, presenters, None, abstract, presented_paper)
