import unittest
from isca.model.person import Affiliation
from isca.model.person import Person


class TestAffiliation(unittest.TestCase):
    def test_default_instantiate(self):
        affiliation = Affiliation("Short Name")
        self.assertIsNone(affiliation.country, "The country should be None if not initialised")

    def test_void_affiliation(self):
        self.assertRaises(AssertionError, lambda: Affiliation(None))

    def test_country_instantiate(self):
        aff_2 = Affiliation("Short Name", "Country")


class TestPerson(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._default_affiliation = Affiliation("Short Name")

    def test_isca_name(self):
        person = Person("id_person", "First Name", "Last Name", self._default_affiliation)
        self.assertEqual(person.isca_name, "First Name {Last Name}")
