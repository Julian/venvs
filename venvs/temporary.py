import click

from venvs.common import _FILESYSTEM, _ROOT
from venvs.create import _INSTALL, _REQUIREMENTS


@_FILESYSTEM
@_ROOT
@_INSTALL
@_REQUIREMENTS
def main(filesystem, locator, installs, requirements):
    """
    Create or reuse the global temporary virtualenv.
    """

    temporary = locator.temporary()
    click.echo(temporary.binary("python").dirname())
    temporary.recreate_on(filesystem=filesystem)
    temporary.install(packages=installs, requirements=requirements)
