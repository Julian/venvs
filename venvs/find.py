from functools import partial

from filesystems import Path
import click
import sys

from venvs import __version__
from venvs.common import _FILESYSTEM, _ROOT, PATH


def run(
    locator,
    filesystem,
    binary=None,
    directory=None,
    name=None,
    existing_only=False,
):
    """
    Find the virtualenv associated with a given project given its name or path.

    If an optional binary is provided, the binary's path within the virtualenv
    is returned.

    """

    if directory is not None:
        virtualenv = locator.for_directory(directory=directory)
    else:
        if name is None:
            sys.stdout.write(str(locator.root))
            sys.stdout.write("\n")
            return

        virtualenv = locator.for_name(name=name)

    if existing_only and not virtualenv.exists_on(filesystem=filesystem):
        return 1

    if binary is not None:
        sys.stdout.write(str(virtualenv.binary(binary)))
    else:
        sys.stdout.write(str(virtualenv.path))

    sys.stdout.write("\n")


@click.group(
    context_settings=dict(help_option_names=["-h", "--help"]),
    invoke_without_command=True,
)
@_FILESYSTEM
@_ROOT
@click.option(
    "-E", "--existing-only",
    flag_value=True,
    help="Only consider existing virtualenvs.",
)
@click.pass_context
@click.version_option(version=__version__)
def main(context, locator, existing_only, filesystem):
    if context.invoked_subcommand is None:
        click.echo(locator.root)
    else:
        context.obj = dict(
            locate=partial(
                run,
                locator=locator,
                existing_only=existing_only,
                filesystem=filesystem,
            ),
        )


@main.command()
@click.argument("directory", required=False, type=PATH)
@click.argument("binary", required=False)
@click.pass_context
def directory(context, directory, binary):
    """
    Find the virtualenv given the project's path.

    """

    locate = context.obj["locate"]
    context.exit(
        locate(directory=directory or Path.cwd(), binary=binary) or 0,
    )


@main.command()
@click.argument("name")
@click.argument("binary", required=False)
@click.pass_context
def name(context, name, binary):
    """
    Find the virtualenv given the project's name.

    """

    locate = context.obj["locate"]
    context.exit(locate(name=name, binary=binary) or 0)
