from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
import os

import nox

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
PYPROJECT = ROOT / "pyproject.toml"
DOCS = ROOT / "docs"
PACKAGE = ROOT / "venvs"

REQUIREMENTS = dict(
    main=ROOT / "requirements.txt",
    docs=DOCS / "requirements.txt",
)
REQUIREMENTS_IN = {
    (
        ROOT / "pyproject.toml"
        if path.absolute() == REQUIREMENTS["main"].absolute()
        else path.parent / f"{path.stem}.in"
    )
    for path in REQUIREMENTS.values()
}


SUPPORTED = ["3.10", "3.11", "3.12", "pypy3.10"]

nox.options.sessions = []


def session(default=True, **kwargs):  # noqa: D103
    def _session(fn):
        if default:
            nox.options.sessions.append(kwargs.get("name", fn.__name__))
        return nox.session(**kwargs)(fn)

    return _session


@session(python=SUPPORTED)
def tests(session):
    """
    Run the test suite with a corresponding Python version.
    """
    session.install("virtue", ROOT)

    if session.posargs and session.posargs[0] == "coverage":
        if len(session.posargs) > 1 and session.posargs[1] == "github":
            github = os.environ["GITHUB_STEP_SUMMARY"]
        else:
            github = None

        session.install("coverage[toml]")
        session.run("coverage", "run", "-m", "virtue", PACKAGE)
        if github is None:
            session.run("coverage", "report")
        else:
            with open(github, "a") as summary:
                summary.write("### Coverage\n\n")
                summary.flush()  # without a flush, output seems out of order.
                session.run(
                    "coverage",
                    "report",
                    "--format=markdown",
                    stdout=summary,
                )
    else:
        session.run("virtue", *session.posargs, PACKAGE)


@session(python=SUPPORTED)
def audit(session):
    """
    Audit Python dependencies for vulnerabilities.
    """
    session.install("pip-audit", "-r", REQUIREMENTS["main"])
    session.run("python", "-m", "pip_audit")


@session(tags=["build"])
def build(session):
    """
    Build a distribution suitable for PyPI and check its validity.
    """
    session.install("build", "twine")
    with TemporaryDirectory() as tmpdir:
        session.run("python", "-m", "build", ROOT, "--outdir", tmpdir)
        session.run("twine", "check", "--strict", tmpdir + "/*")


@session(default=False)
def pex(session):
    """
    Create a PEX for venvs.
    """
    session.install("pex")

    with ExitStack() as stack:
        if session.posargs:
            out = session.posargs[0]
        else:
            tmpdir = Path(stack.enter_context(TemporaryDirectory()))
            out = tmpdir / "venvs"
        session.run(
            "pex",
            ROOT,
            "--entry-point",
            "venvs",
            "--output-file",
            out,
        )


@session(default=False)
def shiv(session):
    """
    Build a shiv which will run venvs.
    """
    session.install("shiv")

    with ExitStack() as stack:
        if session.posargs:
            out = session.posargs[0]
        else:
            tmpdir = Path(stack.enter_context(TemporaryDirectory()))
            out = tmpdir / "venvs"
        session.run(
            "python",
            "-m",
            "shiv",
            "--reproducible",
            "-c",
            "venvs",
            "-r",
            REQUIREMENTS["main"],
            ROOT,
            "-o",
            out,
        )
        print(f"Outputted a shiv to {out}.")


@session(tags=["style"])
def style(session):
    """
    Check Python code style.
    """
    session.install("ruff")
    session.run("ruff", "check", ROOT)


@session(default=False)
def typing(session):
    """
    Check static typing.
    """
    session.install("pyright", ROOT)
    session.run("pyright", PACKAGE)


@session(tags=["docs"])
@nox.parametrize(
    "builder",
    [
        nox.param(name, id=name)
        for name in [
            "dirhtml",
            "doctest",
            "linkcheck",
            "man",
            "spelling",
        ]
    ],
)
def docs(session, builder):
    """
    Build the documentation using a specific Sphinx builder.
    """
    session.install("-r", REQUIREMENTS["docs"])
    with TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        argv = ["-n", "-T", "-W"]
        if builder != "spelling":
            argv += ["-q"]
        posargs = session.posargs or [tmpdir / builder]
        session.run(
            "python",
            "-m",
            "sphinx",
            "-b",
            builder,
            DOCS,
            *argv,
            *posargs,
        )


@session(tags=["docs", "style"], name="docs(style)")
def docs_style(session):
    """
    Check the documentation style.
    """
    session.install(
        "doc8",
        "pygments",
        "pygments-github-lexers",
    )
    session.run("python", "-m", "doc8", "--config", PYPROJECT, DOCS)


@session(default=False)
def requirements(session):
    """
    Update the project's pinned requirements. Commit the result.
    """
    session.install("pip-tools")
    for each in REQUIREMENTS_IN:
        session.run(
            "pip-compile",
            "--resolver",
            "backtracking",
            "--strip-extras",
            "-U",
            each.relative_to(ROOT),
        )
