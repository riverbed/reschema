# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import re
import sys
import copy
import json
import yaml
import markdown
from collections import OrderedDict
import xml.dom.minidom, xml.etree.ElementTree as ET
import urlparse
import jsonpointer

import logging
logger = logging.getLogger(__name__)

import reschema
from reschema.html import HTMLElement, HTMLTable, Document as HTMLDoc, TabBar
from reschema.jsonschema import Schema
from reschema.util import a_or_an, str_to_id as html_str_to_id
from reschema.exceptions import NoManager


class Options(object):
    def __init__(self, printable=False, json=True, xml=True,
                 apiroot="/{root}", docroot='.'):
        self.printable = printable
        self.json = json
        self.xml = xml
        self.apiroot = apiroot
        self.docroot = docroot


class RefSchemaProxy(object):

    def __init__(self, schema, options=None, attrname='refschema'):
        self.schema = schema
        self.options = options

        try:
            self.passthrough = True
            self.refschema = getattr(schema, attrname)
            refid = self.refschema.fullid()
            self.name = self.refschema.name
            self.typestr = self.refschema.typestr
        except NoManager:
            self.passthrough = False
            refid = getattr(schema, '_' + attrname + '_id')
            self.name = refid.split('/')[-1]
            self.typestr = '<ref>'
            self.description = refid

        # refid is something like:
        #   http://support.riverbed.com/apis/test/1.0#/types/type_number_limits
        #
        # Drop the netloc and api root and replace with a relative path ref
        # based on the current schema id
        parsed_id = urlparse.urlparse(refid)

        # Fall back to just using an href of the schema id for the
        # following cases:
        #  - not a riverbed service
        #  - no match to '/apis'
        #  - looking for printable format
        m = re.match("/apis/(.*)$", parsed_id.path)
        if (parsed_id.netloc != 'support.riverbed.com' or
                not m or self.options.printable):
            self.href = refid
        else:
            # Build a relative link based on the difference between this
            # schema id and the refschema id.
            #
            # Figure out how many levels up to recurse -- up to the first diff
            parsed_parent_id = urlparse.urlparse(schema.servicedef.id)
            m_parent = re.match("/apis/(.*)$", parsed_parent_id.path)
            relpath_count = len(m_parent.group(1).split('/'))
            relpath = '/'.join(['..' for i in range(relpath_count)])

            frag_id = html_str_to_id(parsed_id.fragment)
            self.href = ('%s/%s/service.html#%s' %
                         (relpath, m.group(1), frag_id))

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]

        if self.__dict__['passthrough']:
            return getattr(self.refschema, name)
        else:
            return None


class ServiceDefToHtml(object):
    servicedef = None

    def __init__(self, servicedef, container, menu=None, options=None,
                 device="{device}", apiroot="/{root}"):
        ServiceDefToHtml.servicedef = servicedef
        self.servicedef = servicedef
        self.container = container
        self.menu = menu
        self.options = (options or Options())
        self.servicepath = "http://%s%s" % (device, apiroot)

    def process(self):

        resources_div = self.container.div(id='resources')
        self.menu.add_item("Resources", href=resources_div)
        resource_menu = self.menu.add_submenu()
        for resource in self.servicedef.resources.values():
            ResourceToHtml(resource, self.container, resource_menu,
                           self.servicepath, self.options).process()

        types_div = self.container.div(id='types')
        self.menu.add_item("Types", href=types_div)
        type_menu = self.menu.add_submenu()
        for type_ in self.servicedef.types.values():
            rh = ResourceToHtml(type_, self.container, type_menu,
                                self.servicepath, self.options)
            rh.process(is_type=True)


