from StringIO import StringIO
from functools import partial
from unittest import TestCase, skip
import os

from bp.filepath import FilePath
from bp.memory import MemoryFS, MemoryPath

from mkenv import find
from mkenv.common import VIRTUALENVS_ROOT


class TestFind(TestCase):
    def run_cli(self, argv=(), exit_status=os.EX_OK):
        stdin, stdout, stderr = StringIO(), StringIO(), StringIO()
        find.run(
            argv=argv,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            exit=partial(self.assertEqual, 0),
        )
        return stdin.getvalue(), stdout.getvalue(), stderr.getvalue()

    def test_find_without_args_finds_the_virtualenv_root(self):
        stdin, stdout, stderr = self.run_cli()
        self.assertEqual(
            (stdin, stdout, stderr),
            ("", VIRTUALENVS_ROOT.path + "\n", ""),
        )

    def test_find_d_finds_envs_by_directory(self):
        this_dir = FilePath(__file__).parent()
        stdin, stdout, stderr = self.run_cli(["-d", this_dir.path])
        self.assertEqual(
            (stdin, stdout, stderr),
            ("", find.env_for_directory(this_dir).path + "\n", ""),
        )

    def test_find_d_defaults_to_cwd(self):
        stdin, stdout, stderr = self.run_cli(["-d"])
        self.assertEqual(
            (stdin, stdout, stderr),
            ("", find.env_for_directory(FilePath(".")).path + "\n", ""),
        )

    def test_find_n_finds_envs_by_name(self):
        stdin, stdout, stderr = self.run_cli(["-n", "bla"])
        self.assertEqual(
            (stdin, stdout, stderr),
            ("", find.env_for_name("bla").path + "\n", ""),
        )


class TestExisting(TestCase):
    @skip("Skipped until refactoring to make testing this possible.")
    def test_find_existing_fails_for_non_existing_directories(self):
        stdin, stdout, stderr = StringIO(), StringIO(), StringIO()
        path = MemoryPath(fs=MemoryFS())
        exit_status = find.run.with_arguments(
            arguments={"directory" : path, "existing-only" : True},
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
        )
        self.assertNotEqual(exit_status, 0)
