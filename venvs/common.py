"""
Objects for interacting with a central set of virtual environments.
"""

from itertools import chain
from shutil import which
import os
import platform
import subprocess
import sys

from filesystems.click import PATH
import attr
import click
import filesystems.native


def _create_virtualenv(virtualenv, arguments, python, stdout, stderr):
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "virtualenv",
            "--python",
            which(python),
            "--quiet",
        ]
        + list(arguments)
        + [str(virtualenv.path)],
        stderr=stderr,
    )


def _install_into_virtualenv(
    virtualenv,
    packages,
    requirements,
    stdout,
    stderr,
):
    if not packages and not requirements:
        return
    things = list(
        chain(
            packages,
            *(("-r", requirement) for requirement in requirements),
        ),
    )
    subprocess.check_call(
        [
            str(virtualenv.binary("python")),
            "-m",
            "pip",
            "--quiet",
            "install",
        ]
        + things,
        stdout=stdout,
        stderr=stderr,
    )


@attr.s
class VirtualEnv:
    """
    A virtual environment.
    """

    path = attr.ib()
    _create = attr.ib(default=_create_virtualenv, repr=False)
    _install = attr.ib(default=_install_into_virtualenv, repr=False)

    def exists_on(self, filesystem):
        """
        Return whether this environment already exist on the given filesystem.
        """
        return filesystem.is_dir(path=self.path)

    def binary(self, name):
        """
        Retrieve the path to a given binary within this environment.
        """
        return self.path.descendant("bin", name)

    def create(
        self,
        arguments=(),
        python=sys.executable,
        stdout=sys.stdout,
        stderr=sys.stderr,
    ):
        """
        Create this virtual environment.
        """
        self._create(
            self,
            arguments=arguments,
            python=python,
            stdout=stdout,
            stderr=stderr,
        )

    def remove_from(self, filesystem):
        """
        Delete this virtual environment off the given filesystem.
        """
        filesystem.remove(self.path)

    def recreate_on(self, filesystem, **kwargs):
        """
        Recreate this environment, deleting an existing one if necessary.
        """
        try:
            self.remove_from(filesystem=filesystem)
        except filesystems.exceptions.FileNotFound:
            pass
        self.create(**kwargs)

    def install(self, stdout=sys.stdout, stderr=sys.stderr, **kwargs):
        """
        Install a given set of packages into this environment.
        """
        self._install(virtualenv=self, stdout=stdout, stderr=stderr, **kwargs)


@attr.s
class Locator:
    """
    Locates virtualenvs from a common root directory.

    """

    root = attr.ib()
    make_virtualenv = attr.ib(default=VirtualEnv)

    @classmethod
    def default(cls, **kwargs):
        """
        Return the default (OS-specific) location for environments.
        """
        workon_home = os.getenv("WORKON_HOME")
        if workon_home:
            root = workon_home
        else:
            # On OSX, seemingly the best place to put this is also
            # user_data_dir, but that's ~/Library/Application Support, which
            # means that any binaries installed won't be runnable because they
            # will get spaces in their shebangs. Emulating *nix behavior seems
            # to be the "rightest" thing to do instead.
            if platform.system() == "Darwin":
                root = os.path.expanduser("~/.local/share/virtualenvs")
            else:
                from appdirs import user_data_dir

                root = user_data_dir(appname="virtualenvs")
        return cls(root=filesystems.Path.from_string(root), **kwargs)

    def for_directory(self, directory):
        """
        Find the virtualenv that would be associated with the given directory.
        """
        return self.for_name(directory.basename())

    def for_name(self, name):
        """
        Retrieve the environment with the given name.
        """
        if name.endswith(".py"):
            name = name.removesuffix(".py")
        elif name.startswith("python-"):
            name = name.removeprefix("python-")
        child = self.root.descendant(name.lower().replace("-", "_"))
        return self.make_virtualenv(path=child)

    def temporary(self):
        """
        Retrieve a global temporary virtual environment.
        """
        return self.for_name(".venvs-temporary-env")


class _Locator(click.ParamType):
    name = "locator"

    def convert(self, value, param, context):
        if not isinstance(value, str):
            return value
        return Locator(root=PATH.convert(value, param, context))


_ROOT = click.option(
    "--root",
    "locator",
    default=Locator.default,
    type=_Locator(),
    help="Specify a different root directory for virtualenvs.",
)
# Fucking click, cannot find a way to be able to override this
# parameter unless it actually is an argument, so make it one.
_FILESYSTEM = click.option(
    "--filesystem",
    default=filesystems.native.FS(),
    type=lambda value: value,
)
_LINK_DIR = click.option(
    "--link-dir",
    default=filesystems.Path.from_string(
        os.path.expanduser("~/.local/bin/"),
    ),
    type=PATH,
    help="The directory to link scripts into.",
)

_EX_OK = getattr(os, "EX_OK", 0)
_EX_USAGE = getattr(os, "EX_USAGE", 64)
_EX_NOINPUT = getattr(os, "EX_NOINPUT", 66)


class BadParameter(click.BadParameter):
    """
    Set a different exit status from click's default.
    """

    exit_code = _EX_USAGE
