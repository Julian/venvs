from unittest import TestCase
import sys

from filesystems import Path
import filesystems.native

from venvs import _cli, _config
from venvs.common import Locator
from venvs.tests.utils import CLIMixin


class TestCreate(CLIMixin, TestCase):
    def test_create_creates_an_env_with_the_given_name(self):
        self.assertFalse(self.locator.for_name("a").exists_on(self.filesystem))
        self.run_cli(["create", "a"])
        self.assertTrue(self.locator.for_name("a").exists_on(self.filesystem))

    def test_recreate(self):
        virtualenv = self.locator.for_name("something")
        self.assertFalse(virtualenv.exists_on(self.filesystem))

        virtualenv.create()

        thing = virtualenv.path / "thing"
        self.filesystem.touch(path=thing)
        self.assertTrue(self.filesystem.exists(thing))

        self.run_cli(["create", "--recreate", "something"])
        self.assertTrue(virtualenv.exists_on(self.filesystem))

        self.assertFalse(self.filesystem.exists(thing))

    def test_install_and_requirements(self):
        self.run_cli(
            ["create", "-i", "foo", "-i", "bar", "-r", "reqs.txt", "bla"],
        )
        # We've stubbed out our Locator's venvs' install to just store.
        self.assertEqual(
            self.installed(self.locator.for_name("bla")),
            ({"foo", "bar"}, {"reqs.txt"}),
        )

    def test_venvs_default_name(self):
        """
        Just saying ``venvs`` creates an environment based on the current
        directory's name.
        """

        virtualenv = self.locator.for_directory(Path.cwd())
        self.assertFalse(virtualenv.exists_on(self.filesystem))
        self.run_cli(["create"])
        self.assertTrue(virtualenv.exists_on(self.filesystem))

    def test_install_default_name(self):
        """
        If you install one single package and don't specify a name, the name of
        the installed package is used.
        """

        self.run_cli(["create", "-i", "foo"])
        # We've stubbed out our Locator's venvs' install to just store.
        self.assertEqual(
            self.installed(self.locator.for_name("foo")), ({"foo"}, set()),
        )

    def test_install_default_name_with_version_specification(self):
        self.run_cli(["create", "-i", "thing[foo]>=2,<3"])
        # We've stubbed out our Locator's venvs' install to just store.
        self.assertEqual(
            self.installed(self.locator.for_name("thing")),
            ({"thing[foo]>=2,<3"}, set()),
        )

    def test_link_default_name(self):
        """
        If you link one single binary and don't specify a name, the name of
        the binary is probably both the package and what you want to call the
        environment.

        """

        self.run_cli(["create", "-l", "foo"])
        # We've stubbed out our Locator's venvs' install to just store.
        self.assertEqual(
            self.installed(self.locator.for_name("foo")), ({"foo"}, set()),
        )

    def test_multiple_installs_one_link(self):
        self.run_cli(["create", "-i", "foo", "-i", "bar", "-l", "foo", "baz"])
        # We've stubbed out our Locator's venvs' install to just store.
        self.assertEqual(
            self.installed(self.locator.for_name("baz")),
            ({"foo", "bar"}, set()),
        )

    def test_multiple_installs_one_link_no_name(self):
        self.run_cli(
            ["create", "-i", "foo", "-i", "bar", "-l", "foo"],
            exit_status=2,
        )

    def test_install_edit_config(self):
        """Install --persist edits the config file."""
        self.run_cli(["create", "-l", "foo", "-i", "bar", "--persist"])

        self.assertConfigEqual(
            """
            [virtualenv.bar]
            install = ["bar"]
            link = ["foo"]
            """,
        )

    def test_handle_empty_config_file(self):
        """Don't break with an empty config file."""

        self.filesystem.touch(self.locator.root.descendant("virtualenvs.toml"))

        self.run_cli(["create", "-l", "foo", "-i", "bar", "--persist"])

        self.assertConfigEqual(
            """
            [virtualenv.bar]
            install = ["bar"]
            link = ["foo"]
            """,
        )

    def test_persist_handles_missing_config_directory(self):
        """Create the config directory if it does not exist."""

        self.filesystem.remove_empty_directory(self.locator.root)

        self.run_cli(["create", "-l", "foo", "-i", "bar", "--persist"])

        self.assertConfigEqual(
            """
            [virtualenv.bar]
            install = ["bar"]
            link = ["foo"]
            """,
        )

    def test_no_persist_handles_missing_virtualenv_directory(self):
        """Don't break if there is no virtualenv directory."""

        self.filesystem.remove_empty_directory(self.locator.root)

        self.run_cli(["create", "-l", "foo", "-i", "bar", "--no-persist"])

        self.assertTrue(self.filesystem.exists(self.locator.root))

        # Config file has _not_ been created.
        self.assertFalse(
            self.filesystem.exists(
                self.locator.root.descendant("virtualenvs.toml")
            )
        )

    def test_install_no_persist(self):
        """Install --no-persist does not edit the config file."""
        self.run_cli(["create", "-l", "foo", "-i", "bar", "--no-persist"])

        # No file has been created.
        with self.assertRaises(filesystems.exceptions.FileNotFound):
            _config.Config.from_locator(
                filesystem=self.filesystem,
                locator=self.locator,
            )


class TestIntegration(TestCase):
    def setUp(self):
        self.fs = filesystems.native.FS()
        self.root = self.fs.temporary_directory()
        self.addCleanup(self.fs.remove, self.root)

        # Fucking click.
        stdout = sys.stdout
        self.addCleanup(lambda: setattr(sys, "stdout", stdout))

    def test_it_works(self):
        with self.fs.open(self.root / "create_stdout", "w") as stdout:
            sys.stdout = stdout

            try:
                _cli.main(
                    args=[
                        "create",
                        "--root", str(self.root),
                        "venvs-unittest-should-be-deleted",
                    ],
                )
            except SystemExit:
                pass

        with self.fs.open(self.root / "find_stdout", "w") as stdout:
            sys.stdout = stdout

            try:
                _cli.main(
                    [
                        "find",
                        "--root", str(self.root),
                        "--existing-only",
                        "name", "venvs-unittest-should-be-deleted",
                    ],
                )
            except SystemExit:
                pass

        locator = Locator(root=self.root)
        virtualenv = locator.for_name("venvs-unittest-should-be-deleted")
        self.assertEqual(
            self.fs.get_contents(self.root / "find_stdout"),
            str(virtualenv.path) + "\n",
        )
