"""
Converge the set of installed virtualenvs.

"""
import os
import sys

from filesystems.exceptions import FileExists, FileNotFound
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
        config.setdefault("python", sys.version)

        virtualenv = locator.for_name(name=name)
        existing_config_path = virtualenv.path.descendant("installed.toml")

        try:
            with filesystem.open(existing_config_path) as existing_config:
                if toml.loads(existing_config.read()) == config:
                    continue
        except FileNotFound:
            virtualenv.create()
        else:
            virtualenv.recreate_on(filesystem=filesystem)

        packages = [
            os.path.expandvars(os.path.expanduser(package))
            for package in config.get("install", [])
        ]
        requirements = [
            os.path.expandvars(os.path.expanduser(requirement))
            for requirement in config.get("requirements", [])
        ]
        virtualenv.install(packages=packages, requirements=requirements)
        for link in config.get("link", []):
            source = virtualenv.binary(name=link)
            try:
                filesystem.link(
                    source=source, to=link_dir.descendant(link),
                )
            except FileExists as error:
                if filesystem.realpath(error.value) != source:
                    raise

        with filesystem.open(existing_config_path, "w") as existing_config:
            existing_config.write(toml.dumps(config).encode("utf-8"))
