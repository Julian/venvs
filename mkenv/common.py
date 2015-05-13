from itertools import chain
import errno
import os
import platform
import subprocess
import sys

from bp.filepath import FilePath
from characteristic import Attribute, attributes

from mkenv._cli import Argument, Option


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


@attributes(
    [
        Attribute(name="path"),
        Attribute(name="_create", default_value=_create_virtualenv),
        Attribute(name="_install", default_value=_install_into_virtualenv),
    ]
)
class VirtualEnv(object):
    """
    A virtual environment.

    """

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
        except IOError as error:
            if error.errno != errno.ENOENT:
                raise
        self._create(virtualenv=self, **kwargs)

    def install(self, stdout=sys.stdout, stderr=sys.stderr, **kwargs):
        self._install(virtualenv=self, stdout=stdout, stderr=stderr, **kwargs)


@attributes(
    [
        Attribute(name="root"),
        Attribute(name="make_virtualenv", default_value=VirtualEnv),
    ],
)
class Locator(object):
    """
    Locates virtualenvs from a common root directory.

    """

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


_ROOT = Argument(
    kind=Option(names=("-R", "--root")),
    default=Locator.default,
    destination="locator",
    type=lambda root : Locator(root=FilePath(root)),
    help="Specify a different root directory for virtualenvs.",
)
