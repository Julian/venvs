from StringIO import StringIO
import os
import sys

from bp.memory import MemoryFS, MemoryPath
import click.testing

from mkenv.common import Locator, VirtualEnv


class CLIMixin(object):
    def setUp(self):
        super(CLIMixin, self).setUp()

        self.stdin = StringIO()
        self.stdout = StringIO()
        self.stderr = StringIO()

        self.fs = MemoryFS()
        self.locator = Locator(
            root=MemoryPath(fs=self.fs),
            make_virtualenv=lambda **kwargs: VirtualEnv(
                create=self.fake_create,
                install=self.fake_install,
                **kwargs
            ),
        )
        self.installed = {}

    def fake_create(self, virtualenv, **kwargs):
        virtualenv.path.createDirectory()

    def fake_install(self, virtualenv, packages, requirements, stdout, stderr):
        self.installed.setdefault(virtualenv, []).append(
            (packages, requirements),
        )

    def run_cli(self, argv=(), exit_status=os.EX_OK):
        runner = click.testing.CliRunner()
        result = runner.invoke(
            self._fix_click(self.cli.main),
            args=argv,
            default_map=dict(locator=self.locator),
        )
        if result.exception and not isinstance(result.exception, SystemExit):
            cls, exc, tb = result.exc_info
            raise cls, exc, tb

        self.assertEqual(
            result.exit_code,
            exit_status,
            msg="Different exit code, {} != {}\n\nstderr:\n\n{!r}".format(
                result.exit_code, exit_status, self.stderr.getvalue(),
            ),
        )
        return (
            self.stdin.getvalue(),
            self.stdout.getvalue(),
            self.stderr.getvalue(),
        )

    def _fix_click(self, real_main):
        """
        Click is really really really annoying.

        It patches sys.stdout and sys.stderr to the same exact StringIO.

        """

        class Fixed(object):
            def __getattr__(self, attr):
                return getattr(real_main, attr)

            def main(this, *args, **kwargs):
                stdout, sys.stdout = sys.stdout, self.stdout
                stderr, sys.stderr = sys.stderr, self.stderr
                real_main.main(*args, **kwargs)
                sys.stdout = stdout
                sys.stderr = stderr
        return Fixed()
