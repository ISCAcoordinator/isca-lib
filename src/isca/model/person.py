from typing import Iterator
from typing_extensions import Callable

from enum import Enum
import pathlib
from unidecode import unidecode

import pandas as pd


from .core import ISCAItem, ISCAObject


class Affiliation:
    """An affiliation to be associated to a person

    Attributes
    ----------
    short: str
        The short name of the affiliation
    long: str, optional
        The long name of the affiliation
    country: str, optional
        The country of the institute
    """

    def __init__(self, short: str, long: str | None = None, country: str | None = None):
        """Initialisation method

        Parameters
        ----------
        short: str
            The short name of the affiliation
        long: str, optional
            The long name of the affiliation
        country: str, optional
            The country of the institute
        """

        self.short: str = short
        self.long: str | None = long
        self.country: str | None = country

    def __repr__(self) -> str:
        """Get a string representation of the affiliation

        Returns
        -------
        str
            The string representation of the affiliation
        """
        list_elts = [self.short]
        if self.long is not None:
            list_elts.append("[" + self.long + "]")
        if self.country is not None:
            list_elts.append("{" + self.country + "}")

        return ", ".join(list_elts)

    def __str__(self) -> str:
        """Get a string representation of the affiliation

        Returns
        -------
        str
            The string representation of the affiliation
        """
        list_elts = []
        if self.short is not None:
            list_elts.append(self.short)
        list_elts.append(self.long)
        if self.country is not None:
            list_elts.append(self.country)

        return ", ".join(list_elts)

    def to_serie(self) -> pd.Series:
        """Helper to convert the class to a pandas Serie(s)

        Returns
        -------
        pd.Series
            the pandas Serie representation of the affiliation
        """

        return pd.Series({"short": self.short, "long": self.long, "country": self.country})

    @classmethod
    def from_serie(cls, serie: pd.Series) -> "Affiliation":
        """Helper to create an affiliation from a pandas Serie(s)

        Parameters
        ----------
        serie : pd.Series
            The pandas Serie(s) to be converted to an Affiliation

        Returns
        -------
        Affiliation:
            The resulting Affiliation object

        """
        short = str(serie["short"])
        long = str(serie["long"]) if "long" in serie else None
        country = str(serie["country"]) if "country" in serie else None

        return Affiliation(short, long, country)


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
    SESSION_CHAIR = 10

    def __str__(self) -> str:
        """Return the string representation of the role

        Returns
        -------
        str
            the (uppercase) name of the role
        """
        return f'{self.name.replace("Role.", "")}'


