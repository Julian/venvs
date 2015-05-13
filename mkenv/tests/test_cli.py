from StringIO import StringIO
from unittest import TestCase
import os

from mkenv._cli import (
    UsageError,
    Argument,
    CLI,
    CommandLine,
    Flag,
    Group,
    Option,
    Positional,
    Remainder,
)


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

    def test_non_boolean_store(self):
        cli = CLI(Argument(kind=Flag(names=("--foo",), store=12)))
        arguments = cli.parse(CommandLine(argv=["--foo"]))
        self.assertEqual(arguments, {"foo" : 12})

    def test_non_boolean_store_not_provided(self):
        cli = CLI(Argument(kind=Flag(names=("--foo",), store=12)))
        arguments = cli.parse(CommandLine(argv=[]))
        self.assertEqual(arguments, {"foo" : None})


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


class TestGroup(TestCase):
    def test_one_provided(self):
        cli = CLI(
            Group(
                members=[
                    Argument(kind=Option(names=("--foo",))),
                    Argument(kind=Option(names=("--bar",))),
                ],
            )
        )
        arguments = cli.parse(CommandLine(argv=["--foo", "bla"]))
        self.assertEqual(arguments, {"foo" : "bla", "bar" : None})

    def test_two_provided(self):
        cli = CLI(
            Group(
                members=[
                    Argument(kind=Option(names=("--foo",))),
                    Argument(kind=Option(names=("--bar",))),
                ],
            )
        )
        with self.assertRaises(UsageError) as e:
            cli.parse(CommandLine(argv=["--foo", "bla", "--bar", "quux"]))
        self.assertIn(
            "specify only one of '--foo' or '--bar'", str(e.exception),
        )

    def test_neither_provided(self):
        cli = CLI(
            Group(
                members=[
                    Argument(kind=Option(names=("--foo",))),
                    Argument(kind=Option(names=("--bar",))),
                ],
            )
        )
        arguments = cli.parse(CommandLine(argv=[]))
        self.assertEqual(arguments, {"foo" : None, "bar" : None})


class TestRemainder(TestCase):
    def test_provided_after_required_positional(self):
        cli = CLI(
            Argument(kind=Positional(name="argument")),
            remainder=Remainder(name="remaining"),
        )
        arguments = cli.parse(CommandLine(argv=["123", "--", "1", "2", "4"]))
        self.assertEqual(
            arguments, {"argument" : "123", "remaining" : ["1", "2", "4"]},
        )

    def test_not_provided_after_required_positional(self):
        cli = CLI(
            Argument(kind=Positional(name="argument")),
            remainder=Remainder(name="remaining"),
        )
        arguments = cli.parse(CommandLine(argv=["123"]))
        self.assertEqual(arguments, {"argument" : "123", "remaining" : []})

    def test_just_divider_after_required_positional(self):
        cli = CLI(
            Argument(kind=Positional(name="argument")),
            remainder=Remainder(name="remaining"),
        )
        arguments = cli.parse(CommandLine(argv=["123", "--"]))
        self.assertEqual(arguments, {"argument" : "123", "remaining" : []})
