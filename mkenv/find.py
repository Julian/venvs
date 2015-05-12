from bp.filepath import FilePath

from mkenv.common import _ROOT, Locator
from mkenv._cli import CLI, Argument, Flag, Group, Option, Positional


@CLI(
    Argument(
        kind=Flag(names=("-E", "--existing-only")),
        help="Only consider existing virtualenvs.",
    ),
    Group(
        members=[
            Argument(
                kind=Option(names=("-d", "--directory")),
                default=lambda : FilePath("."),
                type=FilePath,
                nargs="?",
                help="Find the virtualenv associated with the given directory.",
            ),
            Argument(
                kind=Option(names=("-n", "--name")),
                help="Find the virtualenv associated with the given project name.",
            ),
        ],
    ),
    _ROOT,
    Argument(
        kind=Positional(name="binary"),
        required=False,
        help="Locate a binary within the specified virtualenv's bin/ folder.",
    ),
)
def run(arguments, stdin, stdout, stderr):
    """
    Find the virtualenv associated with a given project.

    """

    locator = arguments["locator"]

    directory = arguments["directory"]
    if directory is not None:
        virtualenv = locator.for_directory(directory=directory)
    else:
        name = arguments["name"]
        if name is None:
            stdout.write(locator.root.path)
            stdout.write("\n")
            return

        virtualenv = locator.for_name(name=name)

    if arguments["existing-only"] and not virtualenv.exists:
        return 1

    binary = arguments["binary"]
    if binary is not None:
        stdout.write(virtualenv.binary(binary).path)
    else:
        stdout.write(virtualenv.path.path)

    stdout.write("\n")


if __name__ == "__main__":
    run()
