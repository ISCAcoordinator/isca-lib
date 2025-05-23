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
        presenters: list[Person] = [],
        reviewers: list[Person] = [],
        alternative_affiliations: dict[Person, Affiliation] = dict(),
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
        self.presenters: list[Person] = presenters
        self.reviewers: list[Person] = reviewers
        self.alternative_affiliations: dict[Person, Affiliation] = alternative_affiliations

    @property
    def id(self) -> str:
        return self.title

class Session:
    def __init__(self, id: str, name: str, chairs: list[Person]=[], papers: list[Paper]=[]):
        self.id = id
        self.name = name
        self.chairs = chairs
        self.papers = papers

class Conference:
    def __init__(self, conf_id: str, serie: str, start_date: str, end_date: str, chairs: list[Person]):
        self.serie: str = serie
        self.start_date = start_date
        self.end_date = end_date
        self.chairs: list[Person] = chairs
        self._papers: dict[str, Paper] = dict()

    def add_paper(self, paper: Paper, force_replace=True):
        if (paper.id in self._papers) and (not force_replace):
            raise ValueError(f'The paper"{paper.id}" is already in the ')
        self._papers[paper.id] = paper

    def remove_paper(self, paper_id: str) -> Paper:
        if paper_id not in self._papers:
            print(f'The paper "{paper_id}" is not part of this conference')
        paper = self._papers[paper_id]
        return paper

    def get_paper(self, paper_id: str) -> Paper:
        if paper_id not in self._papers:
            raise KeyError(f'The paper "{paper_id}" is not part of this conference')
        return self._papers[paper_id]

    def update_paper(self, paper: Paper):
        self.add_paper(paper, force_replace=True)

    @property
    def papers(self) -> dict[str, Paper]:
        return self._papers.copy()
