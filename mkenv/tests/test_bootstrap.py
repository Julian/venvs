from unittest import TestCase
import sys

from filesystems import native, Path
import filesystems.native

from mkenv import find, make
from mkenv.common import Locator
from mkenv.tests.utils import CLIMixin

from mkenv import bootstrap


class TestBootstrap(CLIMixin, TestCase):
    if sys.version_info < (3,):
        skip = "bootstrap creation is only compatible with Python 3"

    cli = bootstrap

    def test_builds(self):
        native_fs = native.FS()

        package = Path.from_string(__file__).parent().parent()

        artifact = package.descendant('bootstrap.pyz')
        script = Path.from_string('bootstrap_script.py')

        default_script, = (
            parameter.default
            for parameter in bootstrap.main.params
            if parameter.name == 'script'
        )
        with native_fs.open(default_script, 'rb') as source:
            with self.filesystem.open(script, 'wb') as destination:
                destination.write(source.read())

        self.run_cli([
            '--artifact', str(artifact),
            '--script', str(script),
        ])

        self.assertTrue(self.fs.exists(artifact))
