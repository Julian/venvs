from unittest import TestCase

from filesystems import Path

from venvs.common import Locator, VirtualEnv


class TestLocator(TestCase):
    def test_named_virtualenvs_are_children(self):
        locator = Locator(root=Path.root())
        self.assertEqual(
            locator.for_name("one"),
            VirtualEnv(path=locator.root / "one"),
        )

    def test_strips_py(self):
        locator = Locator(root=Path.root())
        self.assertEqual(
            locator.for_name("one.py"),
            VirtualEnv(path=locator.root / "one"),
        )

    def test_strips_python(self):
        locator = Locator(root=Path.root())
        self.assertEqual(
            locator.for_name("python-one"),
            VirtualEnv(path=locator.root / "one"),
        )
