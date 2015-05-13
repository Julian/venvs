"""
mkenv creates virtualenvs.

By default it places them in the appropriate data directory for your platform
(See `appdirs <https://pypi.python.org/pypi/appdirs>`_), but it will also
respect the :envvar:`WORKON_HOME` environment variable for compatibility with
:command:`mkvirtualenv`.

"""

from mkenv.common import _ROOT
from mkenv._cli import (
    CLI, Argument, Flag, Group, Option, Positional, Remainder,
)



@CLI(
    Group(
        members=[
            Argument(
                kind=Positional(name="name"),
                help="create a new named virtualenv",
            ),
            Argument(
                kind=Flag(names=("-t", "--temp", "--temporary")),
                help="create or reuse the global temporary virtualenv",
            ),
        ],
    ),
    Argument(
        kind=Flag(names=("-R", "--recreate")),
        help="recreate the virtualenv if it already exists",
    ),
    Argument(
        kind=Option(names=("-i", "--install")),
        dest="installs",
        repeat=True,
        help="install the given specifier (package) into the "
        "virtualenv with pip after it is created",
    ),
    Argument(
        kind=Option(names=("-r", "--requirement")),
        dest="requirements",
        repeat=True,
        help="install the given requirements file into the "
        "virtualenv with pip after it is created",
    ),
    _ROOT,
    remainder=Remainder(
        name="virtualenv-args",
        help="additional arguments to provide to virtualenv for creation",
    )
)
def run(arguments, stdin, stdout, stderr):
    if arguments.get("temporary"):
        virtualenv = arguments["locator"].temporary()
        act = virtualenv.recreate
    else:
        virtualenv = arguments["locator"].for_name(arguments["name"])
        if arguments["recreate"]:
            act = virtualenv.recreate
        else:
            act = virtualenv.create

    act(arguments=arguments["virtualenv-args"], stdout=stdout, stderr=stderr)
    virtualenv.install(
        packages=arguments["installs"],
        requirements=arguments["requirements"],
    )
