"""
mkenv creates virtualenvs.

By default it places them in the appropriate data directory for your platform
(See `appdirs <https://pypi.python.org/pypi/appdirs>`_), but it will also
respect the :envvar:`WORKON_HOME` environment variable for compatibility with
:command:`mkvirtualenv`.

"""

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys


__version__ = "0.2.1"


# Make a rookie attempt at converting the docstring to plaintext, since of
# course sphinx.builders.text.TextBuilder requires the world to run.
# Sorry. I'm a terrible person. But so is everyone else.
epilog = re.sub(
    r"`[^`]+ <([^`]+)>`_",
    r"\1",
    re.sub(":\w+:", "", __doc__),
)
parser = argparse.ArgumentParser(
    epilog=epilog,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "-V", "--version",
    action="version",
    version=__version__,
)

target_venv_group = parser.add_mutually_exclusive_group(required=True)
target_venv_group.add_argument(
    "name",
    nargs="?",
    help="create a new named virtualenv",
)
target_venv_group.add_argument(
    "-t", "--temp", "--temporary",
    action="store_true",
    help="create or reuse a global temporary virtualenv instead of a named one"
)

parser.add_argument(
    "-i", "--install",
    action="append",
    default=[],
    dest="installs",
    metavar="PACKAGE",
    type=lambda install : [install],
    help="install the given specifier (package) into the virtualenv "
         "with pip after it is created. May be repeated.",
)
parser.add_argument(
    "-r", "--requirement",
    action="append",
    dest="installs",
    metavar="REQUIREMENTS_FILE",
    type=lambda requirement : ["-r", requirement],
    help="install the given requirements file into the virtualenv "
         "with pip after it is created. May be repeated.",
)
parser.add_argument(
    "-v", "--verbose",
    action="store_true",
    help="show more output. Note that using this with the `-t` temporary "
         "virtualenv argument may polute stdout."
)
parser.add_argument(
    "virtualenv-args",
    nargs=argparse.REMAINDER,
    help="additional arguments that will be passed along to virtualenv(1)"
)


def main():
    arguments = vars(parser.parse_args())
    return run(arguments=arguments)


def run(arguments):
    venvs_dir = os.getenv("WORKON_HOME")
    if not venvs_dir:
        # On OSX, seemingly the best place to put this is also
        # user_data_dir, but that's ~/Library/Application Support,
        # which means that any binaries installed won't be runnable
        # because they will get spaces in their shebangs. Emulating *nix
        # behavior seems to be the "rightest" thing to do instead.
        if platform.system() == "Darwin":
            venvs_dir = os.path.expanduser("~/.local/share/virtualenvs")
        else:
            from appdirs import user_data_dir
            venvs_dir = user_data_dir(appname="virtualenvs")

    virtualenv_args = arguments["virtualenv-args"]

    if arguments["temp"]:
        venv = os.path.join(venvs_dir, "mkenv-temp-venv")
        print os.path.join(venv, "bin")
        shutil.rmtree(venv, ignore_errors=True)

        # Don't pollute stdout with output now, since we're using stdout
        if not arguments["verbose"]:
            virtualenv_args.append("--quiet")
    else:
        venv = os.path.join(venvs_dir, arguments["name"])

    subprocess.check_call(["virtualenv"] + virtualenv_args + [venv])

    installs = [arg for args in arguments["installs"] for arg in args]
    if installs:
        command = [
            os.path.join(venv, "bin", "python"), "-m", "pip", "install",
        ]
        subprocess.check_call(command + installs)
