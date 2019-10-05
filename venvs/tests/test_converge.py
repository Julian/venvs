from unittest import TestCase
import os

from filesystems.exceptions import FileExists

from venvs import _config
from venvs.tests.utils import CLIMixin


class TestConverge(CLIMixin, TestCase):
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

        self.run_cli(["converge"])

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

        self.run_cli(["converge"])

        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"), """
            [virtualenv.a]
            install = ["baz", "quux"]
            requirements = ["requirements.txt", "other.txt"]
            """
        )

        self.run_cli(["converge"])

        self.assertEqual(
            self.installed(self.locator.for_name("a")),
            ({"baz", "quux"}, {"requirements.txt", "other.txt"}),
        )

    def test_bundles(self):
        self.assertFalse(self.locator.for_name("a").exists_on(self.filesystem))

        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"), """
            [bundle]
            dev = ["bar", "bla"]

            [virtualenv.a]
            install = ["foo"]
            install-bundle = ["dev"]
            """
        )

        self.run_cli(["converge"])

        self.assertEqual(
            self.installed(self.locator.for_name("a")),
            ({"foo", "bar", "bla"}, set()),
        )

    def test_no_such_bundle(self):
        self.assertFalse(self.locator.for_name("a").exists_on(self.filesystem))

        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"), """
            [virtualenv.a]
            install = ["foo"]
            install-bundle = ["dev"]
            """
        )

        self.run_cli(["converge"])

        self.assertEqual(
            self.installed(self.locator.for_name("a")),
            (set(), set()),
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

        self.run_cli(["converge"])

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
            self.run_cli(["converge", "--fail-fast"])

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

        self.run_cli(["converge"])

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
            self.run_cli(["converge"])

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

        self.run_cli(["converge"])

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

        with self.assertRaises(_config.DuplicatedLinks) as e:
            self.run_cli(["converge"])

        self.assertIn("foo", str(e.exception))
        self.assertEqual(self.linked, {})

    def test_conflicting_links_via_rename(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"), """
            [virtualenv.a]
            link = ["foo"]

            [virtualenv.b]

            [virtualenv.c]
            link = ["bar:foo"]
            """
        )

        with self.assertRaises(_config.DuplicatedLinks) as e:
            self.run_cli(["converge"])

        self.assertIn("foo", str(e.exception))
        self.assertEqual(self.linked, {})

    def test_specified_link_name(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"), """
            [virtualenv.a]
            link = ["foo:fooBar"]
            """
        )

        self.run_cli(["converge"])

        self.assertEqual(
            self.linked,
            {"fooBar": self.locator.for_name("a").binary("foo")},
        )

    def test_link_m_module(self):
        """
        It links modules run via -m as wrappers.
        """
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"), """
            [virtualenv.a]
            link-module = ["this"]
            """
        )

        self.run_cli(["converge"])

        contents = self.filesystem.get_contents(
            self.link_dir.descendant("this"),
        )
        self.assertEqual(
            contents.splitlines()[0],
            "#!" + str(self.locator.for_name("a").binary("python")),
        )

    def test_link_m_module_specified_name(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"), """
            [virtualenv.a]
            link-module = ["this:that"]
            """
        )

        self.run_cli(["converge"])

        contents = self.filesystem.get_contents(
            self.link_dir.descendant("that"),
        )
        self.assertEqual(
            contents.splitlines()[0],
            "#!" + str(self.locator.for_name("a").binary("python")),
        )

    def test_link_m_module_duplicated(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"), """
            [virtualenv.a]
            link = ["foo"]

            [virtualenv.b]

            [virtualenv.c]
            link-module = ["bar:foo"]
            """
        )

        with self.assertRaises(_config.DuplicatedLinks) as e:
            self.run_cli(["converge"])

        self.assertIn("foo", str(e.exception))
        self.assertEqual(self.linked, {})
