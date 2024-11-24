from setuptools_scm import get_version

extensions = ["sphinx.ext.autodoc", "sphinx.ext.viewcode"]
templates_path = ["_templates"]
source_suffix = ".rst"
master_doc = "index"
project = "pthelma"
copyright = "2024, IRMASYS"
author = "Antonis Christofides"
version = get_version(root="..")
release = version
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
pygments_style = "sphinx"
html_theme = "alabaster"
html_static_path = ["_static"]
htmlhelp_basename = "pthelma"
latex_elements = {}
latex_documents = [
    (
        master_doc,
        "pthelma.tex",
        "pthelma Documentation",
        "Antonis Christofides",
        "manual",
    )
]
texinfo_documents = [
    (
        master_doc,
        "pthelma",
        "pthelma Documentation",
        author,
        "pthelma",
        "Utilities for hydrological and meteorological time series processing",
        "Miscellaneous",
    )
]


def setup(app):
    app.add_object_type(
        "confval",
        "confval",
        objname="configuration value",
        indextemplate="pair: %s; configuration value",
    )
