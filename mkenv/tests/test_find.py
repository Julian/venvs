from unittest import TestCase

from bp.filepath import FilePath
from bp.memory import MemoryPath

from mkenv import find
from mkenv.tests.utils import CLIMixin


class TestFind(CLIMixin, TestCase):

    cli = find

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

    def test_find_existing_by_name_fails_for_non_existing_virtualenvs(self):
        stdin, stdout, stderr = self.run_cli(
            ["-n", "bla", "--existing-only"], exit_status=1,
        )
        self.assertEqual((stdin, stdout, stderr), ("", "", "")) 

    def test_find_existing_by_name_succeeds_for_existing_virtualenvs(self):
        path = MemoryPath(fs=self.fs, path=("bla",))
        path.createDirectory()
        stdin, stdout, stderr = self.run_cli(["-n", "bla", "--existing-only"])
        self.assertEqual(
            (stdin, stdout, stderr),
            ("", self.locator.for_name("bla").path + "\n", ""),
        )

    def test_find_existing_by_dir_fails_for_non_existing_virtualenvs(self):
        stdin, stdout, stderr = self.run_cli(
            ["-d", "/foo/bla", "--existing-only"], exit_status=1,
        )
        self.assertEqual((stdin, stdout, stderr), ("", "", ""))

    def test_find_existing_by_dir_succeeds_for_existing_virtualenvs(self):
        self.locator.root.child("bla").createDirectory()
        mem = MemoryPath(fs=self.fs, path=("foo", "bla",))
        stdin, stdout, stderr = self.run_cli(
            ["-d", mem.path, "--existing-only"],
        )
        self.assertEqual(
            (stdin, stdout, stderr),
            ("", self.locator.for_directory(mem).path + "\n", ""),
        )
