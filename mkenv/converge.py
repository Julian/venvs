"""
Converge the set of installed virtualenvs.

"""
import os
import sys

from filesystems.exceptions import FileExists, FileNotFound
import click
import pytoml

from mkenv.common import _FILESYSTEM, _LINK_DIR, _ROOT


def _fail(virtualenv):
    raise


def _do_not_fail(virtualenv):
    sys.stderr.write("Converging {!r} failed!\n".format(virtualenv))


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@_FILESYSTEM
@_LINK_DIR
@_ROOT
@click.option(
    "--fail-fast", "handle_error",
    flag_value=_fail,
    help="Fail if any virtualenv cannot be converged.",
)
@click.option(
    "--no-fail-fast", "handle_error",
    default=True,
    flag_value=_do_not_fail,
    help="Do not fail if a virtualenv cannot be converged.",
)
def main(filesystem, locator, link_dir, handle_error):
    with filesystem.open(locator.root.descendant("virtualenvs.toml")) as venvs:
        contents = pytoml.load(venvs)

    for name, config in contents["virtualenv"].items():
        config.setdefault("sys.version", sys.version)

        virtualenv = locator.for_name(name=name)
        existing_config_path = virtualenv.path.descendant("installed.toml")

        try:
            with filesystem.open(existing_config_path) as existing_config:
                if pytoml.loads(existing_config.read()) == config:
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

        try:
            virtualenv.install(packages=packages, requirements=requirements)
        except Exception:
            handle_error(virtualenv)
            continue

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
            existing_config.write(pytoml.dumps(config).encode("utf-8"))
