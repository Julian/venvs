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
wherever ``$WORKON_HOME`` points). Each entry declares a venv using one
of three table types depending on intent:

.. code-block:: toml

    # [tool.X]: install package X and link its console scripts.
    # Defaults: install = ["X"], link = scripts declared by X.
    [tool.black]
    [tool.ruff]

    [tool.jsonschema]
    extras = ["format"]              # → install jsonschema[format]
    install = ["jsonschema-cli"]     # additional packages (scripts not linked)

    # [dev.X]: a venv tracking a local project checkout, converged via
    # `uv sync`. Disk dir is `X-dev` and auto-linked scripts get a `-dev`
    # suffix, so `[tool.X]` and `[dev.X]` coexist without colliding.
    [dev.jsonschema]
    project = "~/Development/jsonschema"
    groups = ["test"]

    # [venv.X]: the explicit/escape-hatch table. All keys, no smart defaults.
    [venv.development]
    install = ["pudb", "twisted"]
    link = ["trial"]

    [venv.app]
    install = ["flask"]
    python = "python3.12"
    link = ["flask:flask-app"]

Running ``venvs converge`` creates each venv, installs (or syncs) the
specified packages, and symlinks the named binaries into ``~/.local/bin/``.

``[virtualenv.X]`` is also accepted as a back-compat alias for ``[venv.X]``.


Config Reference
^^^^^^^^^^^^^^^^

``[tool.X]``
""""""""""""

Sugar for ``uv tool install``-style venvs: one published package, its
scripts auto-linked.

``extras``
    Package extras for the primary package, e.g. ``["format"]`` →
    installs ``X[format]``.

``install``
    *Additional* (companion) packages, like ``uv tool install ... --with``.
    Their scripts are not auto-linked.

``install-bundle``
    List of bundle names to install (see Bundles below). Scripts from
    bundle packages are not auto-linked.

``python``
    Python interpreter to use (default: ``python3``).

``link``
    Explicit override of the auto-discovered link list. Use
    ``"source:target"`` to rename. ``link = []`` disables linking entirely.

``link-module``
    Modules to expose as ``python -m <module>`` wrappers.

``post-commands``
    Commands to run after converging.

``[dev.X]``
"""""""""""

A venv backed by a local Python project (typically a checkout you are
developing). Converged via ``uv sync`` against the project's
``pyproject.toml`` / ``uv.lock``. Disk dir is always ``X-dev``.

``project`` (required)
    Path to the project directory (supports ``$ENV_VAR`` and ``~/``
    expansion).

``groups``
    PEP 735 dependency groups to install, e.g. ``["test", "docs"]``.

``extras``
    Project extras to install, e.g. ``["cli"]``.

``link``, ``link-module``, ``post-commands``
    As for ``[tool.X]``. Auto-linked scripts get a ``-dev`` suffix on
    their targets; explicit ``link = [...]`` is used verbatim.

``[venv.X]``
""""""""""""

The explicit table — use this when ``[tool.X]`` / ``[dev.X]`` don't fit.
All of: ``install`` (list of packages), ``requirements`` (list of
``requirements.txt`` files), ``install-bundle``, ``python``, ``link``,
``link-module``, ``post-commands``.

Bundles
"""""""

Bundles are reusable package groups, referenceable from ``[venv.X]`` and
``[tool.X]``:

.. code-block:: toml

    [bundle]
    dev = ["pytest", "ruff", "mypy"]

    [venv.myproject]
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

``--dry-run``
    Print what would be done (orphan removals, creates, updates with
    the specific reason, skips) without making any changes. Exits 0
    if the configuration is already converged, 2 if any changes
    would be made, and non-zero on error. Cannot be combined with
    ``--fail-fast``.

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
