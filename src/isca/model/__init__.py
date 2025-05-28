from .person import Person
from .event import Conference
from .paper import Paper

class ISCADataBase:
    def __init__(self):
        self._conferences: dict[str, Conference] = {}
        self._annuary: dict[str, Person] = {}
        self._papers: dict[str, Paper] = {}

    def add_conference(self, conference: Conference):
        for paper_id, paper in conference.papers.items():
            self._papers[paper_id] = paper
            for author in paper.authors:
                self._annuary[author.id] = author

    def add_person(self, person: Person):
        self._annuary[person.id] = person

    # def add_paper(self, paper: Paper):
    #     self.__ap
