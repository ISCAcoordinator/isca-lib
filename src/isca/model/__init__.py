from .person import Person
from .event import Conference

class ISCADataBase:
    def __init__(self):
        self.conferences: dict[str, Conference] = {}
        self.annuary: set[Person] = set()

    def add_conference(self, conference: Conference):
        for _, paper in conference.papers.items():
            for author in paper.authors:
                self.annuary.add(author)

    def add_person(self, person: Person):
        self.annuary.add(person)
