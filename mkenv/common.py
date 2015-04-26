import os
import platform

from bp.filepath import FilePath


_VIRTUALENVS_ROOT = os.getenv("WORKON_HOME")
if not _VIRTUALENVS_ROOT:
    # On OSX, seemingly the best place to put this is also
    # user_data_dir, but that's ~/Library/Application Support, which
    # means that any binaries installed won't be runnable because they
    # will get spaces in their shebangs. Emulating *nix behavior seems
    # to be the "rightest" thing to do instead.
    if platform.system() == "Darwin":
        _VIRTUALENVS_ROOT = os.path.expanduser("~/.local/share/virtualenvs")
    else:
        from appdirs import user_data_dir
        _VIRTUALENVS_ROOT = user_data_dir(appname="virtualenvs")

VIRTUALENVS_ROOT = FilePath(_VIRTUALENVS_ROOT)
TEMPORARY_VIRTUALENV = VIRTUALENVS_ROOT.child(".mkenv-temporary-env")
