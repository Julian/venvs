from unittest import TestCase
import sys

from filesystems import native, Path
import filesystems.native

from venvs import find, make
from venvs.common import Locator
from venvs.tests.utils import CLIMixin

from venvs import bootstrap, bootstrap_script


class TestBootstrap(CLIMixin, TestCase):
    if sys.version_info < (3,):
        skip = "bootstrap creation is only compatible with Python 3"

    cli = bootstrap

    def test_builds(self):
        native_fs = native.FS()

        package = Path.from_string(__file__).parent().parent()

        artifact = package.descendant('bootstrap.pyz')
        script = Path.cwd().descendant('bootstrap_script.py')

        default_script, = (
            parameter.default
            for parameter in bootstrap.main.params
            if parameter.name == 'script'
        )
        with native_fs.open(default_script, 'rb') as source:
            with native_fs.open(script, 'wb') as destination:
                destination.write(source.read())

        self.run_cli([
            '--artifact', str(artifact),
            '--script', str(script),
        ])

        self.assertTrue(native_fs.exists(artifact))
