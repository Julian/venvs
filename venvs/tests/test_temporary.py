from unittest import TestCase

from venvs.tests.utils import CLIMixin


class TestTemporary(CLIMixin, TestCase):
    def test_it_creates_a_global_temporary_environment(self):
        temporary = self.locator.temporary()
        self.assertFalse(temporary.exists_on(self.filesystem))

        stdout, stderr = self.run_cli(["temporary"])
        self.assertEqual(
            (temporary.exists_on(self.filesystem), stdout, stderr),
            (True, str(temporary.path / "bin") + "\n", ""),
        )

    def test_it_recreates_the_environment_if_it_exists(self):
        temporary = self.locator.temporary()
        self.assertFalse(temporary.exists_on(self.filesystem))
        self.run_cli(["temporary"])
        self.assertTrue(temporary.exists_on(self.filesystem))

        foo = temporary.path / "foo"
        self.filesystem.touch(path=foo)
        self.assertTrue(self.filesystem.exists(path=foo))

        self.run_cli(["temporary"])
        self.assertTrue(temporary.exists_on(self.filesystem))
        self.assertFalse(self.filesystem.exists(path=foo))

    def test_env_with_single_install(self):
        self.run_cli(["temporary", "-i", "thing"])
        # We've stubbed out our Locator's venvs' install to just store.
        self.assertEqual(
            self.installed(self.locator.temporary()), ({"thing"}, set()),
        )
