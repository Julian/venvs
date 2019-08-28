import click

from venvs import __version__


@click.group(context_settings=dict(help_option_names=["--help", "-h"]))
@click.version_option(prog_name="venvs", version=__version__)
def main():
    """
    Centralized virtual environments.
    """
