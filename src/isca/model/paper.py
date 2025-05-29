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
        self.title: str = title
        self.authors: list[Person] = authors
        self.abstract = abstract
        self.pdf_file: pathlib.Path | None = (
            pathlib.Path(pdf_file) if (pdf_file is not None) and isinstance(pdf_file, str) else pdf_file
        )
        self.presenters: list[Person] = presenters if presenters is not None else []
        self.reviewers: list[Person] = reviewers if reviewers is not None else []
        self.alternative_affiliations: dict[Person, Affiliation] = (
            alternative_affiliations if alternative_affiliations is not None else dict()
        )

        self._id: str | None = id

    @property
    def id(self) -> str:
        if self._id is None:
            return self.title
        else:
            return self._id

    def __str__(self):
        paper = f"[{self.id}] {self.title}\n"
        print(self.authors)
        for author in self.authors:
            paper += f"  - {author}\n"

        return paper
