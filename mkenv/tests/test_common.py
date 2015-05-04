from unittest import TestCase

from bp.memory import MemoryFS, MemoryPath

from mkenv.common import Locator, VirtualEnv


class TestLocator(TestCase):
    def test_named_virtualenvs_are_children(self):
        root = MemoryPath(fs=MemoryFS())
        locator = Locator(root=root)
        self.assertEqual(
            locator.for_name("one"),
            VirtualEnv(path=locator.root.child("one")),
        )
