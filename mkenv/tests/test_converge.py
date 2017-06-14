from unittest import TestCase
import os

from mkenv import converge
from mkenv.tests.utils import CLIMixin


class TestConverge(CLIMixin, TestCase):

    cli = converge

    def test_it_creates_missing_virtualenvs(self):
        self.assertFalse(self.locator.for_name("a").exists_on(self.filesystem))
        self.assertFalse(self.locator.for_name("b").exists_on(self.filesystem))
        self.assertFalse(self.locator.for_name("c").exists_on(self.filesystem))

        with self.filesystem.open(
            self.locator.root.descendant("virtualenvs.toml"), "w",
        ) as venvs:
            venvs.write(
                """
                [virtualenv.a]
                [virtualenv.b]
                install = ["foo", "bar", "bla"]
                requirements = ["requirements.txt"]
                [virtualenv.c]
                install = ["foo", "$HOME", "~/a"]
                link = ["bar", "baz"]
                """
            )

        self.run_cli([])

        self.assertEqual(
            (
                self.installed(self.locator.for_name("a")),
                self.installed(self.locator.for_name("b")),
                self.installed(self.locator.for_name("c")),
            ), (
                (set(), set()),
                ({"foo", "bar", "bla"}, {"requirements.txt"}),
                ({"foo", os.getenv("HOME"), os.path.expanduser("~/a")}, set()),
            ),
        )

    def test_it_converges_existing_virtualenvs(self):
        self.assertFalse(self.locator.for_name("a").exists_on(self.filesystem))
        self.assertFalse(self.locator.for_name("b").exists_on(self.filesystem))
        self.assertFalse(self.locator.for_name("c").exists_on(self.filesystem))

        with self.filesystem.open(
            self.locator.root.descendant("virtualenvs.toml"), "w",
        ) as venvs:
            venvs.write(
                """
                [virtualenv.a]
                install = ["foo", "bar"]
                requirements = ["requirements.txt"]
                """
            )

        self.run_cli([])

        with self.filesystem.open(
            self.locator.root.descendant("virtualenvs.toml"), "w",
        ) as venvs:
            venvs.write(
                """
                [virtualenv.a]
                install = ["baz", "quux"]
                requirements = ["requirements.txt", "other.txt"]
                """
            )

        self.run_cli([])

        self.assertEqual(
            self.installed(self.locator.for_name("a")),
            ({"baz", "quux"}, {"requirements.txt", "other.txt"}),
        )