class ResourceToHtml(object):
    def __init__(self, schema, container, menu=None, basepath="",
                 options=None):
        self.schema = schema
        self.menu = menu
        self.container = container
        self.basepath = basepath
        self.options = (options or Options())

    def read(self, filename, pointer=None, additional=None):
        if filename == "-":
            f = sys.stdin
        else:
            f = open(filename, "r")

        if filename.endswith('.json'):
            input = json.load(f, object_pairs_hook=OrderedDict)
        elif filename.endswith(('.yml', '.yaml')):
            input = yaml.load(f)
        else:
            raise ValueError(
              "Unrecognized file extension, use '*.json' or '*.yml': %s" %
              filename)

        if additional:
            for a in additional:
                a_input = jsonpointer.resolve_pointer(input, pointer)
                Schema.parse(a_input, name=a)

        name = 'root'
        if pointer:
            input = jsonpointer.resolve_pointer(input, pointer)
            name = pointer

        self.schema_raw = input
        self.schema = Schema.parse(input, name=name)

        if f is not sys.stdin:
            f.close()

    def process(self, is_type=False):
        logger.debug("Processing resource: %s" % self.schema.fullname())
        menu = self.menu
        schema = self.schema
        baseid = html_str_to_id(schema.fullid(True))
        div = self.container.div(id=baseid)
        menu.add_item(schema.name, href=div)

        div.h2().text = ('Type: ' if is_type else 'Resource: ') + schema.name
        if schema.description != '':
            div.p().text = schema.description

        if (not is_type):
            uri = schema.links['self'].path.template
            if uri[0] == '$':
                uri = self.basepath + uri[1:]
            div.pre().text = uri

        self.schema_table(schema, div, baseid)

        if (not is_type):
            div.h3(id="links").text = "Links"
            self.process_links(div, baseid)

            if self.schema.relations:
                div.h3(id="relations").text = "Relations"
                self.process_relations(div, baseid)


    def schema_table(self, schema, container, baseid):
        tabbar = TabBar(container, baseid + '-tabbar',
                        printable=self.options.printable)
        if self.options.json:
            tabbar.add_tab("JSON", baseid + '-json',
                           SchemaSummaryJson(schema, self.options))
        if self.options.xml:
            tabbar.add_tab("XML", baseid + '-xml',
                           SchemaSummaryXML(schema, self.options))
        # tabbar.add_tab("JSON Schema", "jsonschema",
        #               HTMLElement("pre",
        #                            text=json.dumps(self.schema_raw,
        #                           indent=2)))
        tabbar.finish()
        container.append(SchemaTable(schema, self.options))

    def process_links(self, container, containerid):
        schema = self.schema
        for name, link in schema.links.iteritems():
            if name == 'self':
                # need to police invalid $refs underneath params
                for k, v in link.path.var_schemas.iteritems():
                    if isinstance(v, reschema.jsonschema.Ref):
                        RefSchemaProxy(v, self.options)
                continue

            logger.debug("Processing link: %s - %s" %
                         (self.schema.fullname(), name))

            baseid = containerid + '-link-%s' % name
            div = container.div(id=baseid, cls="link-body")
            div.h4().text = link.schema.fullname() + ": " + link.name
            div.p().text = link.description

            uri = link.path.template
            if uri[0] == '$':
                uri = self.basepath + uri[1:]

            path = uri

            httpmethod = link.method
            if httpmethod == "GET":
                # Handle link.request as parameters
                if link.request is not None and \
                       type(link.request) != reschema.jsonschema.Null:
                    properties = link.request.properties
                    params = ["%s={%s}" % (param, properties[param].typestr)
                              for param in properties.keys()]
                    if len(params) != 0:
                        path += "?" + "&".join(params)

            div.pre().text = httpmethod + " " + path

            # if link.headers:
                # div.span(cls="h5").text = "HTTP Headers"
                # table = div.table(cls="paramtable")
                # div.append(ParamTable(link.headers))
                # table.row(["Name", "Type", "Description"], header=True)
                # for name in link.parameters:
                #    p = link.parameters[name]
                #    table.row([name, p.typestr, p.description])

            if httpmethod != "GET":
                if link.request is not None and \
                       type(link.request) != reschema.jsonschema.Null and \
                       httpmethod != "GET":

                    div.span(cls="h5").text = "Request Body"

                    # Need to look at the raw link._request to see if it's
                    # a ref, as link.request is auto-resolved thru refs
                    if type(link._request) is reschema.jsonschema.Ref:
                        p = div.p()

                        schema = RefSchemaProxy(link._request, self.options)
                        p.settext("Provide ",
                                  a_or_an(schema.name),
                                  " ",
                                  p.a(cls="jsonschema-type", href=schema.href,
                                      text=schema.name),
                                  " data object.")
                    elif type(link.request) is reschema.jsonschema.Data:
                        p = div.p()
                        if link.request.description is None:
                            description = "data"
                        else:
                            description = "the " + link.request.description
                            p.settext(("Provide a request body containing %s "
                                       "with content type ") % description,
                                      p.span(cls="content-attribute",
                                             text=link.request.content_type),
                                      ".")
                    else:
                        p = div.p().text = ("Provide a request body with the "
                                            "following structure:")
                        self.schema_table(link.request, div,
                                          baseid + '-request')

                elif httpmethod in ("PUT", "POST"):
                    div.span(cls="h5").text = "Request Body"
                    div.p().text = "Do not provide a request body."

            div.span(cls="h5").text = "Response Body"
            # Need to look at the raw link._response to see if it's
            # a ref, as link.response is auto-resolved thru refs
            schema = link._response
            if schema is not None and \
                   type(schema) is not reschema.jsonschema.Null:
                if type(schema) is reschema.jsonschema.Ref:
                    p = div.p()
                    schema = RefSchemaProxy(link._response, self.options)
                    p.settext("Returns ",
                              a_or_an(schema.name),
                              " ",
                              p.a(cls="jsonschema-type", href=schema.href, text=schema.name),
                              " data object.")
                elif type(schema) is reschema.jsonschema.Data:
                    p = div.p()
                    p.settext("On success, the server returns a response body "
                              "containing data with content type ",
                              p.span(cls="content-attribute",
                                     text=schema.content_type),
                              ".")
                else:
                    p = div.p().text = ("On success, the server returns a "
                                        "response body with the following "
                                        "structure:")
                    self.schema_table(link.response, div, baseid + '-response')

            else:
                div.p().text = ("On success, the server does not provide any "
                                "body in the responses.")

            # XXXCJ - this code may still be needed, but not yet functional
            if None and link.examples is not None:
                div.span(cls="h5").text = "Examples"
                for ex in link.examples:
                    text = ex['text']
                    html = markdown.markdown(text)
                    md_html = ET.XML("<div>" + html + "</div>")
                    div.append(md_html)

        return None

    def process_relations(self, container, containerid):
        schema = self.schema
        for name, relation in schema.relations.iteritems():

            logger.debug("Processing relation: %s - %s" %
                         (self.schema.fullname(), name))

            baseid = containerid + '-relation-%s' % name
            div = container.div(id=baseid, cls="relation-body")
            div.h4().text = relation.schema.fullname() + ": " + relation.name
            div.p().text = relation.description

            div.span(cls="h5").text = "Related resource"
            target_schema = RefSchemaProxy(relation, self.options,
                                           attrname='resource')
            p = div.p()
            p.settext(p.a(cls="jsonschema-type", href=target_schema.href,
                          text=target_schema.name))

            if relation.vars:
                div.span(cls="h5").text = "Variables"
                table = HTMLTable(cls="paramtable")
                table.row(["Related var", "Data value for replacement"],
                          header=True)
                for var, relp in relation.vars.iteritems():
                    table.row([var, relp])
                div.append(table)


