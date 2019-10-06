import click

from venvs import __version__, converge, create, find, remove, temporary


@click.group(context_settings=dict(help_option_names=["--help", "-h"]))
@click.version_option(prog_name="venvs", version=__version__)
def main():
    """
    Centralized virtual environments.
    """


main.command(name="converge")(converge.main)
main.command(name="create")(create.main)
main.add_command(find.main, name="find")
main.command(name="remove")(remove.main)
main.command(name="temporary")(temporary.main)
