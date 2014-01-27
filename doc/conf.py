# -*- coding: utf-8 -*-
#
extensions = []
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
project = 'Pthelma'
copyright = '2005-2014, Antonis Christofides, National Technical University of Athens, TEI of Epirus'
version = 'a'
release = 'b'
today_fmt = '%B %d, %Y'
html_theme_path = ['.']
html_theme = 'enhydris_theme'
html_title = "Pthelma documentation"
html_static_path = ['_static']
html_last_updated_fmt = '%b %d, %Y'
htmlhelp_basename = 'pthelmadoc'
latex_documents = [
  ('index', 'pthelma.tex', 'Pthelma Documentation',
   'Antonis Christofides', 'manual'),
]
