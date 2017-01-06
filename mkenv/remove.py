import os

from filesystems.exceptions import FileNotFound
import click

from mkenv.common import _FILESYSTEM, _ROOT


def run(locator, filesystem, names, force):
    for name in names:
        virtualenv = locator.for_name(name=name)
        try:
            virtualenv.remove_from(filesystem=filesystem)
        except FileNotFound:
            if not force:
                return os.EX_NOINPUT


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@_FILESYSTEM
@_ROOT
@click.option(
    "-f", "--force",
    flag_value=True,
    help="Ignore errors if the virtualenv does not exist.",
)
@click.argument("names", nargs=-1)
@click.pass_context
def main(context, **kwargs):
    context.exit(run(**kwargs) or 0)