class SchemaSummaryJson(HTMLElement):
    def __init__(self, schema, options):
        HTMLElement.__init__(self, "pre", cls="servicedef")
        self.options = options
        self.process(self, schema, 0)

        if isinstance(schema, reschema.jsonschema.Ref):
            example = schema.refschema.example
        else:
            example = schema.example

        if example is not None:
            self.span().text = ("\n\nExample:\n%s\n" %
                                json.dumps(example, indent=2))

    def process(self, parent, schema, indent=0):
        if isinstance(schema, reschema.jsonschema.Object):
            self.process_object(parent, schema, indent)

        elif isinstance(schema, reschema.jsonschema.Array):
            self.process_array(parent, schema, indent)

        elif isinstance(schema, reschema.jsonschema.Ref):
            schema = RefSchemaProxy(schema, self.options)
            parent.a(cls="servicedef-type", href=schema.href, text=schema.name)

        elif isinstance(schema, reschema.jsonschema.Merge):
            self.process(parent, schema.refschema, indent)

        else:
            parent.span(cls="servicedef-type").text = schema.typestr

    def process_object(self, parent, obj, indent):
        logger.debug("process_object: obj: %s" % obj.fullname())
        parent.span().text = "{\n"
        last = None
        for k in obj.properties:
            if last is not None:
                last.text = ",\n"

            txt = ('%*.*s"%s": ' % (indent + 2, indent + 2, "", k))
            parent.span(cls="servicedef-property").text = txt

            s = parent.span()
            self.process(s, obj.properties[k], indent + 2)
            last = parent.span()
            last.text = '\n'

        if obj.additional_properties:
            if last is not None:
                last.text = ",\n"
            if obj.additional_properties is True:
                txt = '%*.*s%s' % (indent + 2, indent + 2, "", 'prop')
                parent.span(cls="servicedef-type").text = txt
                parent.span().text = ": "
                parent.span(cls="servicedef-type").text = 'value'
            else:
                txt = '%*.*s%s' % (indent + 2, indent + 2, "",
                                   obj.additional_properties.name)
                parent.span(cls="servicedef-type").text = txt
                parent.span().text = ": "
                s = parent.span()
                self.process(s, obj.additional_properties, indent + 2)

            last = parent.span()
            last.text = '\n'

        parent.span().text = "%*.*s}" % (indent, indent, "")

    def process_array(self, parent, array, indent):
        item = array.children[0]
        if isinstance(item, reschema.jsonschema.Ref):
            s = parent.span()
            schema = RefSchemaProxy(item, self.options)
            s.settext("[ ", s.a(cls="servicedef-type",
                                href=schema.href, text=schema.name),
                       " ]")

        else:
            parent.span().text = "[\n%*.*s" % (indent + 2, indent + 2, "")
            self.process(parent.span(), item, indent + 2)
            parent.span().text = "\n%*.*s]" % (indent, indent, "")


