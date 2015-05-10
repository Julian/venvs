from StringIO import StringIO
from unittest import TestCase
import os

from mkenv._cli import Argument, CLI, CommandLine, Positional


class TestCLI(TestCase):
    def test_single_positional(self):
        cli = CLI(Argument(kind=Positional(name="first")))
        arguments = cli.parse(CommandLine(argv=["argument"]), help="")
        self.assertEqual(arguments, {"first" : "argument"})
