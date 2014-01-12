reschema
========

This directory contains a library for parsing <rest-schema> objects
that describe a REST API.  The <rest-schema> format is described in GL4v2.

reschema-doc
============

This tool takes an input reschema file and generates HTML and PDF
documentation.

HTML:

  $ python bin/reschema-doc -f examples/Catalog.yml -o /tmp -r 'catalog' --html

This will read in the example Catalog.yml file and generate both 
'catalog.html'.

PDF: 

  $ python bin/reschema-doc -f examples/Catalog.yml -o /tmp -r 'catalog' --pdf

This will generate 'catalog.pdf'.  

Note that this relies on a tool called 'wkhtmltopdf'.  This must be
installed on the local machine and available via the default path or
specified via the -w option to reschema-doc.  

See http://code.google.com/p/wkhtmltopdf for more information.

