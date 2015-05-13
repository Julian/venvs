from unittest import TestCase

from mkenv import remove
from mkenv.tests.utils import CLIMixin


class TestMake(CLIMixin, TestCase):

    cli = remove

    def test_remove_removes_an_env_with_the_given_name(self):
        boom = self.locator.for_name("boom")
        boom.create()
        self.assertTrue(boom.exists)
        self.run_cli(["boom"])
        self.assertFalse(boom.exists)
