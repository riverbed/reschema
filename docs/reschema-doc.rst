reschema-doc
============

This tool takes an input reschema file and generates HTML and PDF
documentation.

HTML: ::

  $ python bin/reschema-doc -f examples/bookstore.yaml -o /tmp -r 'bookstore' --html

This will read in the example ``bookstore.yaml`` file and generate both 
``bookstore.html``.

PDF: ::

    $ python bin/reschema-doc -f examples/bookstore.yaml -o /tmp -r 'bookstore' --pdf

This will generate ``bookstore.pdf``.  

Note that this relies on a tool called ``wkhtmltopdf``.  This must be
installed on the local machine and available via the default path or
specified via the -w option to reschema-doc.  

See http://code.google.com/p/wkhtmltopdf for more information.

