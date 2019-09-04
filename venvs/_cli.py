import subprocess
import sys

from filesystems import Path
import click

from venvs import __version__, _config
from venvs.common import _FILESYSTEM, _ROOT


@click.group(context_settings=dict(help_option_names=["--help", "-h"]))
@click.version_option(prog_name="venvs", version=__version__)
def main():
    """
    Centralized virtual environments.
    """


@main.command()
@_FILESYSTEM
@_ROOT
@click.option(
    "-w", "--wheel-dir",
    default=None,
    help="the directory to place the built wheels",
)
@click.argument("env")
def wheel(filesystem, locator, wheel_dir, env):
    """
    Wheel up a tracked virtual environment.
    """
    if wheel_dir is None:
        wheel_dir = Path.cwd().descendant("wheelhouse")

    config = _config.load(filesystem=filesystem, locator=locator)
    section = config["virtualenv"][env]
    subprocess.check_call(
        [
            sys.executable, "-m", "pip", "wheel",
            "--wheel-dir", str(wheel_dir),
        ] + section["install"],
    )
