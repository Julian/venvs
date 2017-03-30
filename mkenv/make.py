"""
mkenv creates virtualenvs.

By default it places them in the appropriate data directory for your platform
(See `appdirs <https://pypi.python.org/pypi/appdirs>`_), but it will also
respect the :envvar:`WORKON_HOME` environment variable for compatibility with
:command:`mkvirtualenv`.

"""

from functools import partial

from filesystems import Path
from packaging.requirements import Requirement
import click

from mkenv.common import _FILESYSTEM, _LINK_DIR, _ROOT


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@_FILESYSTEM
@_LINK_DIR
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
@click.argument("virtualenv_args", nargs=-1, type=click.UNPROCESSED)
def main(
    filesystem,
    link_dir,
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

        virtualenv = locator.for_name(name=name)
    elif temporary:
        virtualenv = locator.temporary()
        click.echo(virtualenv.binary("python").dirname())
        act = partial(virtualenv.recreate_on, filesystem=filesystem)
    elif len(installs) == 1:
        # When there's just one package to install, default to using that name.
        requirement, = installs
        name = Requirement(requirement).name
        virtualenv = locator.for_name(name=name)
    elif installs:
        raise click.BadParameter("A name is required.")
    elif len(links) == 1:
        # When there's just one binary to link, go for the gold.
        name, = installs = links
        virtualenv = locator.for_name(name=name)
    else:
        virtualenv = locator.for_directory(directory=Path.cwd())

    if recreate or temporary:
        act = partial(virtualenv.recreate_on, filesystem=filesystem)
    else:
        act = virtualenv.create

    act(arguments=virtualenv_args)
    virtualenv.install(packages=installs, requirements=requirements)

    for link in links:
        filesystem.link(
            source=virtualenv.binary(name=link),
            to=link_dir.descendant(link),
        )
