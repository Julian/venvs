from StringIO import StringIO
import os

from bp.memory import MemoryFS, MemoryPath

from mkenv._cli import CommandLine
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
            make_virtualenv=lambda **kwargs : VirtualEnv(
                create=self.fake_create,
                install=self.fake_install,
                **kwargs
            ),
        )
        self.installed = {}

    def fake_create(self, virtualenv, arguments, stdout, stderr):
        virtualenv.path.createDirectory()

    def fake_install(self, virtualenv, packages, requirements, stdout, stderr):
        self.installed.setdefault(virtualenv, []).append(
            (packages, requirements),
        )

    def run_cli(self, argv=(), exit_status=os.EX_OK):
        self.cli.run(
            arguments={"locator" : self.locator},
            command_line=CommandLine(
                argv=argv,
                stdin=self.stdin,
                stdout=self.stdout,
                stderr=self.stderr,
            ),
            exit=lambda got : self.assertEqual(
                got,
                exit_status,
                msg=(got, exit_status, self.stderr.getvalue()),
            ),
        )
        return (
            self.stdin.getvalue(),
            self.stdout.getvalue(),
            self.stderr.getvalue(),
        )
