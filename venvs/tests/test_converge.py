from unittest import TestCase
import os

from filesystems.exceptions import FileExists

from venvs import converge
from venvs.tests.utils import CLIMixin


class TestConverge(CLIMixin, TestCase):

    cli = converge

    def test_it_creates_missing_virtualenvs(self):
        self.assertFalse(self.locator.for_name("a").exists_on(self.filesystem))
        self.assertFalse(self.locator.for_name("b").exists_on(self.filesystem))
        self.assertFalse(self.locator.for_name("c").exists_on(self.filesystem))

        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"), """
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
                (
                    {
                        "foo",
                        os.path.expandvars("$HOME"),
                        os.path.expanduser("~/a"),
                    },
                    set(),
                ),
            ),
        )

    def test_it_converges_existing_virtualenvs(self):
        self.assertFalse(self.locator.for_name("a").exists_on(self.filesystem))
        self.assertFalse(self.locator.for_name("b").exists_on(self.filesystem))
        self.assertFalse(self.locator.for_name("c").exists_on(self.filesystem))

        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"), """
            [virtualenv.a]
            install = ["foo", "bar"]
            requirements = ["requirements.txt"]
            """
        )

        self.run_cli([])

        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"), """
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

    def test_it_does_not_blow_up_by_default_on_install(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"), """
            [virtualenv.a]
            [virtualenv.b]
            [virtualenv.magicExplodingVirtualenv]
            [virtualenv.c]
            """
        )

        self.run_cli([])

        self.assertEqual(
            (
                self.installed(self.locator.for_name("a")),
                self.installed(self.locator.for_name("b")),
                self.installed(self.locator.for_name("c")),
                self.locator.for_name("c").exists_on(self.filesystem),
            ),
            tuple((set(), set()) for _ in "abc") + (True,),
        )

    def test_it_can_be_asked_to_blow_up_immediately_on_install(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"), """
            [virtualenv.a]
            [virtualenv.b]
            [virtualenv.magicExplodingVirtualenv]
            [virtualenv.c]
            """
        )

        with self.assertRaises(ZeroDivisionError):
            self.run_cli(["--fail-fast"])

        self.assertEqual(
            (
                self.installed(self.locator.for_name("a")),
                self.installed(self.locator.for_name("b")),
                self.locator.for_name("c").exists_on(self.filesystem),
            ),
            ((set(), set()), (set(), set()), False),
        )

    def test_specified_python(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"), """
            [virtualenv.a]
            python = "python3"
            """
        )

        self.run_cli([])

        # FIXME: this doesn't properly assert about the python version...
        self.assertEqual(
            self.installed(self.locator.for_name("a")),
            (set(), set()),
        )

    def test_link_exists(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"), """
            [virtualenv.a]
            link = ["foo"]
            """
        )

        self.filesystem.touch(self.link_dir.descendant("foo"))

        with self.assertRaises(FileExists):
            self.run_cli([])

    def test_link_exists_as_broken_symlink(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"), """
            [virtualenv.a]
            link = ["foo"]
            """
        )

        self.filesystem.link(
            source=self.link_dir.descendant("broken"),
            to=self.link_dir.descendant("foo"),
        )

        self.run_cli([])

        self.assertEqual(
            self.linked,
            {"foo": self.locator.for_name("a").binary("foo")},
        )

    def test_conflicting_links(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"), """
            [virtualenv.a]
            link = ["foo"]

            [virtualenv.b]

            [virtualenv.c]
            link = ["foo"]
            """
        )

        with self.assertRaises(converge.DuplicatedLinks):
            self.run_cli([])

        self.assertEqual(self.linked, {})

    def test_specified_link_name(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"), """
            [virtualenv.a]
            link = ["foo:fooBar"]
            """
        )

        self.run_cli([])

        self.assertEqual(
            self.linked,
            {"fooBar": self.locator.for_name("a").binary("foo")},
        )
