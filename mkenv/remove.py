import errno
import os

import click

from mkenv.common import _ROOT


def run(locator, names, force):
    for name in names:
        virtualenv = locator.for_name(name=name)
        try:
            virtualenv.remove()
        except (IOError, OSError) as error:  # FIXME: Once bp has exceptions
            if error.errno != errno.ENOENT:
                raise
            if not force:
                return os.EX_NOINPUT


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
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
