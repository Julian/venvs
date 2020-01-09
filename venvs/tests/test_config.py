from unittest import TestCase
import os
import sys

import tomlkit.exceptions

from venvs import _config


class TestConfig(TestCase):
    def test_simple(self):
        config = _config.Config.from_string(
            """
            [virtualenv.a]
            [virtualenv.b]
            install = ["foo", "bar", "bla"]
            """,
        )
        self.assertEqual(
            list(config), [
                (
                    "a", {
                        "install": [],
                        "requirements": [],
                        "link": {},
                        "link-module": {},
                        "python": sys.executable,
                    },
                ),
                (
                    "b", {
                        "install": ["foo", "bar", "bla"],
                        "requirements": [],
                        "link": {},
                        "link-module": {},
                        "python": sys.executable,
                    },
                ),
            ],
        )

    def test_links(self):
        config = _config.Config.from_string(
            """
            [virtualenv.a]
            link = ["foo", "bar", "baz:quux"]
            link-module = ["spam", "eggs:cheese"]
            """,
        )
        self.assertEqual(
            list(config), [
                (
                    "a", {
                        "install": [],
                        "requirements": [],
                        "link": {"foo": "foo", "bar": "bar", "baz": "quux"},
                        "link-module": {"spam": "spam", "eggs": "cheese"},
                        "python": sys.executable,
                    },
                ),
            ],
        )

    def test_bundles(self):
        config = _config.Config.from_string(
            """
            [bundle]
            one = ["foo", "bar"]

            [virtualenv.a]
            install-bundle = ["one"]

            [virtualenv.b]
            install-bundle = ["one"]
            install = ["bar", "baz"]
            """,
        )
        self.assertEqual(
            list(config), [
                (
                    "a", {
                        "install": ["foo", "bar"],
                        "requirements": [],
                        "link": {},
                        "link-module": {},
                        "python": sys.executable,
                    },
                ),
                (
                    "b", {
                        "install": ["bar", "baz", "foo"],
                        "requirements": [],
                        "link": {},
                        "link-module": {},
                        "python": sys.executable,
                    },
                ),
            ],
        )

    def test_no_such_bundle(self):
        config = _config.Config.from_string(
            """
            [virtualenv.a]
            install-bundle = ["one"]
            """,
        )
        with self.assertRaises(tomlkit.exceptions.NonExistentKey) as e:
            next(iter(config))
        self.assertIn('"one"', str(e.exception))

    def test_expansion(self):
        config = _config.Config.from_string(
            """
            [virtualenv.a]
            install = ["~/a", "$HOME", "${HOME}/b"]
            requirements = ["requirements-${HOME}.txt"]
            """,
        )
        self.assertEqual(
            list(config), [
                (
                    "a", {
                        "install": [
                            os.path.expanduser("~/a"),
                            os.path.expandvars("$HOME"),
                            os.path.expandvars("${HOME}/b"),
                        ],
                        "requirements": [
                            os.path.expandvars("requirements-${HOME}.txt"),
                        ],
                        "link": {},
                        "link-module": {},
                        "python": sys.executable,
                    },
                ),
            ],
        )

    def test_explicit_python(self):
        config = _config.Config.from_string(
            """
            [virtualenv.a]
            install = ["foo"]
            python = "somepython2"
            """,
        )
        self.assertEqual(
            list(config), [
                (
                    "a", {
                        "install": ["foo"],
                        "requirements": [],
                        "link": {},
                        "link-module": {},
                        "python": "somepython2",
                    },
                ),
            ],
        )

    def test_duplicate_links(self):
        with self.assertRaises(_config.DuplicatedLinks):
            _config.Config.from_string(
                """
                [virtualenv.a]
                link = ["python:foo", "pip:foo"]
                """,
            )

    def test_duplicate_links_across_venvs(self):
        with self.assertRaises(_config.DuplicatedLinks):
            _config.Config.from_string(
                """
                [virtualenv.a]
                link = ["python:foo"]
                [virtualenv.b]
                link = ["pip:foo"]
                """,
            )

    def test_duplicate_link_modules(self):
        with self.assertRaises(_config.DuplicatedLinks):
            _config.Config.from_string(
                """
                [virtualenv.a]
                link-module = ["pydoc:foo", "pip:foo"]
                """,
            )

    def test_duplicate_link_modules_across_venvs(self):
        with self.assertRaises(_config.DuplicatedLinks):
            _config.Config.from_string(
                """
                [virtualenv.a]
                link-module = ["pydoc:foo"]
                [virtualenv.b]
                link-module = ["pip:foo"]
                """,
            )

    def test_duplicate_mixed_links(self):
        with self.assertRaises(_config.DuplicatedLinks):
            _config.Config.from_string(
                """
                [virtualenv.a]
                link = ["python:foo"]
                link-module = ["pip:foo"]
                """,
            )

    def test_duplicate_mixed_links_across_venvs(self):
        with self.assertRaises(_config.DuplicatedLinks):
            _config.Config.from_string(
                """
                [virtualenv.a]
                link-module = ["pydoc:foo"]
                [virtualenv.b]
                link = ["pip:foo"]
                """,
            )

    def test_add_with_contents(self):
        config = _config.Config()
        added = config.add("a", install=["foo", "bar"], link=["baz"])
        self.assertEqual(
            (list(config), list(added)),
            (
                [],
                [
                    (
                        "a", {
                            "install": ["foo", "bar"],
                            "requirements": [],
                            "link": {"baz": "baz"},
                            "link-module": {},
                            "python": sys.executable,
                        },
                    ),
                ],
            )
        )

    def test_add_empty(self):
        config = _config.Config()
        added = config.add("a")
        self.assertEqual(
            (list(config), list(added)),
            (
                [],
                [
                    (
                        "a", {
                            "install": [],
                            "requirements": [],
                            "link": {},
                            "link-module": {},
                            "python": sys.executable,
                        },
                    ),
                ],
            )
        )

    def test_empty(self):
        config = _config.Config()
        self.assertEqual(list(config), [])

    def test_empty_from_string(self):
        config = _config.Config.from_string("")
        self.assertEqual(config, _config.Config())
