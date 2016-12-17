from unittest import TestCase

from bp.filepath import FilePath
from bp.memory import MemoryPath

from mkenv import find
from mkenv.tests.utils import CLIMixin


class TestFind(CLIMixin, TestCase):

    cli = find

    def test_find_directory_finds_envs_by_directory(self):
        this_dir = FilePath(__file__).parent()
        stdin, stdout, stderr = self.run_cli(["directory", this_dir.path])
        self.assertEqual(
            (stdin, stdout, stderr),
            ("", self.locator.for_directory(this_dir).path.path + "\n", ""),
        )

    def test_find_directory_defaults_to_cwd(self):
        stdin, stdout, stderr = self.run_cli(["directory"])
        self.assertEqual(
            (stdin, stdout, stderr), (
                "",
                self.locator.for_directory(FilePath(".")).path.path + "\n",
                "",
            ),
        )

    def test_find_name_finds_envs_by_name(self):
        stdin, stdout, stderr = self.run_cli(["name", "bla"])
        self.assertEqual(
            (stdin, stdout, stderr),
            ("", self.locator.for_name("bla").path.path + "\n", ""),
        )

    def test_find_without_args_finds_the_virtualenv_root(self):
        stdin, stdout, stderr = self.run_cli()
        self.assertEqual(
            (stdin, stdout, stderr), ("", self.locator.root.path + "\n", ""),
        )

    def test_find_directory_with_binary(self):
        this_dir = FilePath(__file__).parent()
        stdin, stdout, stderr = self.run_cli(
            ["directory", this_dir.path, "python"],
        )
        this_dir_venv = self.locator.for_directory(this_dir)
        self.assertEqual(
            (stdin, stdout, stderr), (
                "",
                this_dir_venv.binary("python").path + "\n",
                "",
            ),
        )

    def test_find_existing_by_name_fails_for_non_existing_virtualenvs(self):
        stdin, stdout, stderr = self.run_cli(
            ["--existing-only", "name", "bla"], exit_status=1,
        )
        self.assertEqual((stdin, stdout, stderr), ("", "", ""))

    def test_find_existing_by_name_succeeds_for_existing_virtualenvs(self):
        path = MemoryPath(fs=self.fs, path=("bla",))
        path.createDirectory()
        stdin, stdout, stderr = self.run_cli(
            ["--existing-only", "name", "bla"],
        )
        self.assertEqual(
            (stdin, stdout, stderr), (
                "",
                self.locator.for_name("bla").path.path + "\n",
                "",
            ),
        )

    def test_find_existing_by_dir_fails_for_non_existing_virtualenvs(self):
        stdin, stdout, stderr = self.run_cli(
            ["--existing-only", "directory", "/foo/bla"], exit_status=1,
        )
        self.assertEqual((stdin, stdout, stderr), ("", "", ""))

    def test_find_existing_by_dir_succeeds_for_existing_virtualenvs(self):
        self.locator.root.child("bla").createDirectory()
        mem = MemoryPath(fs=self.fs, path=("foo", "bla",))
        stdin, stdout, stderr = self.run_cli(
            ["--existing-only", "directory", mem.path],
        )
        self.assertEqual(
            (stdin, stdout, stderr), (
                "",
                self.locator.for_directory(mem).path.path + "\n",
                "",
            ),
        )

    def test_cannot_specify_random_garbage(self):
        stdin, stdout, stderr = self.run_cli(
            ["--random-garbage"], exit_status=2,
        )
        self.assertEqual(
            (stdin, stdout, stderr),
            ("", stdout, "Error: no such option: --random-garbage\n"),
        )
