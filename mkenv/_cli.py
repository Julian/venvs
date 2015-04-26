from functools import wraps
import os
import pydoc
import sys

from mkenv import __version__


class UsageError(Exception):
    pass


class Argument(object):
    def __init__(self, names, help="", nargs=1, default=lambda : None):
        self.help = help
        self.names = names
        self.default = default
        self.nargs = nargs
        self.dest = max(names, key=len).lstrip("-")

    def consume(self, argv):
        dest, nargs = self.dest, self.nargs
        if nargs == 1:
            yield dest, next(argv)
        elif nargs == "?":
            yield dest, next(argv, self.default())
        else:
            yield dest, [next(argv) for _ in xrange(nargs)]



class Flag(object):
    def __init__(self, names, help="", store=True):
        self.help = help
        self.names = names
        self.dest = max(names, key=len).lstrip("-")
        self.store = store
        self.nargs = 0

    def consume(self, argv):
        return [(self.dest, self.store)]


HELP = Argument(names=set(["-h", "--help"]), help="Show usage information.")
VERSION = Argument(
    names=set(["-V", "--version"]), help="Show version information."
)


def cli(*accepted_arguments):

    names_to_arguments = {}
    for accepted_argument in (HELP, VERSION) + accepted_arguments:
        for name in accepted_argument.names:
            names_to_arguments[name] = accepted_argument

    def _make_cli(fn):
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
                arguments = parse(
                    accepts=names_to_arguments,
                    argv=argv,
                    help=help,
                    stdout=stdout,
                )
            except UsageError as error:
                stderr.write("error: ")
                stderr.write(str(error))
                stderr.write("\n\n")
                show_help(accepts=names_to_arguments, stdout=stdout, help=help)
                exit_status = os.EX_USAGE
            else:
                if arguments is None:
                    exit_status = os.EX_OK
                else:
                    exit_status = fn(
                        arguments=arguments,
                        stdin=stdin,
                        stdout=stdout,
                        stderr=stderr,
                    )
            exit(exit_status or os.EX_OK)
        return main
    return _make_cli


def parse(accepts, argv, help, stdout):
    argv = iter(argv)
    parsed = {}
    for argument in argv:
        found = accepts.get(argument)

        if found is None:
            raise UsageError("No such argument: " + repr(argument))

        if found == HELP:
            show_help(accepts=accepts, help=help, stdout=stdout)
            return
        elif found == VERSION:
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


def show_help(help, accepts, stdout):
    if help:
        stdout.write(help)
        stdout.write("\n\n")
    stdout.write("Usage:\n")

    for accepted_argument in set(accepts.itervalues()):
        stdout.write(
            "  {0:<20}        {1:<57}\n".format(
                ", ".join(accepted_argument.names),
                accepted_argument.help,
            )
        )
