"""
Converge the set of installed virtualenvs.

"""
import os
import subprocess
import sys

from filesystems.exceptions import FileExists, FileNotFound
from tqdm import tqdm
import click
import pytoml

from venvs import __version__
from venvs.common import _FILESYSTEM, _LINK_DIR, _ROOT, _load_config


class DuplicatedLinks(Exception):
    pass


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
@click.version_option(version=__version__)
def main(filesystem, locator, link_dir, handle_error):
    contents = _load_config(filesystem=filesystem, locator=locator)
    _check_for_duplicated_links(contents["virtualenv"].values())

    progress = tqdm(contents["virtualenv"].items())
    for name, config in progress:
        progress.set_description(name)

        python = config.pop("python", sys.executable)
        config.setdefault(
            "sys.version", subprocess.check_output(
                [python, "--version"],
                stderr=subprocess.STDOUT,
            ).decode('ascii'),
        )

        virtualenv = locator.for_name(name=name)
        existing_config_path = virtualenv.path / "installed.toml"

        try:
            with filesystem.open(existing_config_path) as existing_config:
                if pytoml.loads(existing_config.read()) == config:
                    continue
        except FileNotFound:
            virtualenv.create(python=python)
        else:
            virtualenv.recreate_on(filesystem=filesystem, python=python)

        packages, requirements = _to_install(config=config)
        try:
            virtualenv.install(packages=packages, requirements=requirements)
        except Exception:
            handle_error(virtualenv)
            continue

        for link in config.get("link", []):
            name, _, to = link.partition(":")
            _link(
                source=virtualenv.binary(name=name),
                to=link_dir.descendant(to or name),
                filesystem=filesystem,
            )

        with filesystem.open(existing_config_path, "wt") as existing_config:
            existing_config.write(pytoml.dumps(config))


def _check_for_duplicated_links(sections):
    seen, duplicated = set(), set()
    for each in sections:
        for link in each.get("link", ()):
            if link in seen:
                duplicated.add(link)
            seen.add(link)
    if duplicated:
        raise DuplicatedLinks(duplicated)


def _to_install(config):
    packages = [
        os.path.expandvars(os.path.expanduser(package))
        for package in config.get("install", [])
    ]
    requirements = [
        os.path.expandvars(os.path.expanduser(requirement))
        for requirement in config.get("requirements", [])
    ]
    return packages, requirements


def _link(source, to, filesystem):
    """
    Link the given binary, replacing broken symlinks and erroring if existing.
    """

    try:
        filesystem.link(source=source, to=to)
    except FileExists as error:
        if filesystem.realpath(error.value) == filesystem.realpath(source):
            return
        if filesystem.exists(to):
            raise
        filesystem.remove(to)
        filesystem.link(source=source, to=to)
