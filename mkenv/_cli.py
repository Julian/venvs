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

    HELP = Argument(names=set(["-h", "--help"]), help="Show usage information.")
    VERSION = Argument(
        names=set(["-V", "--version"]), help="Show version information."
    )

    def __init__(self, *accepted_arguments):
        self.names_to_arguments = names_to_arguments = {}
        for accepted in (self.HELP, self.VERSION) + accepted_arguments:
            for name in accepted.names:
                names_to_arguments[name] = accepted

    def __call__(self, fn):
        @wraps(fn)
        def main(
            argv=None,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
            exit=sys.exit,
        ):
            if argv is None:
                argv = sys.argv[1:]
            help, _ = pydoc.splitdoc(pydoc.getdoc(fn))

            try:
                arguments = self.parse(argv=argv, help=help, stdout=stdout)
            except UsageError as error:
                stderr.write("error: ")
                stderr.write(str(error))
                stderr.write("\n\n")
                self.show_help(stdout=stdout, help=help)
                exit_status = os.EX_USAGE
            else:
                if arguments is None:
                    exit_status = os.EX_OK
                else:
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
        for argument in argv:
            found = self.names_to_arguments.get(argument)

            if found is None:
                raise UsageError("No such argument: " + repr(argument))

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
                    raise UsageError(
                        "{0} takes {1} argument(s)".format(argument, found.nargs),
                    )
        return parsed

    def show_help(self, help, stdout):
        if help:
            stdout.write(help)
            stdout.write("\n\n")
        stdout.write("Usage:\n")

        for accepted_argument in set(self.names_to_arguments.itervalues()):
            stdout.write(
                "  {0:<20}        {1:<57}\n".format(
                    ", ".join(accepted_argument.names),
                    accepted_argument.help,
                )
            )