class SchemaSummaryXML(HTMLElement):
    def __init__(self, schema, options):
        HTMLElement.__init__(self, "pre", cls="servicedef")
        self.options = options
        self.text = self.process(self, schema, 0)

        if type(schema) is reschema.jsonschema.Ref:
            example = schema.refschema.example
        elif schema.xmlExample is not None:
            # XXX/demmer hack to support types that don't have
            # GL4-compliant XML/JSON
            self.span().text = "\n\nExample:\n%s\n" % schema.xmlExample
            example = None
        else:
            example = schema.example

        if example is not None:
            example_xml = schema.toxml(example)

            x2 = xml.dom.minidom.parseString(ET.tostring(example_xml))
            xs = x2.toprettyxml(indent="  ").split("\n")

            if re.search("\?xml", xs[0]):
                # Remove the leading "xml" tag
                xs = xs[1:]

            example_str = "\n".join(xs)

            self.span().text = "\n\nExample:\n%s\n" % example_str


    def process(self, parent, schema, indent=0, name=None,
                json=None, key=None):
        if (not isinstance(schema, reschema.jsonschema.Ref) and
                schema.xmlSchema is not None):
            # XXX/demmer this is a big hack to support the fact that
            # one of the Shark REST handlers doesn't return
            # GL5-compliant output. The JSON is properly described by
            # the schema, the but XML is specified separately.
            def write_xmlschema(tag, spec, indent):
                parent.span().text = "%*s<" % (indent, "")
                parent.span(cls="xmlschema-element").text = tag
                first = True
                attr_indent = "\n%*s" % (indent + 2 + len(tag), "")

                if 'attributes' in spec:
                    for attr in spec['attributes']:
                        typestr = spec['attributes'][attr]
                        parent.span(cls="xmlschema-attribute").text = (
                          '%s%s' % (" " if first else attr_indent, attr))
                        parent.span().text = '='
                        parent.span(cls="xmlschema-type").text = typestr
                        first = False

                if 'children' in spec:
                    parent.span().text = ">\n"
                    for child_tag, child_spec in spec['children'].items():
                        write_xmlschema(child_tag, child_spec, indent + 2)
                    parent.span().text = "%*s</" % (indent, "")
                    parent.span(cls="xmlschema-element").text = tag
                    parent.span().text = ">\n"
                else:
                    parent.span().text = "/>\n"

            assert (len(schema.xmlSchema.keys()) == 1)
            tag = schema.xmlSchema.keys()[0]
            spec = schema.xmlSchema[tag]
            write_xmlschema(tag, spec, 0)
            return

        name = name or schema.name
        if name == "[]":
            name = "items"
        if type(schema) is reschema.jsonschema.Object:
            self.process_object(parent, schema, indent, name, key=key)

        elif isinstance(schema, reschema.jsonschema.Array):
            self.process_array(parent, schema, indent, name, key=key)

        elif isinstance(schema, reschema.jsonschema.Ref):
            schema = RefSchemaProxy(schema, self.options)
            if not name:
                name = schema.name
            if key:
                parent.span(cls="xmlschema-element").text = (
                  "%*s<%s key=string>" % (indent, "", name))
            else:
                parent.span(cls="xmlschema-element").text = (
                  "%*s<%s>" % (indent, "", name))

            parent.a(cls="xmlschema-type", href=schema.href, text=name)
            parent.span(cls="xmlschema-element").text = "</%s>\n" % (name)

        else:
            if key:
                parent.span(cls="xmlschema-element").text = (
                  "%*s<%s " % (indent, "", name))
                parent.span(cls="xmlschema-attribute").text = key
                parent.span().text = "="
                parent.span(cls="xmlschema-type").text = "string"
                parent.span().text = ">"
            else:
                parent.span(cls="xmlschema-element").text = (
                  "%*s<%s>" % (indent, "", name))
            parent.span(cls="xmlschema-type").text = "%s" % schema.typestr
            parent.span(cls="xmlschema-element").text = "</%s>\n" % (name)

    def process_object(self, parent, obj, indent, name, key=None):
        parent.span().text = "%*s<" % (indent, "")
        parent.span(cls="xmlschema-element").text = name
        subelems = obj.additional_properties
        first = True
        attr_indent = "\n%*s" % (indent + 2 + len(name), "")

        for k in obj.properties:
            prop = obj.properties[k]
            if not prop.is_simple():
                subelems = True
                continue
            parent.span(cls="xmlschema-attribute").text = (
              '%s%s' % (" " if first else attr_indent, k))
            parent.span().text = '='
            parent.span(cls="xmlschema-type").text = prop.typestr
            first = False

        if subelems:
            parent.span().text = ">\n"
        else:
            parent.span().text = "/>\n"

        for k in obj.properties:
            prop = obj.properties[k]
            if prop.is_simple():
                continue
            s = parent.span()
            self.process(s, prop, indent + 2, name=k)

        if obj.additional_properties is True:
            pass
        elif obj.additional_properties:
            s = parent.span()

            subobj = copy.copy(obj.additional_properties)
            keyname = subobj.xmlKeyName or 'key'
            try:
                subobj.properties = OrderedDict()
                json = {'id':keyname, 'type':'string',
                        'description':'property name'}
                subobj.properties[keyname] = subobj.schema.parse(json,
                                                            keyname,
                                                            subobj)
                for k in obj.additional_properties.props:
                    subobj.props[k] = obj.additional_properties.props[k]
            except:
                pass
            self.process(s, subobj, indent + 2, name=subobj.name, key=keyname)

        if subelems:
            parent.span().text = "%*s</" % (indent, "")
            parent.span(cls="xmlschema-element").text = name
            parent.span().text = ">\n"

    def process_array(self, parent, array, indent, name, key):
        parent.span().text = "%*s<" % (indent, "")
        parent.span(cls="xmlschema-element").text = name
        parent.span().text = ">\n"
        self.process(parent.span(), array.children[0], indent + 2,
                     name=array.children[0].name)
        parent.span().text = "%*s</" % (indent, "")
        parent.span(cls="xmlschema-element").text = name
        parent.span().text = ">\n"


