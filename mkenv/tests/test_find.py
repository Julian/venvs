from StringIO import StringIO
from functools import partial
from unittest import TestCase, skip
import os

from bp.filepath import FilePath
from bp.memory import MemoryFS, MemoryPath

from mkenv import find
from mkenv.common import Locator


class TestFind(TestCase):
    def setUp(self):
        self.stdin = StringIO()
        self.stdout = StringIO()
        self.stderr = StringIO()

        self.fs = MemoryFS()
        self.locator = Locator(root=MemoryPath(fs=self.fs))

    def run_cli(self, argv=(), exit_status=os.EX_OK):
        find.run(
            argv=argv,
            stdin=self.stdin,
            stdout=self.stdout,
            stderr=self.stderr,
            exit=partial(self.assertEqual, exit_status),
            arguments={"locator" : self.locator},
        )
        return (
            self.stdin.getvalue(),
            self.stdout.getvalue(),
            self.stderr.getvalue(),
        )

    def test_find_without_args_finds_the_virtualenv_root(self):
        stdin, stdout, stderr = self.run_cli()
        self.assertEqual(
            (stdin, stdout, stderr),
            ("", self.locator.root.path + "\n", ""),
        )

    def test_find_d_finds_envs_by_directory(self):
        this_dir = FilePath(__file__).parent()
        stdin, stdout, stderr = self.run_cli(["-d", this_dir.path])
        self.assertEqual(
            (stdin, stdout, stderr),
            ("", self.locator.for_directory(this_dir).path + "\n", ""),
        )

    def test_find_d_defaults_to_cwd(self):
        stdin, stdout, stderr = self.run_cli(["-d"])
        self.assertEqual(
            (stdin, stdout, stderr),
            ("", self.locator.for_directory(FilePath(".")).path + "\n", ""),
        )

    def test_find_n_finds_envs_by_name(self):
        stdin, stdout, stderr = self.run_cli(["-n", "bla"])
        self.assertEqual(
            (stdin, stdout, stderr),
            ("", self.locator.for_name("bla").path + "\n", ""),
        )

    def test_find_existing_fails_for_non_existing_virtualenvs(self):
        stdin, stdout, stderr = self.run_cli(
            ["-n", "bla", "--existing-only"], exit_status=1,
        )
        self.assertEqual((stdin, stdout, stderr), ("", "", "")) 

    @skip("Skipped until bp supports some more nice things in MemoryPath.")
    def test_find_existing_succeeds_for_existing_virtualenvs(self):
        MemoryPath(fs=self.fs, path="bla").createDirectory()
        stdin, stdout, stderr = self.run_cli(["-n", "bla", "--existing-only"])
        self.assertEqual(
            (stdin, stdout, stderr),
            ("", self.locator.for_directory("bla").path + "\n", ""),
        )
