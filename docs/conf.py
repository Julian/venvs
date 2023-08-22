import importlib.metadata
import re

project = "venvs"
author = "Julian Berman"
copyright = f"2015, {author}"

release = importlib.metadata.version("venvs")
version = release.partition("-")[0]

language = "en"
default_role = "any"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinxcontrib.spelling",
]

pygments_style = "lovelace"
pygments_dark_style = "one-dark"

html_theme = "furo"


def entire_domain(host):
    return r"http.?://" + re.escape(host) + r"($|/.*)"


linkcheck_ignore = [
    entire_domain("img.shields.io"),
    "https://github.com/.*#.*",
    "https://github.com/Julian/venvs/actions",
    "https://github.com/Julian/venvs/workflows/CI/badge.svg",
]

# = Extensions =

# -- autodoc --

autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
}
# -- intersphinx --

intersphinx_mapping = {
    "python": ("https://docs.python.org/", None),
}

# -- sphinxcontrib-spelling --

spelling_word_list_filename = "spelling-wordlist.txt"
