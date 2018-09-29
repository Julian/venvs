from unittest import TestCase

from venvs import remove
from venvs.common import _EX_NOINPUT
from venvs.tests.utils import CLIMixin


class TestRemove(CLIMixin, TestCase):

    cli = remove

    def test_remove_removes_an_env_with_the_given_name(self):
        boom = self.locator.for_name("boom")
        boom.create()
        self.assertTrue(boom.exists_on(filesystem=self.filesystem))
        self.run_cli(["boom"])
        self.assertFalse(boom.exists_on(filesystem=self.filesystem))

    def test_remove_multiple(self):
        names = ["boom", "bang", "whiz"]
        venvs = [self.locator.for_name(name=name) for name in names]

        for venv in venvs:
            venv.create()

        self.run_cli(names)
        self.assertEqual(
            [venv.exists_on(filesystem=self.filesystem) for venv in venvs],
            [False, False, False],
        )

    def test_cannot_remove_non_existing_envs(self):
        boom = self.locator.for_name("boom")
        self.assertFalse(boom.exists_on(filesystem=self.filesystem))
        self.run_cli(["boom"], exit_status=_EX_NOINPUT)

    def test_can_remove_non_existing_envs_with_force(self):
        boom = self.locator.for_name("boom")
        self.assertFalse(boom.exists_on(filesystem=self.filesystem))
        self.run_cli(["--force", "boom"])
