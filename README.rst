=====
venvs
=====

|PyPI| |CI|

``venvs`` is a tool for configuring, in a single file, a set of
virtualenvs, which packages to install into each, and any binaries to
make globally available from within.

It is a thin layer on top of `uv <https://docs.astral.sh/uv/>`_,
adding a declarative configuration format.


Installation
------------

::

    uv tool install venvs

``uv`` must be installed and on your ``PATH``.


Configuration
-------------

Create a file at ``~/.local/share/virtualenvs/virtualenvs.toml`` (or
wherever ``$WORKON_HOME`` points). Here's an example:

.. code-block:: toml

    [virtualenv.development]
    install = [
        "pudb",
        "twisted",
    ]
    link = ["trial"]

    [virtualenv.app]
    install = ["flask"]
    python = "python3.12"
    link = ["flask:flask-app"]

    [virtualenv.tools]
    install = ["ipython"]
    link-module = ["IPython:ipy"]

Running ``venvs converge`` will create each virtualenv, install the
specified packages, and symlink the named binaries into
``~/.local/bin/``.


Config Reference
^^^^^^^^^^^^^^^^

Each ``[virtualenv.<name>]`` section supports:

``install``
    List of packages to install (supports ``$ENV_VAR`` and ``~/``
    expansion).

``requirements``
    List of requirements files to install from.

``python``
    Python interpreter to use (default: ``python3``).

``install-bundle``
    List of bundle names to include (see below).

``link``
    List of binaries to symlink into the link directory. Use
    ``"source:target"`` to rename, e.g. ``"black:black3.12"``.

``link-module``
    List of modules to make available as wrapper scripts that run
    ``python -m <module>``. Use ``"module:name"`` to rename.

``post-commands``
    List of commands (as arrays) to run after converging, e.g.
    ``[["touch", "/tmp/done"]]``.

Bundles
"""""""

Bundles are reusable package groups:

.. code-block:: toml

    [bundle]
    dev = ["pytest", "ruff", "mypy"]

    [virtualenv.myproject]
    install = ["mypackage"]
    install-bundle = ["dev"]


Usage
-----

``venvs converge``
^^^^^^^^^^^^^^^^^^

Converge the configured set of virtualenvs::

    $ venvs converge

Specific virtualenvs can be targeted::

    $ venvs converge myproject tools

Options:

``--fail-fast``
    Stop on the first failure (default: continue and report errors at
    the end).

``--link-dir <path>``
    Directory to symlink binaries into (default: ``~/.local/bin``).

``--root <path>``
    Root directory for virtualenvs (default: platform-specific, or
    ``$WORKON_HOME``).

Converge is idempotent -- if the configuration and Python version
haven't changed and the virtualenv is healthy, it is skipped.
Virtualenvs that are no longer in the configuration are automatically
removed along with their symlinks. Broken virtualenvs (e.g. from a
deleted Python installation) are automatically recreated.

Virtualenvs are converged in parallel.

``venvs find``
^^^^^^^^^^^^^^

Find virtualenv paths::

    $ venvs find                    # print the root directory
    $ venvs find name myproject     # print the virtualenv path
    $ venvs find name myproject python  # print path to a binary


Releasing
---------

Releases are managed via `cargo-release <https://github.com/crate-ci/cargo-release>`_::

    $ cargo release 2026.5.1


.. |PyPI| image:: https://img.shields.io/pypi/v/venvs.svg
   :alt: PyPI version
   :target: https://pypi.org/project/venvs/

.. |CI| image:: https://github.com/Julian/venvs/workflows/CI/badge.svg
  :alt: Build status
  :target: https://github.com/Julian/venvs/actions?query=workflow%3ACI
