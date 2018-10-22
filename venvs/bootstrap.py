import pathlib
import shutil
import subprocess
import sys
import zipapp

import click

from filesystems import native, Path

import venvs
from venvs.bootstrap_script import downloaded_path

this = Path.from_string(__file__)
here = this.parent()

default_artifact_name = 'venvs-bootstrap-{version}.pyz'.format(
    version=venvs.__version__,
)
default_artifact_path = Path.cwd().descendant(default_artifact_name)


@click.command()
@click.option(
    '--artifact',
    type=click.Path(dir_okay=False),
    default=str(default_artifact_path),
    show_default=True,
)
@click.option(
    '--script',
    type=click.Path(dir_okay=False),
    default=str(here.descendant('bootstrap_script.py')),
    show_default=True,
)
@click.option(
    '--root',
    type=click.Path(file_okay=False),
    default=str(here.parent()),
    show_default=True,
)
def main(artifact, script, root):
    return build(
        artifact=Path.from_string(artifact),
        script=Path.from_string(script),
        root=Path.from_string(root),
    )


def build(artifact, script, root):
    fs = native.FS()
    build_path = fs.temporary_directory()
    build_download_path = build_path.descendant(downloaded_path)

    try:
        to_install = (
            ('-r', str(root.descendant('requirements.txt'))),
            # ('setuptools_scm',),
        )
        for target in to_install:
            subprocess.check_call(
                (
                    sys.executable,
                    '-m', 'pip',
                    'download',
                    '--no-deps',
                    '--dest', str(build_download_path),
                    *target,
                ),
                cwd=str(build_path),
            )

        subprocess.check_call(
            (
                sys.executable,
                str(root.descendant('setup.py')),
                'bdist_wheel',
                '--universal',
                '--dist-dir', str(build_download_path),
            ),
            cwd=str(root),
        )

        to_install = pathlib.Path(str(build_download_path)).glob('*')
        subprocess.check_call(
            (
                sys.executable,
                '-m', 'pip',
                'install',
                '--target', str(build_path),
                *(str(p) for p in to_install),
            ),
            cwd=str(build_path),
        )

        shutil.copyfile(
            str(script),
            str(build_path.descendant('__main__.py')),
        )

        extras = {}
        if sys.version_info >= (3, 7):
            extras['compressed'] = True

        zipapp.create_archive(
            source=str(build_path),
            target=str(artifact),
            **extras,
        )
    finally:
        fs.remove(build_path)


if __name__ == '__main__':
    sys.exit(main())
