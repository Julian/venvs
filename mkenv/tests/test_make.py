from functools import partial
from tempfile import mkdtemp
from unittest import TestCase
import os

from bp.filepath import FilePath

from mkenv import find, make
from mkenv.common import Locator
from mkenv._cli import CommandLine
from mkenv.tests.utils import CLIMixin


class TestMake(CLIMixin, TestCase):

    cli = make

    def test_make_creates_an_env_with_the_given_name(self):
        self.assertFalse(self.locator.for_name("made").exists)
        self.run_cli(["made"])
        self.assertTrue(self.locator.for_name("made").exists)

    def test_make_t_creates_a_global_temporary_environment(self):
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
            ["--temporary", "foo"], exit_status=os.EX_USAGE,
        )
        self.assertEqual(
            (stdin, stdout, stderr), (
                "",
                stdout,
                "error: specify only one of "
                "'-t / --temp / --temporary' or 'name'\n\n",
            ),
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
            self.installed[self.locator.for_name("bla")],
            [(["foo", "bar"], ["reqs.txt"])],
        )


class TestIntegration(TestCase):
    def setUp(self):
        self.root = FilePath(mkdtemp())
        self.addCleanup(self.root.remove)

    def test_it_works(self):
        with self.root.child("make_stdout").open("w") as stdout:
            make.run(
                stdout=stdout,
                exit=partial(self.assertEqual, 0),
                command_line=CommandLine(
                    argv=[
                        "--root", self.root.path,
                        "mkenv-unittest-should-be-deleted",
                    ],
                ),
            )

        with self.root.child("find_stdout").open("w") as stdout:
            find.run(
                stdout=stdout,
                exit=partial(self.assertEqual, 0),
                command_line=CommandLine(
                    argv=[
                        "--existing-only",
                        "--root", self.root.path,
                        "--name", "mkenv-unittest-should-be-deleted",
                    ],
                ),
            )

        locator = Locator(root=self.root)
        virtualenv = locator.for_name("mkenv-unittest-should-be-deleted")
        self.assertEqual(
            self.root.child("find_stdout").getContent(),
            virtualenv.path.path + "\n",
        )