class PropTable(HTMLTable):
    def __init__(self, data, options):
        self.options = options
        HTMLTable.__init__(self, cls="paramtable")

        logger.debug("PropTable")

        self.define_columns(["paramtable-propname",
                             "paramtable-proptype",
                             "paramtable-description",
                             "paramtable-notes"])
        self.row(["Property Name", "Type", "Description", "Notes"],
                 header=True)

        self.process(data)

    def process(self, data):
        pass

    def setname(self, elem, name):
        if not name:
            return
        limit = 40
        L = re.split("[.[]", name)
        line = 0
        for i in range(len(L)):
            if L[i][-1] == "]":
                text = "[" + L[i]
            else:
                text = L[i]
            if line + len(text) > limit:
                elem.br()
                line = 2
                elem.span(cls="servicedef-indent", text="")
            if i != len(L) - 1:
                if L[i + 1][-1] != "]":
                    text += "."

            elem.span(cls="servicedef-%s" % "basename" if i == 0
                                                       else "property",
                      text=text)
            line += len(text)

    def makerow(self, schema, name):
        if isinstance(schema, reschema.jsonschema.Merge):
            return self.makerow(schema.refschema, schema.refschema.fullname())

        tds = self.row(["", "", "", ""])

        logger.debug("Row: %s - %s " % (schema.fullname(), name))
        # To avoid very long nested structures from taking up too much
        # room in the table, force line breaks after a set number of
        # characters.

        self.setname(tds[0], name)

        if isinstance(schema, reschema.jsonschema.Ref):
            schema = RefSchemaProxy(schema, self.options)
            tds[1].a(cls="servicedef-type", href=schema.href, text="<" + schema.name + ">")
        else:
            tds[1].span(cls="servicedef-type", text="<" + schema.typestr + ">")

        tds[2].text = schema.description

        desctd = tds[3]
        parts = []

        if schema.readOnly:
            parts.append("Read-only")

        if (isinstance(schema, reschema.jsonschema.Object) and
             schema.required is not None and
             len(schema.required) > 0):
            parts.append("Required properties: [%s]" %
                         ', '.join(schema.required))

        if ((schema.parent is not None) and
             (isinstance(schema.parent, reschema.jsonschema.Object)) and
             ((schema.parent.required is None) or
              (schema.name not in schema.parent.required)) and
             (not (re.match("anyOf|allOf|oneOf|not", schema.name)))
             ):
            parts.append("Optional")

        if (isinstance(schema, reschema.jsonschema.Number) or
             isinstance(schema, reschema.jsonschema.Integer)):
            minimum = None
            if schema.minimum is not None:
                minimum = str(schema.minimum)
                if schema.exclusiveMinimum:
                    minimum = "(%s)" % str(minimum)

            maximum = None
            if schema.maximum is not None:
                maximum = str(schema.maximum)
                if schema.exclusiveMaximum:
                    maximum = "(%s)" % str(maximum)

            if (minimum is not None) and (maximum is not None):
                parts.append("Range: %s to %s" % (minimum, maximum))
            elif (minimum is not None):
                parts.append("Minimum %s" % (minimum))
            elif (maximum is not None):
                parts.append("Maximum %s" % (maximum))

        if isinstance(schema, reschema.jsonschema.Array):
            if schema.minItems is not None and \
                   schema.maxItems is not None:
                parts.append("%s-%s items" % (schema.minItems,
                                              schema.maxItems))
            elif schema.minItems is not None:
                parts.append("Minimum: %s items" % (schema.minItems))
            elif schema.maxItems is not None:
                parts.append("Maximum: %s items" % (schema.maxItems))

        if isinstance(schema, reschema.jsonschema.Timestamp):
            parts.append("Seconds since January 1, 1970")

        if hasattr(schema, 'default') and schema.default is not None:
            parts.append("Default is %s" % schema.default)

        if hasattr(schema, 'enum') and schema.enum is not None:
            parts.append("Values: " + ', '.join([str(x) for x in schema.enum]))

        if hasattr(schema, 'pattern') and schema.pattern is not None:
            parts.append("Pattern: '" + schema.pattern + "'")

        if hasattr(schema, 'notes') and schema.notes is not None:
            parts.append(schema.notes)

        desctd.settext('; '.join(parts))


