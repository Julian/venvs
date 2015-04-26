"""
mkenv creates virtualenvs.

By default it places them in the appropriate data directory for your platform
(See `appdirs <https://pypi.python.org/pypi/appdirs>`_), but it will also
respect the :envvar:`WORKON_HOME` environment variable for compatibility with
:command:`mkvirtualenv`.

"""

import argparse
import os
import shutil
import subprocess

from mkenv.find import env_for_name
from mkenv.cli import cli, parser
from mkenv.common import TEMPORARY_VIRTUALENV


parser = parser(doc=__doc__)

target_venv_group = parser.add_mutually_exclusive_group()
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
    "-R", "--recreate",
    action="store_true",
    help="delete the named virtualenv if it exists before recreating it",
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


@cli(parser=parser)
def run(arguments, stdin, stdout, stderr):
    print arguments
    return
    virtualenv_args = arguments["virtualenv-args"]

    if arguments["temp"]:
        venv = TEMPORARY_VIRTUALENV
        print os.path.join(venv, "bin")
        arguments["recreate"] = True

        # Don't pollute stdout with output now, since we're using stdout
        if not arguments["verbose"]:
            virtualenv_args.append("--quiet")
    else:
        venv = env_for_name(arguments["name"])

    if arguments["recreate"]:
        shutil.rmtree(venv, ignore_errors=True)
    subprocess.check_call(["virtualenv"] + virtualenv_args + [venv])

    installs = [arg for args in arguments["installs"] for arg in args]
    if installs:
        command = [
            os.path.join(venv, "bin", "python"), "-m", "pip", "install",
        ]
        subprocess.check_call(command + installs)
