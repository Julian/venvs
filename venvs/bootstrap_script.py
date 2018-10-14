import itertools
import sys

import click

import venvs.make


@click.command(help='Bootstrap venvs')
def main():
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

    link_args = tuple(itertools.chain.from_iterable(
        (
            ('--link', name)
            for name in (
                "venvs",
                "convergeenvs",
                "findenv",
                "rmenv",
            )
        ),
    ))

    sys.argv[1:] = (
        '--install', 'venvs',
    ) + link_args

    venvs.make.main()


if __name__ == '__main__':
    sys.exit(main())
