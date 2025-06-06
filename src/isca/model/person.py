from enum import Enum
from unidecode import unidecode
import logging


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

    def __init__(self, institute: str, country: str, department: str | None = None):
        """Initialisation method

        Parameters
        ----------
        institute : str
            The name of the institute
        country : str
            The country of the institute
        department : str, optional
            The name of the department, if any, else None [default: None]
        """

        self.department: str | None = department
        self.institute: str = institute
        self.country: str = country


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

    ROLE_SEP: str = ";"

    def __init__(
        self,
        firstname: str,
        lastname: str,
        email: str,
        roles: set[Role] = set([Role.DEFAULT]),
        affiliations: set[Affiliation] = set(),
        middle_initial: str = "",
        id: str | None = None,
    ):
        """Initialisation method

        The email is not used as an identifier as it can change if the person changes institutes.
        An identifier will be automatically generated and can be accessed via the property `self.id`

        Parameters
        ----------
        firstname : str
            The first name of the person
        lastname : str
            The last name of the person
        email : str
            The current email of the person
        affiliation : Affiliation, optional
            The current affiliation of the person (None if no affiliation) [default: None]
        id: str, optional
            A given identifier for the person. This field should only be used for serialisation purposes!
        """
        self._logger = logging.getLogger(self.__class__.__name__)
        self.firstname: str = firstname
        self.lastname: str = lastname
        self.middle_initial: str = middle_initial
        self._roles: set[Role] = roles
        self.email: str = email
        self.affiliations: set[Affiliation] = affiliations

        self._id: str = self._generate_id() if id is None else id

    def __str__(self) -> str:

        if not self.firstname:
            return self.lastname

        if self.middle_initial is not None:
            user_str = f"{self.firstname} {self.middle_initial} {self.lastname}"
        else:
            user_str = f"{self.firstname} {self.lastname}"

        return user_str

    def __hash__(self) -> int:
        """Hashing method which hashes the email to identify the user

        Returns
        -------
        int
            hash(self._email)
        """
        return hash(self.email)

    def __eq__(self, other: object) -> bool:
        """Equality testing

        Parameters
        ----------
        self: type
            description
        other: object
            The other object (instance of User!) to compare to the current one

        Returns
        -------
        bool
            True if both users have the same email
        """
        if not isinstance(other, Person):
            return False

        return other._id == self._id

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

    def str_isca(self) -> str:
        """Get the User formatted as the ISCA archive requires.

        This implies that the user will be formatted as "<First Name> {<Last Name>}" if the last name contains a space.

        Returns
        -------
        str
            the ISCA formatted user name ()
        """
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

    def is_presenter(self) -> bool:
        """Method to know if the current User is a presenter

        Returns
        -------
        bool
           True if the user is a presenter, False if not
        """
        return Role.PRESENTER in self._roles

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
        return f"{self.firstname} {self.lastname} ({self.email})"

    @property
    def id(self) -> str:
        return self._id

    def __repr__(self) -> str:
        return f"Person(id={self.id}, first_name={self.firstname}, middle_initial={self.middle_initial}, last_name={self.lastname}, email={self.email}, affiliations=[{self.affiliations}]), roles=({self._roles})"

    def __str__(self) -> str:
        return self.str_isca()

    def __eq__(self, other) -> bool:
        if self.id == other.id:
            return True
        return False
