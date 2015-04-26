import os
import platform


VIRTUALENVS_ROOT = os.getenv("WORKON_HOME")
if not VIRTUALENVS_ROOT:
    # On OSX, seemingly the best place to put this is also
    # user_data_dir, but that's ~/Library/Application Support, which
    # means that any binaries installed won't be runnable because they
    # will get spaces in their shebangs. Emulating *nix behavior seems
    # to be the "rightest" thing to do instead.
    if platform.system() == "Darwin":
        VIRTUALENVS_ROOT = os.path.expanduser("~/.local/share/virtualenvs")
    else:
        from appdirs import user_data_dir
        VIRTUALENVS_ROOT = user_data_dir(appname="virtualenvs")
TEMPORARY_VIRTUALENV = os.path.join(VIRTUALENVS_ROOT, "mkenv-temp-venv")
