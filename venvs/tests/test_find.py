import os
from unittest import TestCase

from filesystems import Path

from venvs import find
from venvs.tests.utils import CLIMixin


class TestFind(CLIMixin, TestCase):

    cli = find

    def test_find_directory_finds_envs_by_directory(self):
        this_dir = Path.from_string(__file__).parent()
        stdout, stderr = self.run_cli(["directory", str(this_dir)])
        self.assertEqual(
            (stdout, stderr),
            (str(self.locator.for_directory(this_dir).path) + "\n", ""),
        )

    def test_find_directory_defaults_to_cwd(self):
        stdout, stderr = self.run_cli(["directory"])
        self.assertEqual(
            (stdout, stderr), (
                str(self.locator.for_directory(Path.cwd()).path) + "\n",
                "",
            ),
        )

    def test_find_name_finds_envs_by_name(self):
        stdout, stderr = self.run_cli(["name", "bla"])
        self.assertEqual(
            (stdout, stderr),
            (str(self.locator.for_name("bla").path) + "\n", ""),
        )

    def test_find_without_args_finds_the_virtualenv_root(self):
        stdout, stderr = self.run_cli()
        self.assertEqual(
            (stdout, stderr),
            (str(self.locator.root) + os.linesep, ""),
        )

    def test_find_directory_with_binary(self):
        this_dir = Path.from_string(__file__).parent()
        stdout, stderr = self.run_cli(
            ["directory", str(this_dir), "python"],
        )
        this_dir_venv = self.locator.for_directory(this_dir)
        self.assertEqual(
            (stdout, stderr),
            (str(this_dir_venv.binary("python")) + "\n", ""),
        )

    def test_find_existing_by_name_fails_for_non_existing_virtualenvs(self):
        stdout, stderr = self.run_cli(
            ["--existing-only", "name", "bla"], exit_status=1,
        )
        self.assertEqual((stdout, stderr), ("", ""))

    def test_find_existing_by_name_succeeds_for_existing_virtualenvs(self):
        self.filesystem.create_directory(self.locator.root / "bla")

        stdout, stderr = self.run_cli(
            ["--existing-only", "name", "bla"],
        )
        self.assertEqual(
            (stdout, stderr),
            (str(self.locator.for_name("bla").path) + "\n", ""),
        )

    def test_find_existing_by_dir_fails_for_non_existing_virtualenvs(self):
        stdout, stderr = self.run_cli(
            ["--existing-only", "directory", "/foo/bla"], exit_status=1,
        )
        self.assertEqual((stdout, stderr), ("", ""))

    def test_find_existing_by_dir_succeeds_for_existing_virtualenvs(self):
        self.filesystem.create_directory(self.locator.root / "bla")

        path = Path("foo", "bla")
        stdout, stderr = self.run_cli(
            ["--existing-only", "directory", str(path)],
        )
        self.assertEqual(
            (stdout, stderr),
            (str(self.locator.for_directory(path).path) + "\n", ""),
        )

    def test_cannot_specify_random_garbage(self):
        stdout, stderr = self.run_cli(
            ["--random-garbage"], exit_status=2,
        )
        stderr_ends_with = "Error: no such option: --random-garbage\n"
        self.assertEqual(
            (stdout, stderr[-len(stderr_ends_with):]),
            (stdout, stderr_ends_with),
        )
