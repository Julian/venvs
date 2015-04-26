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
        Attribute(name="help", default_value=""),
        Attribute(name="nargs", default_value=1),
        Attribute(name="type", default_value=lambda value : value),
        Attribute(name="default", default_value=lambda : None),
    ],
)
class Argument(object):
    def __init__(self, dest=None):
        if dest is None:
            dest = max(self.names, key=len).lstrip("-")
        self.dest = dest

    def consume(self, argv):
        dest, nargs = self.dest, self.nargs
        if nargs == 1:
            yield dest, self.type(next(argv))
        elif nargs == "?":
            argument = next(argv, None)
            if argument is None:
                argument = self.default()
            else:
                argument = self.type(argument)
            yield dest, argument
        else:
            yield dest, [self.type(next(argv)) for _ in xrange(nargs)]


@attributes(
    [
        Attribute(name="names"),
        Attribute(name="help", default_value=""),
        Attribute(name="store", default_value=True),
    ],
)
class Flag(object):

    nargs = 0

    def __init__(self, dest=None):
        if dest is None:
            dest = max(self.names, key=len).lstrip("-")
        self.dest = dest

    def consume(self, argv):
        return [(self.dest, self.store)]


class CLI(object):

    HELP = Argument(names=("-h", "--help"), help="Show usage information.")
    VERSION = Argument(
        names=("-V", "--version"), help="Show version information."
    )

    def __init__(self, *accepted_arguments):
        self._names_to_arguments = names_to_arguments = {}
        self._positional_arguments = positional_arguments = []

        for accepted in (self.HELP, self.VERSION) + accepted_arguments:
            if is_positional(accepted):
                positional_arguments.append(accepted)
            else:
                for name in accepted.names:
                    names_to_arguments[name] = accepted

        self.accepted_arguments = accepted_arguments

    def __call__(self, fn):
        @wraps(fn)
        def main(
            argv=None,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
            exit=sys.exit,
            arguments=None,
        ):
            if argv is None:
                argv = sys.argv[1:]
            if arguments is None:
                arguments = {}

            help, _ = pydoc.splitdoc(pydoc.getdoc(fn))
            try:
                parsed = self.parse(argv=argv, help=help, stdout=stdout)
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
                    arguments.update(parsed)
                    exit_status = main.with_arguments(
                        arguments=arguments,
                        stdin=stdin,
                        stdout=stdout,
                        stderr=stderr,
                    )
            exit(exit_status or os.EX_OK)
        main.with_arguments = fn
        return main

    def parse(self, argv, help, stdout):
        argv = iter(argv)

        parsed = {}
        positional, seen = iter(self._positional_arguments), set()

        for argument in argv:
            if not argument.startswith("-"):
                found = next(positional, None)
                if found is None:
                    raise UsageError("No such argument: " + repr(argument))
                parsed[found.dest] = argument
                continue

            found = self._names_to_arguments.get(argument)

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
                    parsed.update(found.consume(argv))
                except StopIteration:
                    message = "{0} takes {1} argument(s)"
                    raise UsageError(message.format(argument, found.nargs))
        return parsed

    def show_help(self, help, stdout):
        if help:
            stdout.write(help)
            stdout.write("\n\n")
        stdout.write("Usage:\n")

        for accepted_argument in self.accepted_arguments:
            stdout.write(
                "  {0:<20}        {1:<57}\n".format(
                    ", ".join(accepted_argument.names),
                    accepted_argument.help,
                )
            )


def is_positional(argument):
    return not any(name.startswith("-") for name in argument.names)
