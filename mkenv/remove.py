import errno
import os

from mkenv._cli import CLI, Argument, Flag, Positional
from mkenv.common import _ROOT

from bp.errors import PathError


@CLI(
    Argument(
        kind=Positional(name="name"),
        help="remove the named virtualenv",
    ),
    Argument(
        kind=Flag(names=("-f", "--force")),
        help="ignore errors if the virtualenv does not exist",
    ),
    _ROOT,
)
def run(arguments, stdin, stdout, stderr):
    virtualenv = arguments["locator"].for_name(arguments["name"])
    try:
        virtualenv.remove()
    except PathError as error:
        if error.errno != errno.ENOENT:
            raise
        if not arguments["force"]:
            return os.EX_NOINPUT
