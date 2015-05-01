import os
import platform

from bp.filepath import FilePath
from characteristic import Attribute, attributes


@attributes([Attribute(name="root")])
class Locator(object):
    """
    Locates virtualenvs from a common root directory.

    """

    @classmethod
    def default(cls, **kwargs):
        workon_home = os.getenv("WORKON_HOME")
        if workon_home:
            root = workon_home
        else:
            # On OSX, seemingly the best place to put this is also
            # user_data_dir, but that's ~/Library/Application Support, which
            # means that any binaries installed won't be runnable because they
            # will get spaces in their shebangs. Emulating *nix behavior seems
            # to be the "rightest" thing to do instead.
            if platform.system() == "Darwin":
                root = os.path.expanduser("~/.local/share/virtualenvs")
            else:
                from appdirs import user_data_dir
                root = user_data_dir(appname="virtualenvs")
        return cls(root=FilePath(root), **kwargs)

    def for_directory(self, directory):
        """
        Find the virtualenv that would be associated with the given directory.

        """

        return self.for_name(directory.basename())

    def for_name(self, name=None):
        if not name:
            return self.root
        return self.root.child(name.lower().replace("-", "_"))

    def temporary(self):
        return self.for_name(".mkenv-temporary-env")

