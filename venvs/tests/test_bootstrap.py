import os
from unittest import TestCase
import shutil
import subprocess
import sys

from filesystems import native, Path

from venvs.common import workon_home_env_var
from venvs.bootstrap import build
import venvs.bootstrap_script


class TestBootstrap(TestCase):
    def setUp(self):
        super(TestBootstrap, self).setUp()

        self.native_fs = native.FS()
        self.temporary_directory = self.native_fs.temporary_directory()
        self.artifact = self.temporary_directory.descendant('bootstrap.pyz')

        root = os.environ.get('TOX_INI_DIR')
        if root is not None:
            root = Path.from_string(root)
        else:
            root = Path.from_string(__file__).relative_to(Path.cwd()).parent()
            while 'setup.py' not in self.native_fs.list_directory(root):
                root = root.parent()

        build(
            artifact=self.artifact,
            script=Path.from_string(
                venvs.bootstrap_script.__file__.rstrip('c'),
            ),
            root=root,
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
