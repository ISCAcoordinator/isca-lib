from typing import Iterator
from enum import Enum
from unidecode import unidecode
import logging
import pandas as pd


class Affiliation:
    """An affiliation to be associated to a person

    Attributes
    ----------
    department: str, optional
        The name of the department (if no department, None)
    institute: str
        The name of the institute
    country: str
        The country of the institute
    """

    def __init__(self, institute: str, country: str | None = None, department: str | None = None):
        """Initialisation method

        Parameters
        ----------
        institute : str
            The name of the institute
        country : str, optional
            The country of the institute
        department : str, optional
            The name of the department, if any, else None [default: None]
        """

        self.department: str | None = department
        self.country: str | None = country
        self.institute: str = institute

    def __str__(self) -> str:
        list_elts = []
        if self.department is not None:
            list_elts.append("[" + self.department + "]")
        list_elts.append(self.institute)
        if self.country is not None:
            list_elts.append("{" + self.country + "}")

        return ", ".join(list_elts)

    def short_str(self) -> str:
        return self.institute

    def to_serie(self) -> pd.Series:
        return pd.Series({"departement": self.department, "institute": self.institute, "country": self.country})

    @classmethod
    def from_serie(
        cls, serie: pd.Series
    ) -> "Affiliation":  # NOTE: typing return is a string until we move toward python 3.14
        department = str(serie["department"]) if "department" in serie else None
        institute = str(serie["institute"])
        country = str(serie["country"]) if "country" in serie else None

        return Affiliation(institute, country, department)


class Role(Enum):
    """Enumeration to explicitely address roles"""

    DEFAULT = 0
    AUTHOR = 1
    PRESENTER = 2
    REVIEWER = 3
    META_REVIEWER = 4
    SENIOR_META_REVIEWER = 5
    TRACK_CHAIR = 6
    CHAIR = 7
    PROCEEDING_EDITOR = 8
    SETTING_READER = 9

    def __str__(self) -> str:
        """Return the string representation of the role

        Returns
        -------
        str
            the (uppercase) name of the role
        """
        return f'{self.name.replace("Role.", "")}'


