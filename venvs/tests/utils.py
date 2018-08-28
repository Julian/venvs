import sys

from filesystems import Path
from filesystems.exceptions import FileExists, FileNotFound
import click.testing
import filesystems.memory

from venvs.common import Locator, VirtualEnv, _EX_OK


_PY3 = sys.version_info[0] >= 3
if _PY3:
    from io import StringIO as NativeStringIO
else:
    from io import BytesIO as NativeStringIO


class CLIMixin(object):
    def setUp(self):
        super(CLIMixin, self).setUp()

        self.stdin = NativeStringIO()
        self.stdout = NativeStringIO()
        self.stderr = NativeStringIO()

        self.filesystem = filesystems.memory.FS()

        self.root_dir = Path("virtualenvs")
        self.filesystem.create_directory(self.root_dir)

        self.link_dir = Path("bin")
        self.filesystem.create_directory(self.link_dir)

        self.locator = Locator(
            root=self.root_dir,
            make_virtualenv=lambda **kwargs: VirtualEnv(
                create=self.fake_create,
                install=self.fake_install,
                **kwargs
            ),
        )

    def installed(self, virtualenv):
        base = virtualenv.path
        try:
            with self.filesystem.open(base.descendant("packages")) as f:
                packages = set(line.strip() for line in f)
        except FileNotFound:
            packages = set()

        try:
            with self.filesystem.open(base.descendant("reqs")) as f:
                reqs = set(line.strip() for line in f)
        except FileNotFound:
            reqs = set()

        return packages, reqs

    def fake_create(self, virtualenv, **kwargs):
        try:
            self.filesystem.create_directory(path=virtualenv.path)
        except FileExists:
            pass

    def fake_install(self, virtualenv, packages, requirements, **kwargs):
        # FIXME: ...
        if virtualenv.path.basename() == "magicexplodingvirtualenv":
            raise ZeroDivisionError("Hey you told me to blow up!")

        base = virtualenv.path
        with self.filesystem.open(base.descendant("packages"), "at") as f:
            f.writelines(
                package + u"\n" for package in packages
            )
        with self.filesystem.open(base.descendant("reqs"), "at") as f:
            f.writelines(req + u"\n" for req in requirements)

    def run_cli(self, argv=(), exit_status=_EX_OK):
        runner = click.testing.CliRunner()
        result = runner.invoke(
            self._fix_click(self.cli.main),
            args=argv,
            default_map=dict(
                link_dir=self.link_dir,
                locator=self.locator,
                filesystem=self.filesystem,
            ),
            catch_exceptions=False,
        )

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
