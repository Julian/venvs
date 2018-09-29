import shutil
import subprocess
import sys
import zipapp

import click

from filesystems import native, Path


this = Path.from_string(__file__).relative_to(Path.cwd())
here = this.parent()


@click.command()
@click.option(
    '--artifact',
    type=click.Path(dir_okay=False),
    default=str(Path.cwd().descendant('bootstrap.pyz')),
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

    try:
        to_install = (
            ('-r', str(root.descendant('requirements.txt'))),
            (str(root),),
        )
        for target in to_install:
            subprocess.check_call(
                (
                    sys.executable,
                    '-m', 'pip',
                    'install',
                    '--target', str(build_path),
                ) + target,
            )

        shutil.copyfile(
            str(script),
            str(build_path.descendant('__main__.py')),
        )

        zipapp.create_archive(
            source=str(build_path),
            target=str(artifact),
        )
    finally:
        fs.remove(build_path)


if __name__ == '__main__':
    sys.exit(main())
