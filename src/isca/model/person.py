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

    def __init__(
        self, firstname: str, lastname: str, email: str, affiliation: Affiliation | None = None, id: str | None = None
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
        self.firstname: str = firstname
        self.lastname: str = lastname
        self.email: str = email
        self.affiliation: Affiliation | None = affiliation
        self._id: str = self._generate_id()

    @property
    def id(self) -> str:
        """Property to access the identifier of the Person

        Returns
        -------
        str
            The identifier of the person
        """
        return self._id

    def _generate_id(self) -> str:
        """Helper to generate a unique ID

        The generation relies on the firstname, lastname and email of
        the person. An additional random number is appended to ensure
        the uniqueness of the ID

        Returns
        -------
        str
            The generated identifier of the current person

        """
        return ""
