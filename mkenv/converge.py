"""
Converge the set of installed virtualenvs.

"""

import click
import toml

from mkenv.common import _FILESYSTEM, _ROOT


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@_FILESYSTEM
@_ROOT
def main(filesystem, locator):
    with filesystem.open(locator.root.descendant("virtualenvs.toml")) as venvs:
        contents = toml.load(venvs)

    for name in contents["virtualenv"]:
        locator.for_name(name=name).create()
