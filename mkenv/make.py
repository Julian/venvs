"""
mkenv creates virtualenvs.

By default it places them in the appropriate data directory for your platform
(See `appdirs <https://pypi.python.org/pypi/appdirs>`_), but it will also
respect the :envvar:`WORKON_HOME` environment variable for compatibility with
:command:`mkvirtualenv`.

"""

import sysconfig

from bp.filepath import FilePath
from packaging.requirements import Requirement
import click

from mkenv.common import _ROOT


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@_ROOT
@click.option(
    "-i", "--install", "installs",
    multiple=True,
    help=(
        "install the given specifier (package) into the "
        "virtualenv with pip after it is created"
    ),
)
@click.option(
    "-l", "--link", "links",
    multiple=True,
    help=(
        "After installing any specified packages, link the specified "
        "binaries into the directory they would have been installed into "
        "globally."
    ),
)
@click.option(
    "-r", "--requirement", "requirements",
    multiple=True,
    help=(
        "install the given requirements file into the "
        "virtualenv with pip after it is created"
    ),
)
@click.option(
    "-R", "--recreate",
    flag_value=True,
    help="recreate the virtualenv if it already exists",
)
@click.option(
    "-t", "--temp", "--temporary",
    flag_value=True,
    help="create or reuse the global temporary virtualenv",
)
@click.argument("name", required=False)
@click.argument("virtualenv_args", nargs=-1)
def main(
    name,
    locator,
    temporary,
    installs,
    links,
    requirements,
    recreate,
    virtualenv_args,
):
    if name:
        if temporary:
            raise click.BadParameter(
                "specify only one of '-t / --temp / --temporary' or 'name'",
            )
    elif len(installs) == 1:
        # When there's just one package to install, default to using that name.
        requirement, = installs
        name = Requirement(requirement).name

    if temporary:
        virtualenv = locator.temporary()
        act = virtualenv.recreate
    else:
        virtualenv = locator.for_name(name=name)
        if recreate:
            act = virtualenv.recreate
        else:
            act = virtualenv.create

    act(arguments=virtualenv_args)
    virtualenv.install(packages=installs, requirements=requirements)

    scripts = FilePath(sysconfig.get_path("scripts", "posix_user"))
    for link in links:
        virtualenv.binary(name=link).linkTo(scripts.child(link))