class Person:
    """An affiliation to be associated to a person

    Attributes
    ----------
    firstname: str
        The first name of the person
    lastname: str
        The last name of the person
    email: str
        The email address of the person
    affiliation: Affiliation, optional
        The current affiliation of the person
    _id: str
        The identifier of the person [private attribute, should not be accessed directly, please use self.id instead]
    """

    _counter: int = 0
    ROLE_SEP: str = ";"

    def __init__(
        self,
        firstname: str | None,
        lastname: str,
        main_affiliation: Affiliation,
        email: str | None = None,
        roles: set[Role] = set([Role.DEFAULT]),
        alternative_affiliations: dict[Affiliation, set[str]] | None = None,
        middle_initial: str | None = None,
        id: str | None = None,
    ):
        """Initialisation method

        The email is not used as an identifier as it can change if the person changes institutes.
        An identifier will be automatically generated and can be accessed via the property `self.id`

        Parameters
        ----------
        firstname : str or None
            The first name of the person (set to none if mono-name)
        lastname : str
            The last name of the person
        email : str, optional
            The current email of the person (None if no email) [default: None]
        affiliation : Affiliation, optional
            The current affiliation of the person (None if no affiliation) [default: None]
        id: str, optional
            A given identifier for the person. This field should only be used for serialisation purposes!
        """
        self._logger = logging.getLogger(self.__class__.__name__)
        self.firstname: str | None = firstname
        self.lastname: str = lastname
        self.main_affiliation: Affiliation = main_affiliation
        self.middle_initial: str | None = middle_initial
        self._roles: set[Role] = roles
        self.email: str | None = email
        self.alternative_affiliations: dict[Affiliation, set[str]] = (
            alternative_affiliations if alternative_affiliations is not None else dict()
        )

        self._id: str = self._generate_id() if id is None else id

    def get_organization(self, paper_id: int = -1) -> str:
        """Helper to get the organisation of the user

        The organisation could be paper specific. Therefore, one user can have multiple organisations.
        Parameters
        ----------
        self: type
            description
        paper_id: int
            The paper identifier. If -1, then use the default organisation

        Returns
        -------
        str:
            The organisation
        """
        raise NotImplementedError("This method is not yet implemented")

    def str_with_organization(self, paper_id: int = -1) -> str:
        """Get string version of the user with its organisation.

        A user can have multiple organisations, so the paper ID can be used to specify the organisation of which paper is needed.

        Parameters
        ----------
        self: type
            description
        paper_id: int
            The paper identifiier. If -1, then use the default organisation

        Returns
        -------
        str
            The string version of the User including its organisation
        """
        raise NotImplementedError("This method is not yet implemented")

    def add_role(self, role: Role) -> None:
        """Add a given role to the current user

        Parameters
        ----------
        role: Role
            The role to add to the current User
        """
        self._roles.add(role)

    def validate_roles(self, roles: set[Role]) -> set[Role]:
        """Check if the current User validate a given set of roles

        Parameters
        ----------
        roles: set[Role]
            The set of roles to validate

        Returns
        -------
        set[Role]
            The subset of roles which are taken by the current User
        """
        return self._roles.intersection(roles)

    def str_last_name(self) -> str:
        """Generate a string version of the User's name formatted as "<Last Name>, <First Name>"

        Returns
        -------
        str
            The string version with the last name coming first
        """
        first = self.firstname
        last = self.lastname
        if not first:
            return last

        author_name = f"{last}, {first}"
        if self.middle_initial is not None:
            author_name += " " + self.middle_initial

        return author_name

    def str_sorting_by_last_name(self) -> str:
        """Generate a string version of the current User to be used to sort users by their last names.

        Returns
        -------
        str
            The string version of the current User
        """
        s = self.str_last_name()
        s = unidecode(s.lower())
        return s

    def _generate_id(self) -> str:
        Person._counter += 1
        return str(Person._counter)

    def str_with_flatten_affiliations(self, paper_id: str, short=False) -> str:
        str_person = str(self)
        affiliations = []
        if short:
            affiliations.append(self.main_affiliation.institute)
        else:
            affiliations.append(str(self.main_affiliation))
        for affiliation, papers in self.alternative_affiliations.items():
            if paper_id in papers:
                if short:
                    affiliation = affiliation.institute
                else:
                    affiliation = str(affiliation)
                affiliations.append(affiliation)
        str_person += f" ({'; '.join(affiliations)})"

        return str_person

    def add_alternative_affiliation(self, affiliation: Affiliation, paper_id: str):
        if affiliation not in self.alternative_affiliations:
            self.alternative_affiliations[affiliation] = set()
        self.alternative_affiliations[affiliation].add(paper_id)

    @property
    def id(self) -> str:
        return self._id

    def __hash__(self) -> int:
        """Hashing method which hashes the email to identify the user

        Returns
        -------
        int
            hash(self._id)
        """
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Person(id={self.id}, first_name={self.firstname}, middle_initial={self.middle_initial}, last_name={self.lastname}, email={self.email}, affiliation=[{self.main_affiliation}]), roles=({self._roles})"

    def __str__(self) -> str:
        last_name = self.lastname
        if " " in last_name:
            last_name = f"{{{last_name}}}"

        if not self.firstname:
            return last_name

        if self.middle_initial is not None:
            user_str = f"{self.firstname} {self.middle_initial} {last_name}"
        else:
            user_str = f"{self.firstname} {last_name}"

        return user_str

    def __eq__(self, other) -> bool:
        if not isinstance(other, Person):
            return False

        if self.id == other.id:
            return True
        elif self.email == other.email:
            return True

        if self.firstname != other.firstname:
            return False
        elif self.lastname != other.lastname:
            return False

        # Check affiliations as it can be a bit tricky here
        if self.main_affiliation in other.alternative_affiliations:
            return True
        elif self.main_affiliation in self.alternative_affiliations:
            return True
        elif set(self.alternative_affiliations.keys()).intersection(set(other.alternative_affiliations.keys())):
            return True

        return False


class Annuary:
    def __init__(self):
        self._annuary: set[Person] = set()
        self._email_annuary: dict[str, Person] = dict()

    def add(self, person: Person):
        if (person.email is not None) and (self.find_person_by_email(person.email) is not None):
            return
        if person not in self._annuary:
            self._annuary.add(person)

        if person.email is not None:
            self._email_annuary[person.email] = person

    def update(self, other: "Annuary"):
        for person in other._annuary:
            self._annuary.add(person)

    def find_person_by_email(self, email: str) -> Person | None:
        if email not in self._email_annuary:
            return None
        return self._email_annuary[email]

    def find_person_by_id(self, id: str) -> Person | None:
        raise NotImplementedError("This method is not yet implemented")

    def find_person_by_name(self, firstname: str, lastname: str, middle_initial: str | None=None) -> set[Person]:
        set_person = set()
        for person in self._annuary:
            if (person.firstname != firstname) or (person.lastname != lastname):
                continue

            if (middle_initial is not None) and (person.middle_initial != middle_initial):
                continue

            set_person.add(person)

        return set_person

    def __repr__(self) -> str:
        output = ""
        for person in self._annuary:
            output += f"- {repr(person)}\n"
        return output

    def __str__(self) -> str:
        output = ""
        for person in self._annuary:
            output += f"- {person}\n"
        return output

    def __iter__(self) -> Iterator[Person]:
        return iter(self._annuary)
