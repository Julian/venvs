from importlib import metadata
import re

# -- Project information -----------------------------------------------------

project = "venvs"
author = "Julian Berman"
copyright = "2015, " + author

release = metadata.version("venvs")
version = release.partition("-")[0]


# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinxcontrib.spelling",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# The reST default role (used for this markup: `text`) to use for all documents
default_role = "any"


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ["_static"]


# -- Extension configuration -------------------------------------------------

# -- Options for intersphinx extension ---------------------------------------

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {"https://docs.python.org/3/": None}

# -- Options for the linkcheck builder ------------------------------------


def entire_domain(host):
    return r"http.?://" + re.escape(host) + r"($|/.*)"


linkcheck_ignore = [
    "https://github.com/Julian/venvs/actions",
    "https://github.com/Julian/venvs/workflows/CI/badge.svg",
]

linkcheck_anchors = False

# -- Options for sphinxcontrib-spelling -----------------------------------

spelling_word_list_filename = "spelling-wordlist.txt"
