from StringIO import StringIO
from unittest import TestCase
import os

from bp.filepath import FilePath
from bp.memory import MemoryPath

from mkenv import find
from mkenv._cli import CommandLine
from mkenv.tests.utils import CLIMixin


class TestFind(CLIMixin, TestCase):

    cli = find

    def test_find_d_finds_envs_by_directory(self):
        this_dir = FilePath(__file__).parent()
        stdin, stdout, stderr = self.run_cli(["-d", this_dir.path])
        self.assertEqual(
            (stdin, stdout, stderr),
            ("", self.locator.for_directory(this_dir).path.path + "\n", ""),
        )

    def test_find_d_defaults_to_cwd(self):
        stdin, stdout, stderr = self.run_cli(["-d"])
        self.assertEqual(
            (stdin, stdout, stderr), (
                "",
                self.locator.for_directory(FilePath(".")).path.path + "\n",
                "",
            ),
        )

    def test_find_n_finds_envs_by_name(self):
        stdin, stdout, stderr = self.run_cli(["-n", "bla"])
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
        stdin, stdout, stderr = self.run_cli(["-d", this_dir.path, "python"])
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
            ["-n", "bla", "--existing-only"], exit_status=1,
        )
        self.assertEqual((stdin, stdout, stderr), ("", "", "")) 

    def test_find_existing_by_name_succeeds_for_existing_virtualenvs(self):
        path = MemoryPath(fs=self.fs, path=("bla",))
        path.createDirectory()
        stdin, stdout, stderr = self.run_cli(["-n", "bla", "--existing-only"])
        self.assertEqual(
            (stdin, stdout, stderr), (
                "",
                self.locator.for_name("bla").path.path + "\n",
                "",
            ),
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
            (stdin, stdout, stderr), (
                "",
                self.locator.for_directory(mem).path.path + "\n",
                "",
            ),
        )

    def test_cannot_specify_name_twice(self):
        stdin, stdout, stderr = self.run_cli(
            ["-n", "foo", "-n", "bar"], exit_status=os.EX_USAGE,
        )
        self.assertEqual(
            (stdin, stdout, stderr),
            ("", stdout, "error: '-n / --name' specified multiple times\n\n"),
        )

    def test_cannot_specify_name_twice_in_two_ways(self):
        stdin, stdout, stderr = self.run_cli(
            ["-n", "foo", "--name", "bar"], exit_status=os.EX_USAGE,
        )
        self.assertEqual(
            (stdin, stdout, stderr),
            ("", stdout, "error: '-n / --name' specified multiple times\n\n"),
        )

    def test_cannot_specify_directory_twice(self):
        stdin, stdout, stderr = self.run_cli(
            ["-d", "foo", "-d", "bar"], exit_status=os.EX_USAGE,
        )
        self.assertEqual(
            (stdin, stdout, stderr), (
                "",
                stdout,
                "error: '-d / --directory' specified multiple times\n\n",
            ),
        )

    def test_cannot_specify_directory_twice_in_two_ways(self):
        stdin, stdout, stderr = self.run_cli(
            ["-d", "foo", "--directory", "bar"], exit_status=os.EX_USAGE,
        )
        self.assertEqual(
            (stdin, stdout, stderr), (
                "",
                stdout,
                "error: '-d / --directory' specified multiple times\n\n",
            ),
        )

    def test_cannot_specify_both_name_and_directory(self):
        stdin, stdout, stderr = self.run_cli(
            ["-n", "foo", "--directory", "bar"], exit_status=os.EX_USAGE,
        )
        self.assertEqual(
            (stdin, stdout, stderr), (
                "",
                stdout,
                "error: specify only one of "
                "'-n / --name' or '-d / --directory'\n\n",
            ),
        )

    def test_cannot_specify_random_garbage(self):
        stdin, stdout, stderr = self.run_cli(
            ["--random-garbage"], exit_status=os.EX_USAGE,
        )
        self.assertEqual(
            (stdin, stdout, stderr),
            ("", stdout, "error: no such argument '--random-garbage'\n\n"),
        )


class TestIntegration(TestCase):
    def test_it_works(self):
        with self.assertRaises(SystemExit) as e:
            find.run(CommandLine(argv=["mkenv"]), stdout=StringIO())
        self.assertEqual(e.exception.args, (0,))
