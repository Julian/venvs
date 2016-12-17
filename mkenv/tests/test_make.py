from errno import ENOENT
from tempfile import mkdtemp
from unittest import TestCase
import sys

from bp.filepath import FilePath

from mkenv import find, make
from mkenv.common import Locator
from mkenv.tests.utils import CLIMixin


class TestMake(CLIMixin, TestCase):

    cli = make

    def test_make_creates_an_env_with_the_given_name(self):
        self.assertFalse(self.locator.for_name("made").exists)
        self.run_cli(["made"])
        self.assertTrue(self.locator.for_name("made").exists)

    def test_make_t_creates_a_global_temporary_environment_OSError(self):
        temporary = self.locator.temporary()
        self.assertFalse(temporary.exists)

        def real_fake_remove(path):
            """
            os.remove will raise an OSError, not an IOError.

            """

            raise OSError(ENOENT, "NOPE")

        MemoryPath = temporary.path.__class__
        remove, MemoryPath.remove = MemoryPath.remove, real_fake_remove
        self.addCleanup(setattr, MemoryPath, "remove", remove)

        self.run_cli(["--temporary"])
        self.assertTrue(temporary.exists)

    def test_make_t_creates_a_global_temporary_environment_IOError(self):
        """
        If we use os.remove, this one actually should never happen, since that
        will raise OSError, but we ensure we cover both cases.

        """

        temporary = self.locator.temporary()
        self.assertFalse(temporary.exists)

        self.run_cli(["--temporary"])
        self.assertTrue(temporary.exists)

    def test_make_t_recreates_the_environment_if_it_exists(self):
        temporary = self.locator.temporary()
        self.assertFalse(temporary.exists)
        self.run_cli(["--temporary"])
        self.assertTrue(temporary.exists)

        foo = temporary.path.child("foo")
        foo.setContent("testing123")
        self.assertTrue(foo.exists())

        self.run_cli(["--temporary"])
        self.assertTrue(temporary.exists)
        self.assertFalse(foo.exists())

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
        self.assertFalse(virtualenv.exists)

        virtualenv.create()
        virtualenv.path.child("thing").setContent("")

        self.run_cli(["--recreate", "something"])
        self.assertTrue(virtualenv.exists)
        self.assertFalse(virtualenv.path.child("thing").exists())

    def test_install_and_requirements(self):
        self.run_cli(["-i", "foo", "-i", "bar", "-r", "reqs.txt", "bla"])
        # We've stubbed out our Locator's venvs' install to just store.
        self.assertEqual(
            self.installed.get(self.locator.for_name("bla")),
            [(("foo", "bar"), ("reqs.txt",))],
        )

    def test_install_default_name(self):
        """
        If you install one single package and don't specify a name, the name of
        the installed package is used.

        """

        self.run_cli(["-i", "foo"])
        # We've stubbed out our Locator's venvs' install to just store.
        self.assertEqual(
            self.installed.get(self.locator.for_name("foo")), [(("foo",), ())],
        )

    def test_install_default_name_with_version_specification(self):
        self.run_cli(["-i", "thing[foo]>=2,<3"])
        # We've stubbed out our Locator's venvs' install to just store.
        self.assertEqual(
            self.installed.get(self.locator.for_name("thing")),
            [(("thing[foo]>=2,<3",), ())],
        )


class TestIntegration(TestCase):
    def setUp(self):
        self.root = FilePath(mkdtemp())
        self.addCleanup(self.root.remove)

        # Fucking click.
        stdout = sys.stdout
        self.addCleanup(lambda: setattr(sys, "stdout", stdout))

    def test_it_works(self):
        with self.root.child("make_stdout").open("w") as stdout:
            sys.stdout = stdout

            try:
                make.main(
                    args=[
                        "--root", self.root.path,
                        "mkenv-unittest-should-be-deleted",
                    ],
                )
            except SystemExit:
                pass

        with self.root.child("find_stdout").open("w") as stdout:
            sys.stdout = stdout

            try:
                find.main(
                    [
                        "--root", self.root.path,
                        "--existing-only",
                        "name", "mkenv-unittest-should-be-deleted",
                    ],
                )
            except SystemExit:
                pass

        locator = Locator(root=self.root)
        virtualenv = locator.for_name("mkenv-unittest-should-be-deleted")
        self.assertEqual(
            self.root.child("find_stdout").getContent(),
            virtualenv.path.path + "\n",
        )
