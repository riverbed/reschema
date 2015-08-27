#!/usr/bin/env python

# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import os
import os.path
import re
import datetime
import distutils.spawn
import subprocess
import HTMLParser

from optparse import OptionParser

import reschema
import reschema.html
from reschema import ServiceDef, ServiceDefManager
from reschema.tohtml import ServiceDefToHtml, Options


class ReschemaDocException(Exception):
    def __init__(self, msg):
        super(ReschemaDocException, self).__init__()
        self.msg = msg


class ReschemaDoc(object):
    def __init__(self):
        self.servicedefmgr = ServiceDefManager()

    def parse_args(self, args):
        self.parser = parser = OptionParser(
            description="Generate docuemnation for service defintions.")
        parser.add_option('-f', '--file', dest='filename',
                          help='JSON doc source file', action="store")

        parser.add_option('-r', '--related', dest='related',
                          help='JSON doc source file', action="append")

        parser.add_option('-o', '--outdir', dest='outdir', default=None,
                          help='Output directory', action="store")

        parser.add_option('--html', dest='html', default=False,
                          help="Generate HTML", action="store_true")

        parser.add_option('--pdf', dest='pdf', default=False,
                          help="Generate PDF", action="store_true")

        parser.add_option('-w', '--wkhtmltopdf', dest='wkhtmltopdf', default=None,
                          help='Path to wkhtmltopdf tool', action="store")

        parser.add_option('--copyright', dest='copyright', default=None,
                          help='Company and years for copyright, '
                          'eg "Riverbed Technology Inc. 2014"', action="store")

        parser.add_option('--nojson', action="store_true", default=False,
                          help='Do not include JSON tabs')

        parser.add_option('--noxml', action="store_true", default=False,
                          help='Do not include XML tabs')

        parser.add_option('--device', dest='device', default='{device}',
                          help='Device hosting this service')

        parser.add_option('--apiroot', dest='apiroot', default=None,
                          help='Root path for all resources')

        parser.add_option('--urlname', default=None,
                          help='Name of this service in the URL (if different than name)')

        (options, args) = parser.parse_args(args)

        if not options.filename:
            raise ReschemaDocException("-f FILENAME is required")

        if not options.outdir:
            raise ReschemaDocException("-o OUTDIR is required")

        if not options.pdf and not options.html:
            raise ReschemaDocException(
                "Output format of --pdf and/or --html must be specified")

        self.options = options

    def run(self):
        options = self.options

        servicedef = ServiceDef()
        servicedef.load(options.filename)
        self.servicedefmgr.add(servicedef)

        for related in (options.related or []):
            relateddef = ServiceDef()
            relateddef.load(related)
            self.servicedefmgr.add(relateddef)

        title = "%s v%s %s" % (servicedef.title, servicedef.version,
                               servicedef.status)

        name = (self.options.urlname or servicedef.name)
        relname = os.path.join(name, servicedef.version, 'service')

        outdir = options.outdir

        fullname = os.path.abspath(os.path.join(outdir, relname))
        fulldir = os.path.dirname(fullname)

        if not os.path.exists(fulldir):
            os.makedirs(fulldir)

        apiroot = options.apiroot or ("/api/%s/%s" %
                                      (servicedef.name, servicedef.version))

        # HTML version
        if options.html:
            html = fullname + '.html'
            if os.path.exists(html):
                os.remove(html)

            h = HTMLParser.HTMLParser()

            htmldoc = reschema.html.Document(title, printable=False)
            htmldoc.header.a(href="http://www.riverbed.com", cls="headerimg")
            hl = htmldoc.header.div(cls="headerleft")
            breadcrumbs = hl.div(cls="breadcrumbs")
            breadcrumbs.a(href="../../index.html").text = "apis"
            breadcrumbs.span().text = h.unescape(" &raquo; ")
            breadcrumbs.a(href=("../index.html")).text = name
            breadcrumbs.span().text = h.unescape(" &raquo; %s" % servicedef.version)
            hl.div(cls="headertitle").text = title
            htmldoc.header.span(cls="headerright").text = (
                "Created %s" %
                datetime.datetime.now().strftime("%b %d, %Y at %I:%M %p"))

            r2h = ServiceDefToHtml(servicedef, htmldoc.content, htmldoc.menu,
                                   device=options.device,
                                   apiroot=apiroot,
                                   options=Options(printable=False,
                                                   json=(not options.nojson),
                                                   xml=(not options.noxml),
                                                   apiroot=apiroot,
                                                   docroot=outdir))
            r2h.process()
            htmldoc.write(html)
            print "Wrote %s" % html

        # PDF
        if options.pdf:
            # First make a printable HTML
            phtml = fullname + '-printable.html'
            if os.path.exists(phtml):
                os.remove(phtml)

            htmldoc = reschema.html.Document(title, printable=True)
            r2h = ServiceDefToHtml(servicedef, htmldoc.content, htmldoc.menu,
                                   device=options.device,
                                   apiroot=apiroot,
                                   options=Options(printable=True,
                                                   json=(not options.nojson),
                                                   xml=(not options.noxml),
                                                   apiroot=apiroot,
                                                   docroot=outdir))
            r2h.process()
            htmldoc.write(phtml)
            print "Wrote %s" % phtml

            ### PDF
            if options.wkhtmltopdf is not None:
                wkhtmltopdf = options.wkhtmltopdf
            else:
                wkhtmltopdf = distutils.spawn.find_executable("wkhtmltopdf")
                if not wkhtmltopdf:
                    if not "WKHTMLTOPDF" in os.environ:
                        raise ReschemaDocException(
                            "Cannot find 'wkhtmltopdf' in path, "
                            "use -w <path> or set WKHTMLTOPDF env variable")
                    wkhtmltopdf = os.environ['WKHTMLTOPDF']

            args = [wkhtmltopdf, "--version"]
            lines = subprocess.check_output(args).split('\n')
            version = None
            for line in lines:
                g = re.search("wkhtmltopdf ([0-9]+)\.([0-9]+)", line)
                if g:
                    version = int(g.group(2))
                    break

            if version is None:
                print ("WARNING: Could not determine wkhtmltopdf version, "
                       "assuming latest")
            else:
                print "wkhtmltopdf version %d" % version

            if version is None or version >= 10:
                tocarg = "toc"
                coverarg = "cover"
            else:
                tocarg = "--toc"
                coverarg = "--cover"

            # create a cover apge
            cover = fullname + '-cover.html'
            cover_base = reschema.html.HTMLElement('html')
            cover_body = cover_base.body()
            cover_body.h1().text = title
            if options.copyright:
                cover_body.p().text = u"Copyright \xa9 " + unicode(options.copyright)
            created = datetime.datetime.now().strftime("%b %d, %Y at %I:%m %p")
            cover_body.p().text = "Created %s" % created

            f = open(cover, "w")
            f.write(reschema.html.ET.tostring(cover_base, method="html"))
            f.close()

            pdf = fullname + '.pdf'
            if os.path.exists(pdf):
                os.remove(pdf)

            args = [wkhtmltopdf,
                    '--title', title,
                    coverarg, cover,
                    tocarg, '--toc-header-text', 'Contents',
                    '--footer-center', '[page]',
                    phtml, pdf]
            #print ' '.join(args)
            subprocess.check_call(args)
            # Fix for 'illegal byte sequence'
            os.environ['LC_TYPE'] = 'C'
            os.environ['LANG'] = 'C'
            args = ['sed', '-i.bak', '-e', 's/#00//g', pdf]
            subprocess.check_call(args)
            print "Wrote %s" % pdf
            os.remove(pdf + ".bak")
