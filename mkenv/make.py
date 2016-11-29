"""
mkenv creates virtualenvs.

By default it places them in the appropriate data directory for your platform
(See `appdirs <https://pypi.python.org/pypi/appdirs>`_), but it will also
respect the :envvar:`WORKON_HOME` environment variable for compatibility with
:command:`mkvirtualenv`.

"""
import click

from mkenv.common import _ROOT


def run(
    locator, name, installs, requirements, temporary, recreate, virtualenv_args
):
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
def main(name, temporary, **kwargs):
    if name and temporary:
        raise click.BadParameter(
            "specify only one of '-t / --temp / --temporary' or 'name'",
        )
    run(name=name, temporary=temporary, **kwargs)
