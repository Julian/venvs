from mkenv._cli import CLI, Argument, Positional
from mkenv.common import _ROOT


@CLI(
    Argument(
        kind=Positional(name="name"),
        help="remove the named virtualenv",
    ),
    _ROOT,
)
def run(arguments, stdin, stdout, stderr):
    virtualenv = arguments["locator"].for_name(arguments["name"])
    virtualenv.remove()
