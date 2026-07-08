from typing import Iterator, Any
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
        # NOTE: this assert is added to prevent a likely issue during the metadata parsing
        assert short is not None, "Try to create an affiliation with no information to be used"

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
    _id_counter: int
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

    _id_counter: int = 0
    ROLE_SEP: str = ";"

    def __init__(
        self,
        id: str,
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

        Parameters
        ----------
        id: str
            A given identifier for the person. This field should only be used for serialisation purposes!
        firstname : str or None
            The first name of the person (set to None if mono-name)
        lastname : str
            The last name of the person
        default_affiliation : Affiliation, optional
            The default affiliation of the person
        email : str, optional
            The current email of the person
        roles : set[Role]
            The set of roles of the person (chair, author, ....) [default: {Role.DEFAULT}]
        paper_affiliations: dict[str, list[Affiliations]], optional
            The dictionnary associating a list of affiliations to a given paper (ID)
        middle_initial: str, optional
            The middle initial of the name of the Person
        """
        super().__init__(id)
        self.firstname: str | None = firstname.strip() if firstname is not None else None
        self.lastname: str = lastname.strip()
        self.default_affiliation: Affiliation | None = default_affiliation
        self.middle_initial: str | None = middle_initial if (middle_initial is not None) and middle_initial.strip() else None
        self._roles: set[Role] = roles
        self.email: str | None = email.lower().strip() if email is not None else None
        self.paper_affiliations: dict[str, list[Affiliation]] = paper_affiliations if paper_affiliations is not None else dict()

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

    def get_first_affiliation(self, paper_id: str | None = None) -> Affiliation | None:
        if paper_id is None:
            return self.default_affiliation
        if paper_id in self.paper_affiliations:
            aff = self.paper_affiliations[paper_id]
            if len(aff) > 0:
                return aff[0]
            else:
                return 0

        return self.default_affiliation

    def add_paper_affiliation(self, paper_id: str, affiliation: Affiliation):
        """Add an affiliation for a given paper

        Parameters
        ----------
        paper_id : str
            the paper identifier
        affiliation : Affiliation
            the affiliation used for the paper
        """

        if paper_id not in self.paper_affiliations:
            self.paper_affiliations[paper_id] = list()
        self.paper_affiliations[paper_id].append(affiliation)
        if self.default_affiliation is None:
            self.default_affiliation = affiliation

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

    def str_with_flatten_affiliations(self, paper_id: str | None = None, short: bool = False, markers: bool = False) -> str:
        """Generate a string representation of the person with the affiliation

        It can be controlled to have a more refined structure

        Parameters
        ----------
        paper_id : str, optional
            the affiliations associated with a given paper. If None, only the default affiliation will be used
        short : str,
            get only the short name of the affiliation
        markers : bool
            include ISCA markers

        Returns
        -------
        str
            the string representation of the authors with the affiliations
        """

        if markers:
            str_person = self.isca_name
        else:
            str_person = str(self)

        return f"{str_person} ({self.str_affiliations(paper_id, short, markers)})"

    def str_affiliations(self, paper_id: str | None = None, short: bool = False, markers: bool = False) -> str:
        """Get a string representation of the affiliations of the person

        Parameters
        ----------
        paper_id : str, optional
            The paper ID for which we want the affiliations. If None, use the default affiliation
        short : bool
            use the short name of the affiliation
        markers : bool
            activate markers

        Returns
        -------
        str
            the string representation of the affiliations

        """

        affiliations = []
        if (paper_id is None) or (paper_id not in self.paper_affiliations):
            if self.default_affiliation is not None:
                if short:
                    aff = self.default_affiliation.short
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
                    aff = affiliation.short
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

        return "; ".join(affiliations)

    @property
    def id(self) -> str:
        return self._id

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

    def __hash__(self) -> int:
        """Hashing method which hashes the email to identify the user

        Returns
        -------
        int
            hash(self._id)
        """
        return hash(self._id)

    def __repr__(self) -> str:
        """Generate a string representation of the person

        Returns
        -------
        str
            the string representation
        """

        return (
            f"{self.__class__.__name__}(id={self.id}, first_name={self.firstname}, middle_initial={self.middle_initial}, "
            + f"last_name={self.lastname}, email={self.email}, affiliation=[{self.default_affiliation}]), roles=({self._roles})"
        )

    def __str__(self) -> str:
        """Generate a printable string representation of the person

        It only contains the names (nothing about the affiliations, the email and the roles)

        Returns
        -------
        str
            the printable string representation
        """
        last_name = self.lastname

        if not self.firstname:
            return last_name

        if self.middle_initial is not None:
            user_str = f"{self.firstname} {self.middle_initial} {last_name}"
        else:
            user_str = f"{self.firstname} {last_name}"

        return user_str

    def __eq__(self, other: Any) -> bool:
        """Test if an other object is equal to the current one

        The comparison is done on the email, the first/last names and
        the affiliations.

        Parameters
        ----------
        other : Any
            the other object

        Returns
        -------
        bool
            True if this is the same person, False else
        """

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

    @classmethod
    def generate_id(cls) -> str:
        """Generate a default ID for the person

        It uses an internal counter and get the current value before increasing the counter by one
        Returns
        -------
        str
            the ID of the person

        """

        Person._id_counter += 1
        return str(Person._id_counter)


class Speaker(Person):
    """Representation of a speaker as a subclass of a Person

    Attributes
    ----------
    biography: str, optional
        The biography of the speaker (if available)
    url: str, optional
        The URL to the website of the speaker (if available)
    photo: pathlib.Path, optional
        The path to the picture file of the speaker (if available)
    """

    def __init__(
        self,
        id: str,
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
        """Initialisation method

        The email is not used as an identifier as it can change if the person changes institutes.

        Parameters
        ----------
        id: str
            A given identifier for the person. This field should only be used for serialisation purposes!
        firstname : str or None
            The first name of the person (set to None if mono-name)
        lastname : str
            The last name of the person
        default_affiliation : Affiliation
            The default affiliation of the person
        email : str, optional
            The current email of the person
        roles : set[Role]
            The set of roles of the person (chair, author, ....) [default: {Role.DEFAULT}]
        paper_affiliations: dict[str, list[Affiliations]], optional
            The dictionnary associating a list of affiliations to a given paper (ID)
        middle_initial: str, optional
            The middle initial of the name of the Person
        biography: str, optional
            The biography of the speaker (if available)
        url: str, optional
            The URL to the website of the speaker (if available)
        photo: pathlib.Path, optional
            The path to the picture file of the speaker (if available)
        """
        super().__init__(id, firstname, lastname, default_affiliation, email, roles, paper_affiliations, middle_initial)
        self.biography: str | None = biography
        self.url: str | None = url
        self.photo: pathlib.Path | None = photo
        self.add_role(Role.PRESENTER)

    @classmethod
    def from_person(cls, person: Person) -> "Speaker":
        """Helper to bootstrap a Speaker from a given Person


        Parameters
        ----------
        person : Person
            the person used to generate a speaker

        Returns
        -------
        "Speaker"
            the speaker generated from the person
        """

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
    """Representation of an Annuary of persons (authors, chairs, ...)"""

    def __init__(self, alternative_emails: dict[str, str] | None = None):
        """Initialisation method

        A dictionary of alternative emails can be provided.
        This dictionnary will be used internally to deduplicate some person who are known to be using different emails.

        Parameters
        ----------
        alternative_emails : dict[str, str], optional
            Dictionary of alternative emails [alternative -> reference]

        """

        super().__init__()
        self._annuary: dict[int, Person] = dict()
        self._email_annuary: dict[str, Person] = dict()
        self._alternative_emails: dict[str, str] = dict()

        if alternative_emails is not None:
            for alternative_email, reference_email in alternative_emails.items():
                self.add_alternative_email(reference_email, alternative_email)

    def add_alternative_email(self, reference_email: str, alternative_email: str):
        """Manually add an alternative email

        Parameters
        ----------
        reference_email : str
            The reference email used internally
        alternative_email : str
            The alternative email to be mapped to the reference email
        """

        reference_email = reference_email.strip().lower()
        alternative_email = alternative_email.strip().lower()
        self._alternative_emails[alternative_email] = reference_email

    def get_reference_email(self, alternative_email: str) -> str:
        """Get the reference email of the given alternative email

        Parameters
        ----------
        alternative_email : str
            the alternative email for which we want the mapped reference email

        Returns
        -------
        str
            The reference email associated to the given alternative email
        """
        alternative_email = alternative_email.strip().lower()
        return self._alternative_emails[alternative_email]

    def is_an_alternative_email(self, email: str) -> bool:
        """Check if the given email is part of the available alternative emails

        Parameters
        ----------
        email : str
            The email to check

        Returns
        -------
        bool
            True if the email is considered as an alternative email, False else
        """
        return email.strip().lower() in self._alternative_emails

    def update_alternative_emails(self, alternative_emails: dict[str, str]):
        """Update the dictionnary of alternative emails

        Parameters
        ----------
        alternative_emails : dict[str, str]
            the dictionnary of alternative emails to be added or  updated

        """

        for alternative_email, reference_email in alternative_emails.items():
            if alternative_email in self._alternative_emails:
                self.logger.info(
                    f"The alternative email <{alternative_email}> already points to <{self._alternative_emails[alternative_email]}> in the current annuary"
                )
            else:
                self.add_alternative_email(reference_email, alternative_email)

    def add(self, person: Person, force: bool = False):
        """Add a person to the annuary

        Parameters
        ----------
        person : Person
            the person to add
        force : bool
            If True, replace the person if it already exists; else NOTHING HAPPENS

        """

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

    def replace(self, old_person: Person, new_person: Person):
        """Replace a given person by a new one in the annuary

        Parameters
        ----------
        old_person : Person
            The person to be replaced
        new_person : Person
            The new person to be inserted

        """

        assert old_person.email is not None
        del self._email_annuary[old_person.email]
        del self._annuary[hash(old_person)]

        self.add(new_person)

    def update(self, other: "Annuary", force: bool = False, ignore_alternative: bool = False):
        """Update the annuary using the information from another annuary

        Parameters
        ----------
        other : Annuary
            The other annuary whose information is inserted in the current one
        force : bool
            force the replacement of the person
        ignore_alternative : bool
            ignore the alternative emails or not

        """

        for person in other._annuary.values():
            self.add(person, force)

        if not ignore_alternative:
            self.update_alternative_emails(other._alternative_emails)

    def find_person_by_email(self, email: str) -> Person | None:
        """Search for a given person using the email

        Parameters
        ----------
        email : str
            The email used to search the person

        Returns
        -------
        Person | None
            the found person, else None

        """

        email = email.lower().strip()
        if self.is_an_alternative_email(email):
            email = self.get_reference_email(email)

        if email not in self._email_annuary:
            return None
        return self._email_annuary[email]

    def find_persons_by_name(
        self, firstname: str, lastname: str, middle_initial: str | None = None, ignore_middle_initial: bool = False
    ) -> set[Person]:
        """Search for the person using the name information

        Parameters
        ----------
        firstname : str
            The first name of the person
        lastname : str
            The last name of the person
        middle_initial : str, optional
            The middle initial
        ignore_middle_initial : bool
            Helper flag to relax the constraint on the middle initial

        Returns
        -------
        set[Person]
            The set of found persons (generally only one element, but the set may be composed ofn homonyms!)

        """
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

    def compress(self, select_criterion: Callable[[Person], bool] = lambda x: bool(x.roles)) -> "Annuary":
        """Compress the annuary based on the criterion

        In other words, all the person not validating the criterion  will be removed from the annuary

        Parameters
        ----------
        select_criterion : Callable[[Person], bool]
            The criterion used to compress, by default it should have at least one role

        Returns
        -------
        Annuary
            The compressed annuary

        """

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

    @property
    def reviewers(self) -> set[Person]:
        reviewers = set()
        for p in self._annuary.values():
            if p.validate_roles(set([Role.REVIEWER])):
                reviewers.add(p)
        return reviewers

    @property
    def alternative_emails(self) -> dict[str, str]:
        return self._alternative_emails

    def __repr__(self) -> str:
        """Get a string representation of the annuary

        Returns
        -------
        str
            The string presentation of the annuary
        """
        output = ""
        for person in self._annuary:
            output += f"- {repr(person)}\n"
        return output

    def __str__(self) -> str:
        """Get a printable string representation of the annuary

        Returns
        -------
        str
            The printable string presentation of the annuary
        """

        output = ""
        for person in self._annuary.values():
            output += f"- {person}\n"
        return output

    def __iter__(self) -> Iterator[Person]:
        """Make the annuary iterable

        Returns
        -------
        Iterator[Person]
            The iterator which provides a person at each iteration

        """

        return iter(self._annuary.values())
