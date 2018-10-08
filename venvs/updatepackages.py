import itertools
import subprocess
import sys


import attr
import click


@attr.s
class Requirement(object):
    name = attr.ib()
    version = attr.ib()
    url = attr.ib()


def parse_requirements(lines, require_vcs):
    requirements = []

    for line in lines:
        standard, sep, comment = line.strip().partition(b'##')
        if len(sep) == 0 and require_vcs == True:
            continue
        comment = comment.strip()
        if len(comment) == 0:
            comment = None

        name, sep, version = standard.partition(b'==')
        name = name.strip()
        version = version.strip()

        if len(sep) == 0:
            version = None

        requirement = Requirement(
            name=name,
            version=version,
            url=comment,
        )

        requirements.append(requirement)

    return requirements


@click.command()
@click.option(
    '--mode',
    type=click.Choice(['latest', 'pre', 'vcs']),
    required=True,
)
@click.option(
    '--source',
    type=click.File('rb'),
    required=True,
)
@click.option(
    '--destination',
    type=click.File('wb', atomic=True),
    required=True,
)
def main(mode, source, destination):
    frozen = subprocess.check_output(
        [
            sys.executable,
            '-m',
            'pip',
            'freeze',
            '--exclude-editable',
        ],
    )

    frozen_requirements = parse_requirements(
        lines=frozen.splitlines(),
        require_vcs=False,
    )

    file_requirements = parse_requirements(
        lines=source,
        require_vcs=True,
    )

    merged = sorted({
        requirement.name: requirement
        for requirement in itertools.chain(
            frozen_requirements,
            file_requirements,
        )
    }.values())

    if mode == 'latest':
        for requirement in merged:
            destination.write(requirement.name + b'\n')
    elif mode == 'pre':
        for requirement in merged:
            destination.write(requirement.name + b'>=0.0.dev0\n')
    elif mode == 'vcs':
        for requirement in merged:
            if requirement.url is not None:
                destination.write(
                    requirement.url + b'#egg=' + requirement.name + b'\n',
                )
