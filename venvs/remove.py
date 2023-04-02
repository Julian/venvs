"""
CLI for deleting virtual environments imperatively.
"""
from filesystems.exceptions import FileNotFound
import click

from venvs.common import _EX_NOINPUT, _FILESYSTEM, _ROOT


def run(locator, filesystem, names, force):
    """
    Remove an ad hoc virtual environment.
    """
    for name in names:
        virtualenv = locator.for_name(name=name)
        try:
            virtualenv.remove_from(filesystem=filesystem)
        except FileNotFound:
            if not force:
                return _EX_NOINPUT


@_FILESYSTEM
@_ROOT
@click.option(
    "-f",
    "--force",
    flag_value=True,
    help="Ignore errors if the virtualenv does not exist.",
)
@click.argument("names", nargs=-1)
@click.pass_context
def main(context, **kwargs):
    """
    Remove an ad hoc virtualenv.
    """
    context.exit(run(**kwargs) or 0)
