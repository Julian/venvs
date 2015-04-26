from mkenv._cli import cli, parser


parser = parser(doc=__doc__)


@cli(parser=parser)
def run(arguments, stdin, stdout, stderr):
    pass