class ParamTable(PropTable):
    def __init__(self, parameters):
        PropTable.__init__(self, parameters)

    def process(self, parameters):
        for p in parameters:
            self.makerow(parameters[p], p)


class SchemaTable(PropTable):
    def __init__(self, schema, options):
        PropTable.__init__(self, schema, options)

    def process(self, schema):
        self.makerow(schema, schema.fullname())

        if isinstance(schema, reschema.jsonschema.Merge):
            schema = schema.refschema

        for child in schema.children:
            if re.match("anyOf|allOf|oneOf|not", child.name):
                continue
            self.process(child)

        if isinstance(schema, reschema.jsonschema.Object):
            if schema.additional_properties is True:
                tds = self.row(["", "", "", ""])
                self.setname(tds[0], schema.fullname() + ".<prop>")
                tds[1].span(cls="servicedef-type").text = "<value>"
                tds[2].text = ("Additional properties may have "
                               "any property name and value")

        for child in schema.children:
            if not re.match("anyOf|allOf|oneOf|not", child.name):
                continue
            self.process(child)

if __name__ == '__main__':
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option('-f', '--file', dest='filename',
                      help='source file', action="store")
    parser.add_option('-o', '--output', dest='output',
                      help='HTML output file')
    parser.add_option('-p', '--pointer', dest='pointer',
                      help='JSON pointer to element within source to parse')
    parser.add_option('-a', '--additional', dest='additional', action="append",
                      help='JSON pointer to element within source to parse')

    (options, args) = parser.parse_args()

    htmldoc = HTMLDoc(options.filename)
    s2h = SchemaToHtml(basepath="/api", document=htmldoc)
    s2h.read(options.filename, options.pointer, options.additional)
    htmldoc.header.span(cls="headerleft").text = s2h.schema.name
    s2h.process()
    htmldoc.write(options.output)
