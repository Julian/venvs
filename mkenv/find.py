from bp.filepath import FilePath

from mkenv.common import Locator
from mkenv._cli import CLI, Argument, Flag, Group, Option, Positional


@CLI(
    Argument(
        Flag(),
        names=("-E", "--existing-only"),
        help="Only consider existing virtualenvs.",
    ),
    Group(
        members=[
            Argument(
                Option(),
                names=("-d", "--directory"),
                default=lambda : FilePath("."),
                type=FilePath,
                nargs="?",
                help="Find the virtualenv associated with the given directory.",
            ),
            Argument(
                Option(),
                names=("-n", "--name"),
                help="Find the virtualenv associated with the given project name.",
            ),
        ],
    ),
    Argument(
        Option(),
        names=("-R", "--root"),
        dest="locator",
        type=lambda root : Locator(root=FilePath(root)),
        help="Specify a different root directory for virtualenvs.",
    ),
    Argument(
        Positional(),
        names=("binary",),
        help="Locate a binary within the specified virtualenv's bin/ folder.",
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
        found = locator.for_name(name=arguments.get("name"))

    if arguments.get("existing-only") and not found.isdir():
        return 1

    binary = arguments.get("binary")
    if binary is not None:
        found = found.descendant(["bin", binary])

    stdout.write(found.path)
    stdout.write("\n")


if __name__ == "__main__":
    run()
