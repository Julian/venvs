from tempfile import mkdtemp
from unittest import TestCase

from bp.filepath import FilePath
from bp.memory import MemoryFS, MemoryPath
from characteristic import Attribute, attributes
from testscenarios import with_scenarios

from mkenv.common import Locator, VirtualEnv


@attributes([Attribute(name="path")])
class FakeVirtualEnv(object):
    pass


@with_scenarios()
class TestLocator(TestCase):

    scenarios = [
        (
            "with_virtualenv", {
                "make_root" : lambda : FilePath(mkdtemp()),
                "cleanup" : lambda root : root.remove,
                "virtualenv_class" : VirtualEnv,
            },
        ),
        (
            "with_fake_virtualenv", {
                "make_root" : lambda : MemoryPath(fs=MemoryFS()),
                "cleanup" : lambda root : lambda : None,
                "virtualenv_class" : FakeVirtualEnv,
            },
        ),
    ]

    def test_named_virtualenvs_are_children(self):
        root = self.make_root()
        self.addCleanup(self.cleanup(root))
        locator = Locator(root=root, virtualenv_class=self.virtualenv_class)

        self.assertEqual(
            locator.for_name("one"),
            self.virtualenv_class(path=locator.root.child("one")),
        )