class Person(ISCAItem):
    """An affiliation to be associated to a person

    Class Attributes
    ----------------
    counter: int
        The counter used to generate an automatic ID
    ROLE_SEP: str
        The separator used

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
        id: str | None,
        firstname: str | None,
        lastname: str,
        default_affiliation: Affiliation | None = None,
        email: str | None = None,
        roles: set[Role] = set([Role.DEFAULT]),
        paper_affiliations: dict[str, list[Affiliation]] | None = None,
        middle_initial: str | None = None,
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
        super().__init__(self._generate_id() if id is None else id)
        self.firstname: str | None = firstname.strip() if firstname is not None else None
        self.lastname: str = lastname.strip()
        self.default_affiliation: Affiliation = default_affiliation
        self.middle_initial: str | None = middle_initial if (middle_initial is not None) and middle_initial.strip() else None
        self._roles: set[Role] = roles
        self.email: str | None = email.lower().strip() if email is not None else None
        self.paper_affiliations: dict[str, list[Affiliation]] = paper_affiliations if paper_affiliations is not None else dict()

        # # Other refinement
        # if (self.firstname is not None) and (self.firstname.isupper() or self.firstname.islower()):
        #     self.firstname = self.firstname.title()

        # if (self.lastname is not None) and (self.lastname.isupper() or self.lastname.islower()):
        #     self.lastname = self.lastname.title()

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
        if (first is None) or (not first):
            return last

        author_name = f"{last}, {first}"
        if self.middle_initial is not None:
            author_name += " " + self.middle_initial

        return author_name

    @property
    def roles(self) -> set[Role]:
        return self._roles.copy()

    @property
    def name(self) -> str:
        first = self.firstname
        last = self.lastname
        if not first:
            return last

        name = first
        if self.middle_initial is not None:
            name += " " + self.middle_initial
        return name + " " + last

    @property
    def isca_name(self) -> str:
        first = self.firstname
        last = self.lastname
        if not first:
            return last

        name = first
        if self.middle_initial is not None:
            name += " " + self.middle_initial
        return name + " {" + last + "}"

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

    def str_with_flatten_affiliations(self, paper_id: str | None = None, short=False, markers=False) -> str:
        if markers:
            str_person = self.isca_name
        else:
            str_person = str(self)

        affiliations = []
        if (paper_id is None) or (paper_id not in self.paper_affiliations):
            if short:
                aff = self.default_affiliation.long
                if self.default_affiliation.country is not None:
                    if markers:
                        aff += f", {{{self.default_affiliation.country}}}"
                    else:
                        aff += f", {self.default_affiliation.country}"
                affiliations.append(aff)
            elif markers:
                affiliations.append(repr(self.default_affiliation))
            else:
                affiliations.append(str(self.default_affiliation))
        else:
            for affiliation in self.paper_affiliations[paper_id]:
                if short:
                    aff = affiliation.long
                    if affiliation.country is not None:
                        if markers:
                            aff += f", {{{affiliation.country}}}"
                        else:
                            aff += f", {affiliation.country}"
                    affiliation = aff
                elif markers:
                    affiliation = repr(affiliation)
                else:
                    affiliation = str(affiliation)

                if affiliation not in affiliations:
                    affiliations.append(affiliation)
        str_person += f" ({'; '.join(affiliations)})"

        return str_person

    def str_affiliations(self, short=False, markers=False) -> str:
        affiliations = set()
        if not self.paper_affiliations:
            # Add the default affiliation
            if short:
                affiliation = self.default_affiliation.long
            elif markers:
                affiliation = repr(self.default_affiliation)
            else:
                affiliation = str(self.default_affiliation)

            affiliations.add(affiliation)
        else:
            # add all the potentiation affiliations
            for affiliation_list in self.paper_affiliations.values():
                for affiliation in affiliation_list:
                    if short:
                        affiliation = affiliation.long
                    elif markers:
                        affiliation = repr(affiliation)
                    else:
                        affiliation = str(affiliation)

                    affiliations.add(affiliation)

        return "; ".join(affiliations)

    def add_paper_affiliation(self, paper_id: str, affiliation: Affiliation):
        if paper_id not in self.paper_affiliations:
            self.paper_affiliations[paper_id] = list()
        self.paper_affiliations[paper_id].append(affiliation)

    @property
    def id(self) -> str:
        return self._id

    def _generate_id(self) -> str:
        Person._counter += 1
        return str(Person._counter)

    def __hash__(self) -> int:
        """Hashing method which hashes the email to identify the user

        Returns
        -------
        int
            hash(self._id)
        """
        return hash(self._id)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id}, first_name={self.firstname}, middle_initial={self.middle_initial}, last_name={self.lastname}, email={self.email}, affiliation=[{self.default_affiliation}]), roles=({self._roles})"

    def __str__(self) -> str:
        last_name = self.lastname

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
        if self.default_affiliation in other.paper_affiliations:
            return True
        elif self.default_affiliation in self.paper_affiliations:
            return True
        elif set(self.paper_affiliations.keys()).intersection(set(other.paper_affiliations.keys())):
            return True

        return False


class Speaker(Person):
    def __init__(
        self,
        id: str | None,
        firstname: str | None,
        lastname: str,
        default_affiliation: Affiliation,
        email: str | None = None,
        roles: set[Role] = set([Role.DEFAULT]),
        paper_affiliations: dict[str, list[Affiliation]] | None = None,
        middle_initial: str | None = None,
        biography: str | None = None,
        url: str | None = None,
        photo: pathlib.Path | None = None,
    ):
        super().__init__(id, firstname, lastname, default_affiliation, email, roles, paper_affiliations, middle_initial)
        self.biography: str | None = biography
        self.url: str | None = url
        self.photo: pathlib.Path | None = photo
        self.add_role(Role.PRESENTER)

    @classmethod
    def from_person(cls, person: Person) -> "Speaker":
        speaker = Speaker(
            person.id,
            person.firstname,
            person.lastname,
            person.default_affiliation,
            person.email,
            person.roles,
            person.paper_affiliations,
            person.middle_initial,
        )

        return speaker


class Annuary(ISCAObject):
    def __init__(self, alternative_emails: dict[str, str] | None = None):
        super().__init__()
        self._annuary: dict[int, Person] = dict()
        self._email_annuary: dict[str, Person] = dict()
        self._alternative_emails: dict[str, str] = dict()

        if alternative_emails is not None:
            for alternative_email, reference_email in alternative_emails.items():
                self.add_alternative_email(reference_email, alternative_email)

    @property
    def alternative_emails(self) -> dict[str, str]:
        return self._alternative_emails

    def add_alternative_email(self, reference_email: str, alternative_email: str):
        reference_email = reference_email.strip().lower()
        alternative_email = alternative_email.strip().lower()
        self._alternative_emails[alternative_email] = reference_email

    def get_reference_email(self, alternative_email: str) -> str:
        alternative_email = alternative_email.strip().lower()
        return self._alternative_emails[alternative_email]

    def is_an_alternative_email(self, email: str) -> bool:
        return email.strip().lower() in self._alternative_emails

    def update_alternative_emails(self, alternative_emails: dict[str, str]):
        for alternative_email, reference_email in alternative_emails.items():
            if alternative_email in self._alternative_emails:
                self.logger.info(
                    f"The alternative email <{alternative_email}> already points to <{self._alternative_emails[alternative_email]}> in the current annuary"
                )
            else:
                self.add_alternative_email(reference_email, alternative_email)

    def add(self, person: Person, force: bool = False):
        # Check if person exist
        old_person = None
        if hash(person) in self._annuary:
            old_person = self._annuary[hash(person)]

        elif person.email is not None:
            old_person = self.find_person_by_email(person.email)

        if old_person is not None:
            if not force:
                return

            self.replace(old_person, person)
        else:
            self._annuary[hash(person)] = person
            if person.email is not None:
                self._email_annuary[person.email] = person

    def update(self, other: "Annuary", force: bool = False, ignore_alternative: bool = False):
        for person in other._annuary.values():
            self.add(person, force)

        if not ignore_alternative:
            self.update_alternative_emails(other._alternative_emails)

    def replace(self, old_person: Person, new_person: Person):
        assert old_person.email is not None
        del self._email_annuary[old_person.email]
        del self._annuary[hash(old_person)]

        self.add(new_person)

    def find_person_by_email(self, email: str) -> Person | None:
        email = email.lower().strip()
        if self.is_an_alternative_email(email):
            email = self.get_reference_email(email)

        if email not in self._email_annuary:
            return None
        return self._email_annuary[email]

    def find_person_by_name(
        self, firstname: str, lastname: str, middle_initial: str | None = None, ignore_middle_initial: bool = False
    ) -> set[Person]:
        set_person = set()
        for person in self._annuary.values():
            person_firstname = person.firstname
            if (ignore_middle_initial) and (person.middle_initial is not None):
                person_firstname += f" {person.middle_initial}"

            if (person_firstname != firstname) or (person.lastname != lastname):
                continue

            if ignore_middle_initial:
                continue

            if (middle_initial is not None) and (person.middle_initial != middle_initial):
                continue

            set_person.add(person)

        return set_person

    @property
    def reviewers(self) -> set[Person]:
        reviewers = set()
        for p in self._annuary.values():
            if p.validate_roles(set([Role.REVIEWER])):
                reviewers.add(p)
        return reviewers

    def __repr__(self) -> str:
        output = ""
        for person in self._annuary:
            output += f"- {repr(person)}\n"
        return output

    def __str__(self) -> str:
        output = ""
        for person in self._annuary.values():
            output += f"- {person}\n"
        return output

    def __iter__(self) -> Iterator[Person]:
        return iter(self._annuary)

    def compress(self, select_criterion: Callable[[Person], bool] = lambda x: bool(x.roles)) -> "Annuary":
        annuary = Annuary()
        ignored_counter = 0
        total_counter = len(self._annuary)
        for person in self._annuary.values():
            if select_criterion(person):
                annuary.add(person)
            else:
                ignored_counter += 1
        ratio = ignored_counter / total_counter * 100
        self.logger.info(f"Compression removed {ignored_counter} ({ratio:.2f}%) persons from the annuary")
        return annuary
