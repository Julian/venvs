from unittest import TestCase

from filesystems import Path
import toml

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
                install = ["foo"]
                link = ["bar", "baz"]
                """
            )

        self.run_cli([])

        self.assertEqual(
            (
                self.installed.get(self.locator.for_name("a")),
                self.installed.get(self.locator.for_name("b")),
                self.installed.get(self.locator.for_name("c")),
            ), (
                [([], [])],
                [(["foo", "bar", "bla"], ["requirements.txt"])],
                [(["foo"], [])],
            ),
        )