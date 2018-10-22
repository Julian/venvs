import os
from unittest import TestCase
import shutil
import subprocess
import sys

from filesystems import native, Path

from venvs.common import Locator, workon_home_env_var

from venvs import bootstrap


class TestBootstrap(TestCase):
    if sys.version_info < (3,):
        skip = "bootstrap creation is only compatible with Python 3"

    def setUp(self):
        super(TestBootstrap, self).setUp()

        self.native_fs = native.FS()

        self.temporary_directory = self.native_fs.temporary_directory()

        package = Path.from_string(__file__).parent().parent()

        self.artifact = self.temporary_directory.descendant('bootstrap.pyz')
        script = self.temporary_directory.descendant('bootstrap_script.py')

        default_script, = (
            parameter.default
            for parameter in bootstrap.main.params
            if parameter.name == 'script'
        )
        with self.native_fs.open(default_script, 'rb') as source:
            with self.native_fs.open(script, 'wb') as destination:
                destination.write(source.read())

        locator = Locator(root=self.temporary_directory)
        build_venv = locator.for_name('build_venv')
        build_venv.create(python='python3')
        build_venv.install(
            # TODO: shouldn't this be a default or such?
            packages=[],
            requirements=[
                str(package.parent().descendant('test-requirements.txt')),
            ],
        )

        subprocess.check_call(
            [
                str(build_venv.binary('python')),
                '-m', 'venvs.bootstrap',
                '--artifact', str(self.artifact),
                '--script', str(script),
            ],
        )

    def tearDown(self):
        shutil.rmtree(str(self.temporary_directory))

    def test_installs(self):
        temporary_root = self.native_fs.temporary_directory()
        temporary_links = temporary_root.descendant('links')

        try:
            env = dict(os.environ)
            env[workon_home_env_var] = str(temporary_root)

            subprocess.check_call(
                [
                    sys.executable,
                    str(self.artifact),
                    '--link-dir', str(temporary_links),
                ],
                env=env,
            )

            assert self.native_fs.is_dir(temporary_root.descendant('venvs'))
            assert self.native_fs.is_link(temporary_links.descendant('venvs'))
        finally:
            shutil.rmtree(str(temporary_root))
