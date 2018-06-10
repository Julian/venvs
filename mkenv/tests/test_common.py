from unittest import TestCase

from filesystems import Path, native

from mkenv.common import Locator, VirtualEnv


class TestLocator(TestCase):
    def test_named_virtualenvs_are_children(self):
        locator = Locator(root=Path.root(), filesystem=native.FS)
        self.assertEqual(
            locator.for_name("one"),
            VirtualEnv(
                path=locator.root.descendant("one"),
                filesystem=locator.filesystem,
                virtualenv_install=locator.virtualenv_install(),
            ),
        )
