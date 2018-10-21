import os
import subprocess
import shutil
import sys
import tempfile
import zipfile

import click
from filesystems import Path

from venvs.common import _FILESYSTEM, _LINK_DIR, _ROOT, Locator


downloaded_path = 'downloaded'


@click.command(help='Bootstrap venvs')
@_FILESYSTEM
@_LINK_DIR
# @_ROOT
def main(filesystem, link_dir):
    # doesn't work because pkg_resources doesn't work in the pyz
    #
    # entry_points = list(
    #     entry
    #     for entry in pkg_resources.iter_entry_points('console_scripts')
    #     if entry.dist.project_name == 'venvs'
    # )
    #
    # link_args = tuple(itertools.chain.from_iterable(
    #     (
    #         ('--link', str(entry.name))
    #         for entry in entry_points
    #     ),
    # ))

    pyz = Path.from_string(__file__).parent()

    virtualenv = Locator.default().for_name('venvs')
    virtualenv.recreate_on(filesystem=filesystem)

    d = Path.from_string(tempfile.mkdtemp())
    try:
        with zipfile.ZipFile(str(pyz)) as z:
            prefix = downloaded_path + os.sep
            dists = [
                dist
                for dist in z.namelist()
                if (
                    dist.startswith(prefix)
                    and len(dist) > len(prefix)
                )
            ]
            z.extractall(path=str(d), members=dists)

        full_dists = [
            d.descendant(dist)
            for dist in dists
        ]

        subprocess.check_call(
            (
                str(virtualenv.binary('python')),
                '-m', 'pip',
                'install',
                '--no-deps',
                '--no-index',
            ) + tuple(str(fd) for fd in full_dists),
            cwd=str(virtualenv.path),
        )
    finally:
        shutil.rmtree(str(d))

    if not filesystem.exists(link_dir):
        # TODO: add an `exists_ok` parameter
        filesystem.create_directory(link_dir)

    for link in ("venvs", "convergeenvs", "findenv", "rmenv"):
        if filesystem.exists(link_dir.descendant(link)):
            continue

        # TODO: add an `overwrite` parameter
        filesystem.link(
            source=virtualenv.binary(name=link),
            to=link_dir.descendant(link),
        )


if __name__ == '__main__':
    sys.exit(main())
