from itertools import chain
import errno
import os
import platform
import subprocess
import sys

from bp.filepath import FilePath
import attr
import click


def _create_virtualenv(virtualenv, arguments, stdout, stderr):
    subprocess.check_call(
        ["virtualenv"] + list(arguments) + [virtualenv.path.path],
        stdout=stdout,
        stderr=stderr,
    )


def _install_into_virtualenv(
    virtualenv, packages, requirements, stdout, stderr,
):
    if not packages and not requirements:
        return
    things = list(
        chain(packages, (("-r", requirement) for requirement in requirements))
    )
    subprocess.check_call(
        [virtualenv.binary("python").path, "-m", "pip", "install"] + things,
        stdout=stdout,
        stderr=stderr,
    )


@attr.s
class VirtualEnv(object):
    """
    A virtual environment.

    """

    path = attr.ib()
    _create = attr.ib(default=_create_virtualenv, repr=False)
    _install = attr.ib(default=_install_into_virtualenv, repr=False)

    @property
    def exists(self):
        return self.path.isdir()

    def binary(self, name):
        return self.path.descendant(["bin", name])

    def create(self, arguments=(), stdout=sys.stdout, stderr=sys.stderr):
        self._create(self, arguments=arguments, stdout=stdout, stderr=stderr)

    def remove(self):
        self.path.remove()

    def recreate(self, **kwargs):
        try:
            self.remove()
        except EnvironmentError as error:
            if error.errno != errno.ENOENT:
                raise
        self.create(**kwargs)

    def install(self, stdout=sys.stdout, stderr=sys.stderr, **kwargs):
        self._install(virtualenv=self, stdout=stdout, stderr=stderr, **kwargs)


@attr.s
class Locator(object):
    """
    Locates virtualenvs from a common root directory.

    """

    root = attr.ib()
    make_virtualenv = attr.ib(default=VirtualEnv)

    @classmethod
    def default(cls, **kwargs):
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
        return cls(root=FilePath(root), **kwargs)

    def for_directory(self, directory):
        """
        Find the virtualenv that would be associated with the given directory.

        """

        return self.for_name(directory.basename())

    def for_name(self, name):
        child = self.root.child(name.lower().replace("-", "_"))
        return self.make_virtualenv(path=child)

    def temporary(self):
        return self.for_name(".mkenv-temporary-env")


class _FilePath(click.ParamType):

    name = "path"

    def convert(self, value, param, context):
        if not isinstance(value, str):
            return value
        return FilePath(str(value))


class _Locator(click.ParamType):

    name = "locator"

    def convert(self, value, param, context):
        if not isinstance(value, str):
            return value
        return Locator(root=FilePath(value))


FILEPATH = _FilePath()
_ROOT = click.option(
    "-R", "--root", "locator",
    default=Locator.default,
    type=_Locator(),
    help="Specify a different root directory for virtualenvs.",
)


class BadParameter(click.BadParameter):
    exit_code = os.EX_USAGE
