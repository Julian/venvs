from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile
from unittest import TestCase
import os

from filesystems.exceptions import FileExists

from venvs import _config
from venvs.tests.utils import CLIMixin


class TestConverge(CLIMixin, TestCase):
    def test_it_creates_missing_virtualenvs(self):
        self.assertFalse(self.locator.for_name("a").exists_on(self.filesystem))
        self.assertFalse(self.locator.for_name("b").exists_on(self.filesystem))
        self.assertFalse(self.locator.for_name("c").exists_on(self.filesystem))

        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            [virtualenv.b]
            install = ["foo", "bar", "bla"]
            requirements = ["requirements.txt"]
            [virtualenv.c]
            install = ["foo", "$HOME", "~/a"]
            link = ["bar", "baz"]
            """,
        )

        self.run_cli(["converge"])

        self.assertEqual(
            (
                self.installed(self.locator.for_name("a")),
                self.installed(self.locator.for_name("b")),
                self.installed(self.locator.for_name("c")),
            ),
            (
                (set(), set()),
                ({"foo", "bar", "bla"}, {"requirements.txt"}),
                (
                    {
                        "foo",
                        os.path.expandvars("$HOME"),
                        os.path.expanduser("~/a"),
                    },
                    set(),
                ),
            ),
        )

    def test_it_converges_existing_virtualenvs(self):
        self.assertFalse(self.locator.for_name("a").exists_on(self.filesystem))
        self.assertFalse(self.locator.for_name("b").exists_on(self.filesystem))
        self.assertFalse(self.locator.for_name("c").exists_on(self.filesystem))

        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            install = ["foo", "bar"]
            requirements = ["requirements.txt"]
            """,
        )

        self.run_cli(["converge"])

        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            install = ["baz", "quux"]
            requirements = ["requirements.txt", "other.txt"]
            """,
        )

        self.run_cli(["converge"])

        self.assertEqual(
            self.installed(self.locator.for_name("a")),
            ({"baz", "quux"}, {"requirements.txt", "other.txt"}),
        )

    def test_it_converges_specified_virtualenvs(self):
        self.assertFalse(self.locator.for_name("a").exists_on(self.filesystem))
        self.assertFalse(self.locator.for_name("b").exists_on(self.filesystem))
        self.assertFalse(self.locator.for_name("c").exists_on(self.filesystem))

        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            [virtualenv.b]
            install = ["foo", "bar", "bla"]
            requirements = ["requirements.txt"]
            [virtualenv.c]
            install = ["foo"]
            link = ["bar", "baz"]
            """,
        )

        self.run_cli(["converge", "a", "c"])

        self.assertTrue(self.locator.for_name("a").exists_on(self.filesystem))
        self.assertFalse(self.locator.for_name("b").exists_on(self.filesystem))
        self.assertTrue(self.locator.for_name("c").exists_on(self.filesystem))

        self.assertEqual(
            (
                self.installed(self.locator.for_name("a")),
                self.installed(self.locator.for_name("b")),
                self.installed(self.locator.for_name("c")),
            ),
            (
                (set(), set()),
                (set(), set()),
                ({"foo"}, set()),
            ),
        )

    def test_it_runs_post_commands(self):
        self.assertFalse(self.locator.for_name("a").exists_on(self.filesystem))

        file = NamedTemporaryFile(delete=False)
        self.addCleanup(os.remove, file.name)
        mtime = os.path.getmtime(file.name)
        new_mtime = datetime.fromtimestamp(mtime) + timedelta(minutes=10)

        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            f"""
            [virtualenv.a]
            post-commands = [
                ["true"],
                ["touch", "-t", "{new_mtime:%Y%m%d%H%M}", "{file.name}"],
            ]
            """,
        )

        self.run_cli(["converge"])

        self.assertTrue(self.locator.for_name("a").exists_on(self.filesystem))
        self.assertGreater(os.path.getmtime(file.name), mtime)

    def test_it_does_not_run_post_commands_for_already_converged_envs(self):
        self.assertFalse(self.locator.for_name("a").exists_on(self.filesystem))

        file = NamedTemporaryFile(delete=False)
        self.addCleanup(os.remove, file.name)

        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            f"""
            [virtualenv.a]
            post-commands = [
                ["true"],
                ["touch", "{file.name}"],
            ]
            """,
        )

        self.run_cli(["converge"])
        mtime = os.path.getmtime(file.name)

        self.run_cli(["converge"])
        self.assertEqual(os.path.getmtime(file.name), mtime)

    def test_it_stops_post_commands_on_error(self):
        self.assertFalse(self.locator.for_name("a").exists_on(self.filesystem))

        file = NamedTemporaryFile(delete=False)
        self.addCleanup(os.remove, file.name)
        mtime = os.path.getmtime(file.name)

        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            f"""
            [virtualenv.a]
            post-commands = [
                ["false"],
                ["touch", "{file.name}"],
            ]
            """,
        )

        self.run_cli(["converge"])

        self.assertEqual(os.path.getmtime(file.name), mtime)

    def test_bundles(self):
        self.assertFalse(self.locator.for_name("a").exists_on(self.filesystem))

        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [bundle]
            dev = ["bar", "bla"]

            [virtualenv.a]
            install = ["foo"]
            install-bundle = ["dev"]
            """,
        )

        self.run_cli(["converge"])

        self.assertEqual(
            self.installed(self.locator.for_name("a")),
            ({"foo", "bar", "bla"}, set()),
        )

    def test_modifying_a_bundle_recreates_envs_using_it(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [bundle]
            dev = ["bar"]

            [virtualenv.a]
            install-bundle = ["dev"]
            """,
        )

        self.run_cli(["converge"])
        self.assertEqual(
            self.installed(self.locator.for_name("a")),
            ({"bar"}, set()),
        )

        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [bundle]
            dev = ["bar", "baz"]

            [virtualenv.a]
            install-bundle = ["dev"]
            """,
        )

        self.run_cli(["converge"])

        self.assertEqual(
            self.installed(self.locator.for_name("a")),
            ({"bar", "baz"}, set()),
        )

    def test_no_such_bundle(self):
        self.assertFalse(self.locator.for_name("a").exists_on(self.filesystem))

        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            install = ["foo"]
            install-bundle = ["dev"]
            """,
        )

        self.run_cli(["converge"])

        self.assertEqual(
            self.installed(self.locator.for_name("a")),
            (set(), set()),
        )

    def test_it_does_not_blow_up_by_default_on_install(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            [virtualenv.b]
            [virtualenv.magicExplodingVirtualenvOnInstall]
            [virtualenv.c]
            """,
        )

        self.run_cli(["converge"])

        self.assertEqual(
            (
                self.installed(self.locator.for_name("a")),
                self.installed(self.locator.for_name("b")),
                self.installed(self.locator.for_name("c")),
                self.locator.for_name("c").exists_on(self.filesystem),
            ),
            tuple((set(), set()) for _ in "abc") + (True,),
        )
        self.assertIn(
            "'magicExplodingVirtualenvOnInstall' failed",
            self.stderr.getvalue(),
        )

    def test_it_can_be_asked_to_blow_up_immediately_on_install(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            [virtualenv.b]
            [virtualenv.magicExplodingVirtualenvOnInstall]
            [virtualenv.c]
            """,
        )

        with self.assertRaises(ZeroDivisionError):
            self.run_cli(["converge", "--fail-fast"])

        self.assertEqual(
            (
                self.installed(self.locator.for_name("a")),
                self.installed(self.locator.for_name("b")),
                self.locator.for_name("c").exists_on(self.filesystem),
            ),
            ((set(), set()), (set(), set()), False),
        )

    def test_it_does_not_blow_up_by_default_on_create(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            [virtualenv.b]
            [virtualenv.magicExplodingVirtualenvOnCreate]
            [virtualenv.c]
            """,
        )

        self.run_cli(["converge"])

        self.assertEqual(
            (
                self.installed(self.locator.for_name("a")),
                self.installed(self.locator.for_name("b")),
                self.installed(self.locator.for_name("c")),
                self.locator.for_name("c").exists_on(self.filesystem),
            ),
            tuple((set(), set()) for _ in "abc") + (True,),
        )
        self.assertIn(
            "'magicExplodingVirtualenvOnCreate' failed",
            self.stderr.getvalue(),
        )

    def test_it_can_be_asked_to_blow_up_immediately_on_create(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            [virtualenv.b]
            [virtualenv.magicExplodingVirtualenvOnCreate]
            [virtualenv.c]
            """,
        )

        with self.assertRaises(ZeroDivisionError):
            self.run_cli(["converge", "--fail-fast"])

        self.assertEqual(
            (
                self.installed(self.locator.for_name("a")),
                self.installed(self.locator.for_name("b")),
                self.locator.for_name("c").exists_on(self.filesystem),
            ),
            ((set(), set()), (set(), set()), False),
        )

    def test_specified_python(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            python = "python3"
            """,
        )

        self.run_cli(["converge"])

        # FIXME: this doesn't properly assert about the python version...
        self.assertEqual(
            self.installed(self.locator.for_name("a")),
            (set(), set()),
        )

    def test_custom_link_dir(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            link = ["foo"]
            """,
        )

        link_dir = self.link_dir.descendant("some", "child", "bin")
        self.run_cli(["converge", "--link-dir", str(link_dir)])

        self.assertEqual(
            self.filesystem.readlink(link_dir / "foo"),
            self.locator.for_name("a").binary("foo"),
        )

    def test_link_exists(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            link = ["foo"]
            """,
        )

        self.filesystem.touch(self.link_dir.descendant("foo"))

        with self.assertRaises(FileExists):
            self.run_cli(["converge"])

    def test_link_exists_as_broken_symlink(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            link = ["foo"]
            """,
        )

        self.filesystem.link(
            source=self.link_dir.descendant("broken"),
            to=self.link_dir.descendant("foo"),
        )

        self.run_cli(["converge"])

        self.assertEqual(
            self.linked,
            {"foo": self.locator.for_name("a").binary("foo")},
        )

    def test_conflicting_links(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            link = ["foo"]

            [virtualenv.b]

            [virtualenv.c]
            link = ["foo"]
            """,
        )

        with self.assertRaises(_config.DuplicatedLinks) as e:
            self.run_cli(["converge"])

        self.assertIn("foo", str(e.exception))
        self.assertEqual(self.linked, {})

    def test_conflicting_links_via_rename(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            link = ["foo"]

            [virtualenv.b]

            [virtualenv.c]
            link = ["bar:foo"]
            """,
        )

        with self.assertRaises(_config.DuplicatedLinks) as e:
            self.run_cli(["converge"])

        self.assertIn("foo", str(e.exception))
        self.assertEqual(self.linked, {})

    def test_specified_link_name(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            link = ["foo:fooBar"]
            """,
        )

        self.run_cli(["converge"])

        self.assertEqual(
            self.linked,
            {"fooBar": self.locator.for_name("a").binary("foo")},
        )

    def test_missing_link_dir(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            link = ["foo"]
            """,
        )

        self.filesystem.remove_empty_directory(self.link_dir)
        self.assertFalse(self.filesystem.is_dir(path=self.link_dir))

        self.run_cli(["converge"])

        self.assertEqual(
            self.linked,
            {"foo": self.locator.for_name("a").binary("foo")},
        )

    def test_link_m_module(self):
        """
        It links modules run via -m as wrappers.
        """
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            link-module = ["this"]
            """,
        )

        self.run_cli(["converge"])

        contents = self.filesystem.get_contents(
            self.link_dir.descendant("this"),
        )
        self.assertEqual(
            contents.splitlines()[0],
            "#!" + str(self.locator.for_name("a").binary("python")),
        )

    def test_link_m_module_specified_name(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            link-module = ["this:that"]
            """,
        )

        self.run_cli(["converge"])

        contents = self.filesystem.get_contents(
            self.link_dir.descendant("that"),
        )
        self.assertEqual(
            contents.splitlines()[0],
            "#!" + str(self.locator.for_name("a").binary("python")),
        )

    def test_link_m_module_duplicated(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            link = ["foo"]

            [virtualenv.b]

            [virtualenv.c]
            link-module = ["bar:foo"]
            """,
        )

        with self.assertRaises(_config.DuplicatedLinks) as e:
            self.run_cli(["converge"])

        self.assertIn("foo", str(e.exception))
        self.assertEqual(self.linked, {})

    def test_link_m_module_replaces_generated_files(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            link-module = ["this"]
            """,
        )

        self.run_cli(["converge"])

        # Just change the config in a way that will re-converge
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            link-module = ["this", "that"]
            """,
        )

        self.run_cli(["converge"])

    def test_link_m_module_does_not_replace_non_venvs_wrappers(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            link-module = ["this"]
            """,
        )

        self.filesystem.touch(self.link_dir.descendant("this"))

        with self.assertRaises(FileExists):
            self.run_cli(["converge"])

    def test_linking_the_same_binary_twice(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            link = ["this:that", "this"]
            """,
        )

        self.run_cli(["converge"])

        this = self.locator.for_name("a").binary("this")
        self.assertEqual(self.linked, dict(this=this, that=this))

    def test_changing_a_bundle_recreates_the_venv(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [bundle]
            one = ["foo"]

            [virtualenv.a]
            install-bundle = ["one"]
            """,
        )
        self.run_cli(["converge"])
        self.assertEqual(
            self.installed(self.locator.for_name("a")),
            ({"foo"}, set()),
        )

        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [bundle]
            one = ["foo", "bar"]

            [virtualenv.a]
            install-bundle = ["one"]
            """,
        )

        self.run_cli(["converge"])

        self.assertEqual(
            self.installed(self.locator.for_name("a")),
            ({"foo", "bar"}, set()),
        )

    def test_missing_config_recreates_the_venv(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            """,
        )
        self.run_cli(["converge"])

        venv = self.locator.for_name("a")
        self.filesystem.remove_file(venv.path / "installed.json")

        some_random_file = venv.path / "some-random-file"
        self.filesystem.touch(some_random_file)
        self.assertTrue(self.filesystem.is_file(some_random_file))

        # Now the file should disappear as the venv gets recreated
        self.run_cli(["converge"])
        self.assertFalse(self.filesystem.is_file(some_random_file))

    def test_invalid_config_recreates_the_venv(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            """,
        )
        self.run_cli(["converge"])

        venv = self.locator.for_name("a")
        self.filesystem.set_contents(
            venv.path / "installed.json",
            "not even json",
        )

        some_random_file = venv.path / "some-random-file"
        self.filesystem.touch(some_random_file)
        self.assertTrue(self.filesystem.is_file(some_random_file))

        # Now the file should disappear as the venv gets recreated
        self.run_cli(["converge"])
        self.assertFalse(self.filesystem.is_file(some_random_file))

    def test_valid_json_invalid_config_recreates_the_venv(self):
        self.filesystem.set_contents(
            self.locator.root.descendant("virtualenvs.toml"),
            """
            [virtualenv.a]
            """,
        )
        self.run_cli(["converge"])

        venv = self.locator.for_name("a")
        self.filesystem.set_contents(venv.path / "installed.json", "{}")

        some_random_file = venv.path / "some-random-file"
        self.filesystem.touch(some_random_file)
        self.assertTrue(self.filesystem.is_file(some_random_file))

        # Now the file should disappear as the venv gets recreated
        self.run_cli(["converge"])
        self.assertFalse(self.filesystem.is_file(some_random_file))
