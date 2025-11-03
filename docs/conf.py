# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
from datetime import datetime

# Add the project root to the Python path so Sphinx can find the package
sys.path.insert(0, os.path.abspath(".."))

# Import the version from the package
try:
    from sentinel_log_aggregator.version import __version__
except ImportError:
    __version__ = "0.1.0"

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Microsoft Sentinel Log Aggregator"
copyright = f"{datetime.now().year}, Microsoft Corporation"
author = "Microsoft Sentinel Team"
release = __version__
version = __version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",  # Auto-generate documentation from docstrings
    "sphinx.ext.viewcode",  # Add source code links
    "sphinx.ext.napoleon",  # Support for Google and NumPy style docstrings
    "sphinx.ext.intersphinx",  # Link to other project's documentation
    "sphinx.ext.todo",  # Support for todo items
    "sphinx.ext.coverage",  # Coverage statistics
    "myst_parser",  # Markdown support
]

# MyST parser configuration for Markdown support
myst_enable_extensions = [
    "tasklist",
    "deflist",
    "fieldlist",
    "colon_fence",
    "smartquotes",
    "replacements",
    "strikethrough",
    "substitution",
    "html_image",
]

# Source file suffixes
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# Theme options
html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "includehidden": True,
    "titles_only": False,
    "style_external_links": True,
}

# Custom CSS
html_css_files = []

# The master toctree document
master_doc = "index"

# -- Extension configuration -------------------------------------------------

# AutoDoc configuration
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}

# Napoleon configuration for Google-style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Intersphinx configuration
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# Todo configuration
todo_include_todos = True

# HTML options
html_title = f"{project} v{version}"
html_short_title = project
html_show_sourcelink = True
html_show_sphinx = True
html_show_copyright = True

# If building on Read the Docs, use their canonical URL
if os.environ.get("READTHEDOCS"):
    html_baseurl = f"https://{os.environ['READTHEDOCS_PROJECT']}.readthedocs.io/"

# Additional HTML context
html_context = {
    "display_github": True,
    "github_user": "TheAlistairRoss",
    "github_repo": "Sentinel-Log-Aggregator",
    "github_version": "main",
    "conf_py_path": "/docs/",
}

# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    "papersize": "letterpaper",
    "pointsize": "10pt",
    "preamble": "",
    "fncychap": "",
    "printindex": "",
}

# Grouping the document tree into LaTeX files
latex_documents = [
    (
        master_doc,
        "SentinelLogAggregator.tex",
        "Microsoft Sentinel Log Aggregator Documentation",
        "Microsoft Sentinel Team",
        "manual",
    ),
]

# -- Options for manual page output ------------------------------------------

# One entry per manual page
man_pages = [
    (
        master_doc,
        "sentinel-log-aggregator",
        "Microsoft Sentinel Log Aggregator Documentation",
        [author],
        1,
    )
]

# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files
texinfo_documents = [
    (
        master_doc,
        "SentinelLogAggregator",
        "Microsoft Sentinel Log Aggregator Documentation",
        author,
        "SentinelLogAggregator",
        "Microsoft Sentinel Log Aggregator for multi-workspace log aggregation.",
        "Miscellaneous",
    ),
]

# -- Options for Epub output -------------------------------------------------

# Bibliographic Dublin Core info
epub_title = project
epub_author = author
epub_publisher = author
epub_copyright = copyright
epub_exclude_files = ["search.html"]
