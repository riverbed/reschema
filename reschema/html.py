# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import os
import re
import xml.etree.ElementTree as ET

import reschema
ElementBase = ET.Element


class Document(object):
    def __init__(self, title, printable=False):
        self.printable = printable
        self.html = HTMLElement('html')
        self.head = self.html.head()
        self.head.title().text = title
        self.head.script(type="text/javascript", text="$script")
        self.head.style(type="text/css", text="$css")
        self.body = self.html.body(onload="set_favicon()")

        self.header = self.body.div(cls="header")
        if self.printable:
            self.header.attrib['style'] = 'display: none'

        if self.printable:
            self.main = self.body.div(cls="main-printable")
        else:
            self.main = self.body.div(cls="main")

        self.navbar = self.main.div(cls="navbar")
        if self.printable:
            self.navbar.attrib['style'] = 'display: none'
        self.toc = self.navbar.div(cls="toc")

        if self.printable:
            self.content = self.main.div(cls="content-printable")
        else:
            self.content = self.main.div(cls="content")

        self.menu = Menu(self.toc)

        self.footer = self.body.div(cls="footer")
        if self.printable:
            self.footer.attrib['style'] = 'display: none'

    def write(self, file):
        f = open(file, "w")
        text = ET.tostring(self.html, method="html")
        path = os.path.dirname(os.path.abspath(reschema.__file__))

        f2 = open(path + "/servicedef.css", "r")
        text = text.replace("$css", "<!--" + f2.read() + "-->")
        f2.close()

        f2 = open(path + "/servicedef.js", "r")
        text = text.replace("$script", f2.read())
        f2.close()

        text = text.replace("><pre", ">\n<pre")
        text = text.replace("</pre>", "</pre>\n")

        inpre = False
        for line in text.split("\n"):
            if inpre:
                if re.search("</pre>", line):
                    inpre = False
            else:
                if re.match("<pre", line):
                    if not re.search("</pre", line):
                        inpre = True
                else:
                    # Insert newline breaks before certain tags (but not all)
                    line = re.sub("><(div|p|ul|li|script|style|td|tr|th|table|col|colgroup)",
                                  ">\n<\\1",
                                  line)
            f.write(line + "\n")

        f.close()


class TabBar(object):
    def __init__(self, div, baseid, printable=False):
        self.div = div
        self.baseid_init = baseid
        self.baseid = baseid
        self.selected = True
        self.init = True
        self.count = 0
        self.printable = printable

    def init_tabbar(self):
        if self.printable:
            if self.count > 0:
                self.finish()
            self.baseid = self.baseid_init + str(self.count)
            self.count = self.count + 1
            self.selected = True
        self.tabContainer = self.div.div().div(cls='tabContainer', id='%s-tabs' % self.baseid)
        self.ul = self.tabContainer.div(cls='digiTabs', id='%s-tabbar' % self.baseid)
        self.init = False

    def add_tab(self, label, id, content):
        if self.init or self.printable:
            self.init_tabbar()

        self.ul.li(cls=('selected' if self.selected else None),
                   id='%s-tab-%s' % (self.baseid, id),
                   onclick='showtab("%s", "%s")' % (self.baseid, id)).text = label

        if self.selected:
            self.tabContainer.div(cls='tabContent', id='%s-tabcontent' % self.baseid).append(content)

        self.tabContainer.div(id='%s-%s' % (self.baseid, id), style='display:none').append(content)

        self.selected = False

    def finish(self):
        self.div.div(style="clear:both")


class HTMLElement(ElementBase):
    def __init__(self, name, *args, **kwargs):
        delargs = []
        for arg, value in kwargs.iteritems():
            if value is None:
                delargs.append(arg)
        for arg in delargs:
            del kwargs[arg]

        if 'cls' in kwargs:
            kwargs['class'] = kwargs['cls']
            del kwargs['cls']
        if 'text' in kwargs:
            self.text = kwargs['text']
            del kwargs['text']
        ElementBase.__init__(self, name, attrib=kwargs)

    def settext(self, *lst):
        last = None
        newlist = []

        # Need to first join up any strings in a row
        for e in lst:
            if last is not None:
                if (((type(last) is str) or (type(last) is unicode)) and
                    ((type(e) is str) or (type(e) is unicode))):
                    last += e
                else:
                    newlist.append(last)
                    last = e
            else:
                last = e
        newlist.append(last)

        last = None
        for e in newlist:
            if (type(e) is str) or (type(e) is unicode):
                if last is None:
                    self.text = e
                else:
                    last.tail = e
            else:
                last = e

    def tostring(self):
        return ET.tostring(self)

    def subelement(self, name, *args, **kwargs):
        sube = HTMLElement(name, **kwargs)
        self.append(sube)
        return sube

    def __getattr__(self, name):
        def method(*args, **kwargs):
            return self.subelement(name, *args, **kwargs)
        return method

    def table(self, *args, **kwargs):
        table = HTMLTable(*args, **kwargs)
        self.append(table)
        return table


class HTMLTable(HTMLElement):

    def __init__(self, *args, **kwargs):
        HTMLElement.__init__(self, 'table', *args, **kwargs)
        self._body = None

    def define_columns(self, classes):
        grp = self.colgroup()
        for _cls in classes:
            grp.col(cls=_cls)

    def row(self, cells, header=False):
        if self._body is None:
            self._body = self.tbody()

        tr = self._body.tr()
        tds = []
        for cell in cells:
            td = tr.th() if header else tr.td()
            tds.append(td)
            td.text = cell
        return tds


class Menu(HTMLElement):

    def __init__(self, parent, *args, **kwargs):
        HTMLElement.__init__(self, 'ul', *args, **kwargs)
        parent.append(self)

    def add_item(self, text, href=None):
        li = self.li()
        if href is not None:
            if isinstance(href, HTMLElement):
                href = '#' + href.attrib['id']
            li.a(href=href, text=text)

        else:
            li.text = text
        return li

    def add_submenu(self):
        return Menu(self)
