from unittest import TestCase
import sys

from filesystems import Path
import filesystems.native

from venvs import find, make
from venvs.common import Locator
from venvs.tests.utils import CLIMixin


class TestMake(CLIMixin, TestCase):

    cli = make

    def test_make_creates_an_env_with_the_given_name(self):
        self.assertFalse(self.locator.for_name("a").exists_on(self.filesystem))
        self.run_cli(["a"])
        self.assertTrue(self.locator.for_name("a").exists_on(self.filesystem))

    def test_make_t_creates_a_global_temporary_environment(self):
        temporary = self.locator.temporary()
        self.assertFalse(temporary.exists_on(self.filesystem))

        stdin, stdout, stderr = self.run_cli(["--temporary"])
        self.assertEqual(
            (temporary.exists_on(self.filesystem), stdin, stdout, stderr),
            (True, "", str(temporary.path.descendant("bin")) + "\n", ""),
        )

    def test_make_t_recreates_the_environment_if_it_exists(self):
        temporary = self.locator.temporary()
        self.assertFalse(temporary.exists_on(self.filesystem))
        self.run_cli(["--temporary"])
        self.assertTrue(temporary.exists_on(self.filesystem))

        foo = temporary.path.descendant("foo")
        self.filesystem.touch(path=foo)
        self.assertTrue(self.filesystem.exists(path=foo))

        self.run_cli(["--temporary"])
        self.assertTrue(temporary.exists_on(self.filesystem))
        self.assertFalse(self.filesystem.exists(path=foo))

    def test_cannot_specify_both_name_and_temporary(self):
        stdin, stdout, stderr = self.run_cli(
            ["--temporary", "foo"], exit_status=2,
        )
        self.assertTrue(
            stderr.endswith(
                "specify only one of '-t / --temp / --temporary' or 'name'\n"
            ), msg=stderr,
        )

    def test_recreate(self):
        virtualenv = self.locator.for_name("something")
        self.assertFalse(virtualenv.exists_on(self.filesystem))

        virtualenv.create()

        thing = virtualenv.path.descendant("thing")
        self.filesystem.touch(path=thing)
        self.assertTrue(self.filesystem.exists(thing))

        self.run_cli(["--recreate", "something"])
        self.assertTrue(virtualenv.exists_on(self.filesystem))

        self.assertFalse(self.filesystem.exists(thing))

    def test_install_and_requirements(self):
        self.run_cli(["-i", "foo", "-i", "bar", "-r", "reqs.txt", "bla"])
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
        self.run_cli([])
        self.assertTrue(virtualenv.exists_on(self.filesystem))

    def test_install_default_name(self):
        """
        If you install one single package and don't specify a name, the name of
        the installed package is used.

        """

        self.run_cli(["-i", "foo"])
        # We've stubbed out our Locator's venvs' install to just store.
        self.assertEqual(
            self.installed(self.locator.for_name("foo")), ({"foo"}, set()),
        )

    def test_install_default_name_with_version_specification(self):
        self.run_cli(["-i", "thing[foo]>=2,<3"])
        # We've stubbed out our Locator's venvs' install to just store.
        self.assertEqual(
            self.installed(self.locator.for_name("thing")),
            ({"thing[foo]>=2,<3"}, set()),
        )

    def test_temporary_env_with_single_install(self):
        self.run_cli(["-t", "-i", "thing"])
        # We've stubbed out our Locator's venvs' install to just store.
        self.assertEqual(
            self.installed(self.locator.temporary()), ({"thing"}, set()),
        )

    def test_link_default_name(self):
        """
        If you link one single binary and don't specify a name, the name of
        the binary is probably both the package and what you want to call the
        environment.

        """

        self.run_cli(["-l", "foo"])
        # We've stubbed out our Locator's venvs' install to just store.
        self.assertEqual(
            self.installed(self.locator.for_name("foo")), ({"foo"}, set()),
        )

    def test_multiple_installs_one_link(self):
        self.run_cli(["-i", "foo", "-i", "bar", "-l", "foo", "baz"])
        # We've stubbed out our Locator's venvs' install to just store.
        self.assertEqual(
            self.installed(self.locator.for_name("baz")),
            ({"foo", "bar"}, set()),
        )

    def test_multiple_installs_one_link_no_name(self):
        self.run_cli(["-i", "foo", "-i", "bar", "-l", "foo"], exit_status=2)


class TestIntegration(TestCase):
    def setUp(self):
        self.fs = filesystems.native.FS()
        self.root = self.fs.temporary_directory()
        self.addCleanup(self.fs.remove, self.root)

        # Fucking click.
        stdout = sys.stdout
        self.addCleanup(lambda: setattr(sys, "stdout", stdout))

    def test_it_works(self):
        with self.fs.open(self.root.descendant("make_stdout"), "w") as stdout:
            sys.stdout = stdout

            try:
                make.main(
                    args=[
                        "--root", str(self.root),
                        "venvs-unittest-should-be-deleted",
                    ],
                )
            except SystemExit:
                pass

        with self.fs.open(self.root.descendant("find_stdout"), "w") as stdout:
            sys.stdout = stdout

            try:
                find.main(
                    [
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
            self.fs.contents_of(self.root.descendant("find_stdout")),
            str(virtualenv.path) + "\n",
        )
