from functools import wraps
import os
import pydoc
import sys

from characteristic import Attribute, attributes

from mkenv import __version__


class UsageError(Exception):
    pass


@attributes(
    [
        Attribute(name="names"),
        Attribute(name="help", default_value="", exclude_from_repr=True),
        Attribute(name="type", default_value=lambda value : value),
        Attribute(
            name="default",
            default_value=lambda : None,
            exclude_from_repr=True,
        ),
    ],
)
class Argument(object):
    def __init__(self, kind, dest=None, nargs=None):
        self.kind = kind

        if dest is None:
            dest = max(self.names, key=len).lstrip("-")
        self.dest = dest

        if nargs is None:
            nargs = getattr(kind, "nargs", 1)
        self.nargs = nargs

    def consume(self, command_line):
        dest, nargs = self.dest, self.nargs

        if nargs == 1:
            value = self.type(next(command_line))
        elif nargs == "?":
            argument = next(command_line, None)
            if argument is None:
                value = self.default()
            else:
                value = self.type(argument)
        else:
            value = [self.type(next(command_line)) for _ in xrange(nargs)]

        return [(dest, self.prepare(value))]

    def prepare(self, argument_value):
        return getattr(self.kind, "prepare", lambda arg : arg)(argument_value)

    def register(self):
        if self.kind.is_positional:
            return (self,), ()
        else:
            return (), [(name, self) for name in self.names]

    def emit_default(self):
        return [(self.dest, self.default())]

    def format_help(self):
        return "  {names:<20}        {self.help:<57}\n".format(
            names=", ".join(self.names),
            self=self,
        )


@attributes([Attribute(name="store", default_value=True)])
class Flag(object):
    is_positional = False
    nargs = 0

    def prepare(self, argument_value):
        return self.store


@attributes([])
class Option(object):
    is_positional = False


@attributes([])
class Positional(object):
    is_positional = True


@attributes([Attribute(name="members")], apply_with_cmp=False)
class Group(object):
    def register(self):
        return [], [
            (name, _Exclusivity.wrap(group=self, argument=nonpositional))
            for argument in self.members
            for name, nonpositional in argument.register()[1]
        ]

    def format_help(self):
        body = "".join(member.format_help() for member in self.members)
        return "\n" + body + "\n"

    def emit_default(self):
        # TODO: probably something different for required groups
        return []


@attributes([Attribute(name="argument"), Attribute(name="group")])
class _Exclusivity(object):
    def __init__(self):
        self.names = self.argument.names

    @classmethod
    def wrap(cls, argument, group):
        return cls(argument=argument, group=group)

    def consume(self, command_line):
        state = command_line.state.setdefault(self.group, {})
        seen = state.get("seen")
        if seen is not None:
            raise UsageError(
                "specify only one of {0!r} or {1!r}".format(
                    " / ".join(seen.names), " / ".join(self.argument.names),
                )
            )
        else:
            state["seen"] = self.argument
            return self.argument.consume(command_line=command_line)


class CLI(object):

    HELP = Argument(
        Option(),
        names=("-h", "--help"),
        help="Show usage information.",
    )
    VERSION = Argument(
        Option(),
        names=("-V", "--version"),
        help="Show version information."
    )

    def __init__(self, *argspec):
        self._nonpositionals = nonpositionals = {}
        self._positionals = positionals = []

        for argument in (self.HELP, self.VERSION) + argspec:
            for_positionals, for_nonpositionals = argument.register()
            positionals.extend(for_positionals)
            nonpositionals.update(for_nonpositionals)

        self.argspec = argspec

    def __call__(self, fn):
        @wraps(fn)
        def main(
            command_line=None,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
            exit=sys.exit,
            arguments=None,
        ):
            if command_line is None:
                command_line = CommandLine()
            if arguments is None:
                arguments = {}

            help, _ = pydoc.splitdoc(pydoc.getdoc(fn))
            try:
                parsed = self.parse(
                    command_line=command_line,
                    help=help,
                    stdout=stdout,
                )
            except UsageError as error:
                stderr.write("error: ")
                stderr.write(str(error))
                stderr.write("\n\n")
                self.show_help(stdout=stdout, help=help)
                exit_status = os.EX_USAGE
            else:
                if parsed is None:
                    exit_status = os.EX_OK
                else:
                    parsed.update(arguments)
                    exit_status = main.with_arguments(
                        arguments=parsed,
                        stdin=stdin,
                        stdout=stdout,
                        stderr=stderr,
                    )
            exit(exit_status or os.EX_OK)
        main.with_arguments = fn
        return main

    def parse(self, command_line, help, stdout):
        parsed = {}
        seen = set()
        positionals = iter(self._positionals)
        nonpositionals = self._nonpositionals

        for argument in command_line:
            if not argument.startswith("-"):
                found = next(positionals, None)
                if found is None:
                    raise UsageError("No such argument: " + repr(argument))
                parsed[found.dest] = argument
                seen.add(found)
                continue

            found = nonpositionals.get(argument)

            if found is None:
                raise UsageError("No such argument: " + repr(argument))

            if found in seen:
                name = " / ".join(found.names)
                raise UsageError("{0!r} specified multiple times".format(name))
            seen.add(found)

            if found == CLI.HELP:
                self.show_help(help=help, stdout=stdout)
                return
            elif found == CLI.VERSION:
                stdout.write(__version__)
                stdout.write("\n")
                return
            else:
                try:
                    parsed.update(found.consume(command_line=command_line))
                except StopIteration:
                    message = "{0} takes {1} argument(s)"
                    raise UsageError(message.format(argument, found.nargs))

        for argument in self.argspec:
            if argument not in seen:
                parsed.update(argument.emit_default())
        return parsed

    def show_help(self, help, stdout):
        if help:
            stdout.write(help)
            stdout.write("\n\n")
        stdout.write(self.concise_usage())
        stdout.write("\n\nUsage:\n")

        for argument in self.argspec:
            stdout.write(argument.format_help())

    def concise_usage(self):
        return "findenv"


@attributes([Attribute(name="argv", default_factory=lambda : sys.argv[1:])])
class CommandLine(object):
    def __init__(self):
        self.remaining = iter(self.argv)
        self.state = {}

    def __iter__(self):
        return self

    def next(self):
        return next(self.remaining)
