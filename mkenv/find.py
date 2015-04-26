import os

from bp.filepath import FilePath

from mkenv.common import VIRTUALENVS_ROOT
from mkenv._cli import CLI, Argument, Flag


@CLI(
    Flag(
        names=("-E", "--existing-only"),
        help="Only consider existing virtualenvs.",
    ),
    Argument(
        names=("-d", "--directory"),
        default=lambda : FilePath("."),
        type=FilePath,
        nargs="?",
        help="Find the virtualenv associated with the given directory.",
    ),
    Argument(
        names=("-n", "--name"),
        help="Find the virtualenv associated with the given project name.",
    ),
)
def run(arguments, stdin, stdout, stderr):
    """
    Find the virtualenv associated with a given project.

    """

    directory = arguments.get("directory")
    if directory is not None:
        found = env_for_directory(directory=directory)
    else:
        name = arguments.get("name")
        if name is not None:
            found = env_for_name(name=name)
        else:
            found = VIRTUALENVS_ROOT

    if arguments.get("existing-only") and not os.path.exists(found):
        return 0
        return 1

    stdout.write(found.path)
    stdout.write("\n")


def env_for_directory(directory):
    """
    Find the virtualenv that would be associated with the given directory.

    """

    return env_for_name(directory.basename())


def env_for_name(name):
    return VIRTUALENVS_ROOT.child(name.lower().replace("-", "_"))


if __name__ == "__main__":
    run()
