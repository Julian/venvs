import click

from venvs import __version__, converge, create, find, remove


@click.group(context_settings=dict(help_option_names=["--help", "-h"]))
@click.version_option(prog_name="venvs", version=__version__)
def main():
    """
    Centralized virtual environments.
    """


main.add_command(converge.main, name="converge")
main.add_command(create.main, name="create")
main.add_command(find.main, name="find")
main.add_command(remove.main, name="remove")
