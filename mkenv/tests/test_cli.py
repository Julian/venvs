from StringIO import StringIO
from unittest import TestCase
import os

from mkenv._cli import (
    UsageError, Argument, CLI, CommandLine, Flag, Option, Positional,
)


class TestPositional(TestCase):
    def test_properly_provided(self):
        cli = CLI(Argument(kind=Positional(name="first")))
        arguments = cli.parse(CommandLine(argv=["argument"]))
        self.assertEqual(arguments, {"first" : "argument"})


class TestFlag(TestCase):
    def test_provided(self):
        cli = CLI(Argument(kind=Flag(names=("--flag",))))
        arguments = cli.parse(CommandLine(argv=["--flag"]))
        self.assertEqual(arguments, {"flag" : True})

    def test_not_provided(self):
        cli = CLI(Argument(kind=Flag(names=("--flag",))))
        arguments = cli.parse(CommandLine(argv=[]))
        self.assertEqual(arguments, {"flag" : False})

    def test_different_store(self):
        cli = CLI(Argument(kind=Flag(names=("--foo",), store=False)))
        arguments = cli.parse(CommandLine(argv=["--foo"]))
        self.assertEqual(arguments, {"foo" : False})

    def test_different_store_not_provided(self):
        cli = CLI(Argument(kind=Flag(names=("--foo",), store=False)))
        arguments = cli.parse(CommandLine(argv=[]))
        self.assertEqual(arguments, {"foo" : True})


class TestOption(TestCase):
    def test_provided(self):
        cli = CLI(Argument(kind=Option(names=("--foo",))))
        arguments = cli.parse(CommandLine(argv=["--foo", "bar"]))
        self.assertEqual(arguments, {"foo" : "bar"})

    def test_not_provided(self):
        cli = CLI(Argument(kind=Option(names=("--foo",))))
        arguments = cli.parse(CommandLine(argv=[]))
        self.assertEqual(arguments, {"foo" : None})


class TestPositional(TestCase):
    def test_provided(self):
        cli = CLI(Argument(kind=Positional(name="foo")))
        arguments = cli.parse(CommandLine(argv=["bla"]))
        self.assertEqual(arguments, {"foo" : "bla"})

    def test_not_provided(self):
        cli = CLI(Argument(kind=Positional(name="foo")))
        with self.assertRaises(UsageError) as e:
            cli.parse(CommandLine(argv=[]))
        self.assertIn("'foo' is required", str(e.exception))
