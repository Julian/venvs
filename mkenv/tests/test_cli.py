from unittest import TestCase

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

    def test_bare_provided(self):
        cli = CLI(Argument(kind=Option(names=("--bar",))))
        arguments = cli.parse(CommandLine(argv=["--bar", "123"]))
        self.assertEqual(arguments, {"bar" : "123"})

    def test_bare_unprovided(self):
        cli = CLI(Argument(kind=Option(names=("--bar",), bare=lambda : "12")))
        arguments = cli.parse(CommandLine(argv=["--bar"]))
        self.assertEqual(arguments, {"bar" : "12"})

    def test_bare_multiconsumer_provided(self):
        cli = CLI(
            Argument(
                kind=Option(
                    names=("--bar",),
                    bare=lambda : ["a", "b", "c"],
                    consumes=3,
                ),
            ),
        )
        arguments = cli.parse(CommandLine(argv=["--bar", "2", "3", "4"]))
        self.assertEqual(arguments, {"bar" : ["2", "3", "4"]})

    def test_bare_multiconsumer_unprovided(self):
        cli = CLI(
            Argument(
                kind=Option(
                    names=("--bar",),
                    bare=lambda : ["a", "b", "c"],
                    consumes=3,
                ),
            ),
        )
        arguments = cli.parse(CommandLine(argv=["--bar"]))
        self.assertEqual(arguments, {"bar" : ["a", "b", "c"]})

    def test_bare_multiconsumer_underprovided(self):
        cli = CLI(
            Argument(
                kind=Option(
                    names=("--bar",),
                    bare=lambda : ["a", "b", "c"],
                    consumes=3,
                ),
            ),
        )
        with self.assertRaises(UsageError) as e:
            cli.parse(CommandLine(argv=["--bar", "2", "3"]))
        self.assertIn("'--bar' takes 3 argument(s)", str(e.exception))

    def test_bare_unprovided_before_another_option(self):
        cli = CLI(
            Argument(kind=Option(names=("--baz",))),
            Argument(kind=Option(names=("--bar",), bare=lambda : "11")),
        )
        arguments = cli.parse(CommandLine(argv=["--bar", "--baz", "22"]))
        self.assertEqual(arguments, {"bar" : "11", "baz" : "22"})


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
    def test_one_provided_option(self):
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

    def test_two_provided_options(self):
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

    def test_neither_option_provided(self):
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


class TestAsymmetricGroup(TestCase):
    cli = CLI(
        Group(
            members=[
                Argument(kind=Positional(name="foo"), required=False),
                Argument(kind=Flag(names=("--bar",))),
            ],
        )
    )

    def test_positional(self):
        arguments = self.cli.parse(CommandLine(argv=["123"]))
        self.assertEqual(arguments, {"foo" : "123", "bar" : False})

    def test_flag(self):
        arguments = self.cli.parse(CommandLine(argv=["--bar"]))
        self.assertEqual(arguments, {"foo" : None, "bar" : True})

    def test_both(self):
        with self.assertRaises(UsageError) as e:
            self.cli.parse(CommandLine(argv=["123", "--bar"]))
        self.assertIn("specify only one of 'foo' or '--bar'", str(e.exception))

    def test_neither(self):
        arguments = self.cli.parse(CommandLine(argv=[]))
        self.assertEqual(arguments, {"foo" : None, "bar" : False})


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


class TestCLI(TestCase):
    def test_defaults_are_set_per_dest(self):
        """
        Two arguments that set the same ``dest`` do not quash each other by
        overriding the ``dest`` with a default when one of the two are seen.

        """

        cli = CLI(
            Argument(kind=Flag(names=("-a",)), destination="foo"),
            Argument(kind=Flag(names=("-b",)), destination="foo"),
        )
        self.assertEqual(
            (
                cli.parse(CommandLine(argv=["-a"])),
                cli.parse(CommandLine(argv=["-b"])),
            ),
            ({"foo" : True}, {"foo" : True}),
        )
