from StringIO import StringIO
from unittest import TestCase
import os

from mkenv._cli import Argument, CLI, CommandLine, Flag, Positional


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
