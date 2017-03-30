"""
Converge the set of installed virtualenvs.

"""

import click
import toml

from mkenv.common import _FILESYSTEM, _LINK_DIR, _ROOT


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@_FILESYSTEM
@_LINK_DIR
@_ROOT
def main(filesystem, locator, link_dir):
    with filesystem.open(locator.root.descendant("virtualenvs.toml")) as venvs:
        contents = toml.load(venvs)

    for name, config in contents["virtualenv"].iteritems():
        virtualenv = locator.for_name(name=name)
        virtualenv.create()
        virtualenv.install(
            packages=config.get("install", []),
            requirements=config.get("requirements", []),
        )
        for link in config.get("link", []):
            filesystem.link(
                source=virtualenv.binary(name=link),
                to=link_dir.descendant(link),
            )
