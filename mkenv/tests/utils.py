from StringIO import StringIO
from functools import partial
import os

from bp.memory import MemoryFS, MemoryPath

from mkenv.common import Locator


class CLIMixin(object):
    def setUp(self):
        super(CLIMixin, self).setUp()

        self.stdin = StringIO()
        self.stdout = StringIO()
        self.stderr = StringIO()

        self.fs = MemoryFS()
        self.locator = Locator(root=MemoryPath(fs=self.fs))

    def run_cli(self, argv=(), exit_status=os.EX_OK):
        self.cli.run(
            argv=argv,
            stdin=self.stdin,
            stdout=self.stdout,
            stderr=self.stderr,
            exit=partial(self.assertEqual, exit_status),
            arguments={"locator" : self.locator},
        )
        return (
            self.stdin.getvalue(),
            self.stdout.getvalue(),
            self.stderr.getvalue(),
        )
