from pathlib import Path

import nox

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
PYPROJECT = ROOT / "pyproject.toml"
DOCS = ROOT / "docs"
PACKAGE = ROOT / "venvs"


nox.options.sessions = []


def session(default=True, **kwargs):
    def _session(fn):
        if default:
            nox.options.sessions.append(kwargs.get("name", fn.__name__))
        return nox.session(**kwargs)(fn)

    return _session


@session(python=["3.9", "3.10", "3.11", "pypy3"])
def tests(session):
    session.install("virtue", "-r", ROOT / "requirements.txt", ROOT)
    if session.posargs == ["coverage"]:
        session.install("coverage[toml]")
        session.run("coverage", "run", "-m", "virtue")
        session.run("coverage", "report")
    else:
        session.run("virtue", *session.posargs, PACKAGE)


@session(tags=["build"])
def build(session):
    session.install("build")
    tmpdir = session.create_tmp()
    session.run("python", "-m", "build", ROOT, "--outdir", tmpdir)


@session(tags=["style"])
def readme(session):
    session.install("build", "twine")
    tmpdir = session.create_tmp()
    session.run("python", "-m", "build", ROOT, "--outdir", tmpdir)
    session.run("python", "-m", "twine", "check", tmpdir + "/*")


@session(tags=["style"])
def style(session):
    session.install("ruff")
    session.run("ruff", "check", ROOT)


@session(default=False)
def typing(session):
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
    session.install("-r", DOCS / "requirements.txt")
    tmpdir = Path(session.create_tmp())
    argv = ["-n", "-T", "-W"]
    if builder != "spelling":
        argv += ["-q"]
    session.run(
        "python",
        "-m",
        "sphinx",
        "-b",
        builder,
        DOCS,
        tmpdir / builder,
        *argv,
    )


@session(tags=["docs", "style"], name="docs(style)")
def docs_style(session):
    session.install(
        "doc8",
        "pygments",
        "pygments-github-lexers",
    )
    session.run("python", "-m", "doc8", "--config", PYPROJECT, DOCS)


@session(default=False)
def pex(session):
    session.install("pex")
    session.run(
        "pex",
        ROOT,
        "--entry-point",
        "venvs",
        "--output-file",
        DIST / "venvs",
    )


@session(default=False)
def shiv(session):
    session.install("shiv")
    session.run(
        "shiv",
        "-c",
        "venvs",
        "-o",
        DIST / "venvs",
        "-r",
        ROOT / "requirements.txt",
        ROOT,
    )


@session(default=False)
def requirements(session):
    session.install("pip-tools")
    for each in [DOCS / "requirements.in", ROOT / "pyproject.toml"]:
        session.run(
            "pip-compile",
            "--resolver",
            "backtracking",
            "-U",
            each.relative_to(ROOT),
        )
