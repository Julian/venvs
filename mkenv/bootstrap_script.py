import itertools
import pkg_resources
import subprocess
import sys

import click
import click.testing
from filesystems import Path

import mkenv.make


@click.command(help='Bootstrap mkenv')
def main():
    # entry_points = list(
    #     entry
    #     for entry in pkg_resources.iter_entry_points('console_scripts')
    #     # if entry.dist.project_name == 'mkenv'
    # )
    #
    # link_args = tuple(itertools.chain.from_iterable(
    #     (
    #         ('--link', str(entry.name))
    #         for entry in entry_points
    #     ),
    # ))
    #
    # print(entry_points)
    # print(link_args)

    # requirement, = installs
    # name = Requirement(requirement).name
    # virtualenv = locator.for_name(name=name)
    #
    # act = virtualenv.create
    #
    # act(arguments=virtualenv_args)
    # virtualenv.install(packages=installs, requirements=requirements)
    #
    # for link in links:
    #     filesystem.link(
    #         source=virtualenv.binary(name=link),
    #         to=link_dir.descendant(link),
    #     )
    #
    # return

    link_args = tuple(itertools.chain.from_iterable(
        (
            ('--link', name)
            for name in (
                "mkenv",
                "convergeenvs",
                "findenv",
                "rmenv",
            )
        ),
    ))

    sys.argv[1:] = (
        '-R',
        '-i', 'mkenv',
    ) + link_args

    mkenv.make.main()

    # runner = click.testing.CliRunner()
    # result = runner.invoke(
    #     mkenv.make.main,
    #     (
    #         '-R',
    #         '-i', 'mkenv',
    #     ) + link_args,
    #     catch_exceptions=False,
    # )
    # print(result.output)
    # print(result.exception)
    # print(result.exit_code)
    # return result.exit_code

    # return
    # print('output:')
    # print(result.output)
    # print('exception:')
    # print(result.exception)
    # assert result.exit_code == 0
    #
    # return
    #
    # print('\n'.join(str(x) for x in entry_points))
    #
    # archive = Path(sys.argv[0]).relative_to(Path.cwd())
    #
    # import mkenv
    # print(sys.argv[0])
    # print(dir(mkenv))
    # return
    #
    # args = (
    #         sys.executable,
    #         '-m', 'mkenv',
    #         '-R',
    #         '-i', 'mkenv',
    # )
    # args += tuple(itertools.chain.from_iterable(
    #     (
    #         ('--link', str(entry.name))
    #         for entry in entry_points
    #     ),
    # ))
    # print(args)
    # subprocess.check_call(
    #     args,
    # )


if __name__ == '__main__':
    sys.exit(main())
