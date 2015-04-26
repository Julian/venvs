from bp.filepath import FilePath

from mkenv.common import Locator
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
    Argument(
        names=("-R", "--root"),
        dest="locator",
        type=lambda root : Locator(root=FilePath(root)),
        help="Specify a different root directory for virtualenvs.",
    ),
)
def run(arguments, stdin, stdout, stderr):
    """
    Find the virtualenv associated with a given project.

    """

    locator = arguments.get("locator") or Locator.default()

    directory = arguments.get("directory")
    if directory is not None:
        found = locator.for_directory(directory=directory)
    else:
        name = arguments.get("name")
        if name is not None:
            found = locator.for_name(name=name)
        else:
            found = locator.root

    if arguments.get("existing-only") and not found.isdir():
        return 1

    stdout.write(found.path)
    stdout.write("\n")


if __name__ == "__main__":
    run()
