# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/reschema/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import re
import sys
import copy
import json
import yaml
import markdown
from collections import OrderedDict
import xml.dom.minidom, xml.etree.ElementTree as ET

import jsonpointer

from reschema.html import HTMLElement, HTMLTable, Document as HTMLDoc, TabBar
from reschema.jsonschema import Schema
from reschema.util import a_or_an, str_to_id as html_str_to_id
import reschema.yaml_omap


class Options(object):
    def __init__(self, printable=False, json=True, xml=True):
        self.printable = printable
        self.json = json
        self.xml = xml


class RestSchemaToHtml(object):
    def __init__(self, restschema, container, menu=None, options=None):
        self.restschema = restschema
        self.container = container
        self.menu = menu
        self.options = (options or Options())

    def process(self):

        resources_div = self.container.div(id='resources')
        self.menu.add_item("Resources", href=resources_div)
        resource_menu = self.menu.add_submenu()
        for resource in self.restschema.resources.values():
            ResourceToHtml(resource, self.container, resource_menu,
                           self.restschema.servicePath, self.options).process()

        types_div = self.container.div(id='types')
        self.menu.add_item("Types", href=types_div)
        type_menu = self.menu.add_submenu()
        for type_ in self.restschema.types.values():
            ResourceToHtml(type_, self.container, type_menu,
                           self.restschema.servicePath, self.options).process(is_type=True)


class ResourceToHtml(object):
    def __init__(self, schema, container, menu=None, basepath="", options=None):
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

        if re.match(".*\.json", filename):
            input = json.load(f, object_pairs_hook=OrderedDict)
        elif re.match(".*\.yml", filename):
            input = yaml.load(f)
        else:
            raise ValueError("Unrecognized file extension, use '*.json' or '*.yml': %s" % filename)

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
        menu = self.menu
        schema = self.schema
        baseid = ('type-' if is_type else 'resource-') + html_str_to_id(schema.fullid())

        div = self.container.div(id=baseid)
        menu.add_item(schema.name, href=div)

        div.h2().text = ('Type: ' if is_type else 'Resource: ') + schema.name
        if schema.description != '':
            div.p().text = schema.description

        if (not is_type):
            div.pre().text = "https://{device}" + self.basepath + str(schema.links['self'].path)
        
        self.schema_table(schema, div, baseid)

        if (not is_type):
            methodsmenu = menu.add_submenu()
            div.h3(id="methods").text = "Methods"
            self.process_methods(div, baseid, methodsmenu)

    def schema_table(self, schema, container,  baseid):
        tabbar = TabBar(container, baseid+'-tabbar', printable=self.options.printable)
        if self.options.json:
            tabbar.add_tab("JSON", baseid+'-json', SchemaSummaryJson(schema))
        if self.options.xml:
            tabbar.add_tab("XML", baseid+'-xml', SchemaSummaryXML(schema))
        #tabbar.add_tab("JSON Schema", "jsonschema", HTMLElement("pre", text=json.dumps(self.schema_raw, indent=2)))
        tabbar.finish()
        container.append(SchemaTable(self.schema))
        
    def process_methods(self, container, containerid, submenu):
        schema = self.schema
        for name, link in schema.links.iteritems():
            if name == 'self':
                continue

            baseid = containerid + '-method-%s' % name
            div = container.div(id=baseid, cls="method-body")
            submenu.add_item(name, href=div)
            div.h4().text = link.schema.fullname() + ": " + link.name
            div.p().text = link.description

            path = ("https://{device}" + self.basepath + str(link.path))
            
            httpmethod = link.method
            if httpmethod == "GET":
                # Handle link.request as parameters
                if link.request is not None:
                    props = link.request.props
                    params = ["%s={%s}" % (param, props[param].typestr)
                              for param in props.keys()]
                    if len(params) != 0:
                        path += "?" + "&".join(params)

            if httpmethod is None:
                div.pre().text = path
            else:
                div.pre().text = httpmethod + " " + path

            div.span(cls="h5").text = "Authorization"
            if link.authorization == "required":
                div.p().text = "This request requires authorization."
            elif link.authorization == "optional":
                div.p().text = "This request may be made with or without authorization."
            else:
                div.p().text = "This request does not require authorization."

            #if link.headers:
                #div.span(cls="h5").text = "HTTP Headers"
                #table = div.table(cls="paramtable")
                #div.append(ParamTable(link.headers))
                #table.row(["Name", "Type", "Description"], header=True)
                #for name in link.parameters:
                #    p = link.parameters[name]
                #    table.row([name, p.typestr, p.description])

            if httpmethod != "GET":
                div.span(cls="h5").text = "Request Body"
                if link.request is not None and httpmethod != "GET":
                    if type(link.request) is reschema.jsonschema.Ref:
                        p = div.p()
                        p.settext("Provide ",
                                  a_or_an(link.request.refschema.name),
                                  " ",
                                  p.a(cls="jsonschema-type",
                                      href="#type-%s" % html_str_to_id(link.request.refschema.fullid()),
                                      text=link.request.refschema.name),
                                  " data object." )
                    elif type(link.request) is reschema.jsonschema.Data:
                        p = div.p()
                        if link.request.description is None:
                            description = "data"
                        else:
                            description = "the " + link.request.description
                            p.settext("Provide a request body containing %s with content type " % description,
                                      p.span(cls="content-attribute", text=link.request.content_type),
                                      ".")
                    else:
                        p = div.p().text = "Provide a request body with the following structure:"
                        self.schema_table(link.request, div, baseid + '-request')

                elif httpmethod in ("PUT", "POST"):
                    div.p().text = "Do not provide a request body."

            div.span(cls="h5").text = "Response Body"
            schema = link.response
            if schema:
                if type(schema) is reschema.jsonschema.Ref:
                    p = div.p()
                    p.settext("Returns ",
                              a_or_an(schema.refschema.name),
                              " ",
                              p.a(cls="jsonschema-type",
                                  href="#type-%s" % html_str_to_id(schema.refschema.fullid()),
                                  text=schema.refschema.name),
                              " data object.")
                elif type(schema) is reschema.jsonschema.Data:
                    p = div.p()
                    p.settext("On success, the server returns a response body containing data with content type ",
                              p.span(cls="content-attribute", text=schema.content_type),
                              ".")
                else:
                    p = div.p().text = "On success, the server returns a response body with the following structure:"
                    self.schema_table(link.response, div, baseid + '-response')

            else:
                div.p().text = "On success, the server does not provide any body in the responses."

            # XXXCJ - this code may still be needed, but not yet functional
            if None and link.examples is not None:
                div.span(cls="h5").text = "Examples"
                for ex in link.examples:
                    text = ex['text']
                    html = markdown.markdown(text)
                    md_html = ET.XML("<div>" + html + "</div>")
                    div.append(md_html)

        return None


class SchemaSummaryJson(HTMLElement):
    def __init__(self, schema):
        HTMLElement.__init__(self, "pre", cls="restschema")
        self.process(self, schema, 0)

        if isinstance(schema, reschema.jsonschema.Ref):
            example = schema.refschema.example
        else:
            example = schema.example
        
        if example is not None:
            self.span().text = "\n\nExample:\n%s\n" % json.dumps(example, indent=2)

    def process(self, parent, schema, indent=0, follow_refs=False):
        if isinstance(schema, reschema.jsonschema.Object):
            self.process_object(parent, schema, indent)

        elif isinstance(schema, reschema.jsonschema.Array):
            self.process_array(parent, schema, indent)

        elif isinstance(schema, reschema.jsonschema.Ref):
            if follow_refs:
                self.process(parent, schema.refschema, indent)
            else:
                href = "#type-%s" % html_str_to_id(schema.refschema.fullid())
                parent.a(cls="restschema-type", href=href, text=schema.refschema.name)
        else:
            parent.span(cls="restschema-type").text = schema.typestr
            
    def process_object(self, parent, obj, indent):
        parent.span().text = "{\n"
        last = None
        for k in obj.props:
            if last is not None:
                last.text = ",\n"
            parent.span(cls="restschema-property").text = ('%*.*s"%s": ' %
                                                           (indent+2, indent+2, "", k))
            s = parent.span()
            self.process(s, obj.props[k], indent+2)
            last = parent.span()
            last.text = '\n'
            
        if obj.additionalProps:
            if last is not None:
                last.text = ",\n"
            parent.span(cls="restschema-type").text = '%*.*s%s' % (indent+2, indent+2, "",
                                                                   obj.additionalProps.name)
            parent.pan().text = ": "
            s = parent.span()
            self.process(s, obj.additionalProps, indent+2)
            last = parent.span()
            last.text = '\n'

        parent.span().text = "%*.*s}" % (indent, indent, "")
    
    def process_array(self, parent, array, indent):
        #print "Array.schema_summary: type(self.children[0]) is %s" % type(self.children[0])
        item = array.children[0]
        if isinstance(item, reschema.jsonschema.Ref):
            s = parent.span()
            s.settext( "[ ", s.a(cls="restschema-type",
                                 href="#type-%s" % html_str_to_id(item.refschema.fullid()),
                                 text=item.refschema.name),
                       " ]")

        else:
            parent.span().text = "[\n%*.*s" % (indent+2, indent+2, "")
            self.process(parent.span(), item, indent+2)
            parent.span().text = "\n%*.*s]" % (indent, indent, "")


class SchemaSummaryXML(HTMLElement):
    def __init__(self, schema):
        HTMLElement.__init__(self, "pre", cls="restschema")
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
                

    def process(self, parent, schema, indent=0, follow_refs=False, name=None, json=None, key=None):
        if schema.xmlSchema is not None:
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
                        parent.span(cls="xmlschema-attribute").text = ('%s%s' % (" " if first else attr_indent, attr))
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

        if name is None:
            if schema.id is None:
                name = schema.name
            else:
                name = schema.id
        if name == "[]":
            name = "items"
        if type(schema) is reschema.jsonschema.Object:
            self.process_object(parent, schema, indent, name, key=key)

        elif isinstance(schema, reschema.jsonschema.Array):
            if name is None:
                if schema.id is None:
                    name = schema.name
                else:
                    name = schema.id
            self.process_array(parent, schema, indent, name, key=key)

        elif isinstance(schema, reschema.jsonschema.Ref):
            if follow_refs:
                self.process(parent, schema.refschema, indent, name, key=key)
            else:
                dtype = schema.refschema.name
                if not name:
                    name = dtype
                if key:
                    parent.span(cls="xmlschema-element").text = "%*s<%s key=string>" % (indent, "", name)
                else:
                    parent.span(cls="xmlschema-element").text = "%*s<%s>" % (indent, "", name)

                parent.a(cls="xmlschema-type", href="#type-%s" % html_str_to_id(schema.refschema.fullid()),
                         text="%s" % dtype)
                parent.span(cls="xmlschema-element").text = "</%s>\n" % (name)

        else:
            if key:
                parent.span(cls="xmlschema-element").text = "%*s<%s " % (indent, "", name)
                parent.span(cls="xmlschema-attribute").text = key
                parent.span().text = "="
                parent.span(cls="xmlschema-type").text = "string"
                parent.span().text = ">"
            else:
                parent.span(cls="xmlschema-element").text = "%*s<%s>" % (indent, "", name)
            parent.span(cls="xmlschema-type").text = "%s" % schema.typestr
            parent.span(cls="xmlschema-element").text = "</%s>\n" % (name)
            
    def process_object(self, parent, obj, indent, name, key=None):
        parent.span().text = "%*s<" % (indent, "")
        parent.span(cls="xmlschema-element").text =  name
        subelems = obj.additionalProps
        first = True
        attr_indent = "\n%*s" % (indent + 2 + len(name), "")
        
        for k in obj.props:
            prop = obj.props[k]
            if not prop.isSimple():
                subelems = True
                continue
            parent.span(cls="xmlschema-attribute").text = ('%s%s' % (" " if first else attr_indent, k))
            parent.span().text = '='
            parent.span(cls="xmlschema-type").text = prop.typestr
            first = False

        if subelems:
            parent.span().text = ">\n" 
        else:
            parent.span().text = "/>\n"
        
        for k in obj.props:
            prop = obj.props[k]
            if prop.isSimple():
                continue
            s = parent.span()
            self.process(s, prop, indent+2, name=k)
            
        if obj.additionalProps:
            s = parent.span()

            subobj = copy.copy(obj.additionalProps)
            keyname = subobj.xmlKeyName or 'key'
            try:
                subobj.props = OrderedDict()
                json = {'id':keyname, 'type':'string', 'description':'property name'}
                subobj.props[keyname] = subobj.schema.parse(json, keyname, subobj)
                for k in obj.additionalProps.props:
                    subobj.props[k] = obj.additionalProps.props[k]
            except:
                pass
            self.process(s, subobj, indent+2, name=subobj.id, key=keyname)
            
        if subelems:
            parent.span().text = "%*s</" % (indent, "")
            parent.span(cls="xmlschema-element").text = name
            parent.span().text = ">\n"
    
    def process_array(self, parent, array, indent, name, key):
        parent.span().text = "%*s<" % (indent, "")
        parent.span(cls="xmlschema-element").text = name
        parent.span().text = ">\n"
        self.process(parent.span(), array.children[0], indent+2, name=array.children[0].id)
        parent.span().text = "%*s</" % (indent, "")
        parent.span(cls="xmlschema-element").text = name
        parent.span().text = ">\n"


class PropTable(HTMLTable):
    def __init__(self, data):
        HTMLTable.__init__(self, cls="paramtable")

        self.define_columns(["paramtable-propname",
                             "paramtable-proptype",
                             "paramtable-description",
                             "paramtable-notes"])
        self.row(["Property Name", "Type", "Description", "Notes"], header=True)

        self.process(data)

    def process(self, data):
        pass

    def makerow(self, schema, name):
        tds = self.row(["", "", "", ""])

        # To avoid very long nested structures from taking up too much
        # room in the table, force line breaks after a set number of
        # characters.
        limit = 40
        L = re.split("[.[]", name)
        line = 0
        for i in range(len(L)):
            if L[i][-1] == "]":
                text = "[" + L[i]
            else:
                text = L[i]
            if line + len(text) > limit:
                tds[0].br()
                line = 2
                tds[0].span(cls="restschema-indent", text="")
            if i != len(L) - 1:
                if L[i+1][-1] != "]":
                    text += "."
                
            tds[0].span(cls="restschema-%s" % "basename" if i == 0 else "property",
                        text=text)
            line += len(text)
        
        if isinstance(schema, reschema.jsonschema.Ref):
            dtype = schema.typestr
            tds[1].a(cls="restschema-type",
                     href="#type-%s" % html_str_to_id(schema.refschema.fullid()),
                     text="<" + schema.refschema.name + ">")
        else:
            tds[1].span(cls="restschema-type", text="<" + schema.typestr + ">")

        tds[2].text = schema.description

        desctd = tds[3]
        parts = []

        if schema.required is False:
            parts.append("Optional")
            
        if isinstance(schema, reschema.jsonschema.Number):
            minimum = None
            if schema.minimum is not None:
                minimum = str(schema.minimum)
            elif schema.exclusiveMinimum is not None:
                minimum = "(%s)" % str(schema.exclusiveMinimum)

            maximum = None
            if schema.maximum is not None:
                maximum = str(schema.maximum)
            elif schema.exclusiveMaximum is not None:
                maximum = "(%s)" % str(schema.exclusiveMaximum)

            if (minimum is not None) and (maximum is not None):
                parts.append("Range: %s to %s" % (minimum, maximum))
            elif (minimum is not None):
                parts.append("Min %s"  % (minimum))
            elif (maximum is not None):
                parts.append("Max %s" % (maximum))

        if isinstance(schema, reschema.jsonschema.Array):
            if schema.minItems is not None:
                parts.append("Minimum: %s" % (schema.minItems))

            if schema.maxItems is not None:
                parts.append("Maximum: %s" % (schema.maxItems))
            
        if isinstance(schema, reschema.jsonschema.Timestamp):
            parts.append("Seconds since January 1, 1970")
            
        if hasattr(schema, 'default') and schema.default is not None:
            parts.append("Default is %s" % schema.default)

        if hasattr(schema, 'enum') and schema.enum is not None:
            parts.append("Values: " + ', '.join(schema.enum))

        if hasattr(schema, 'pattern') and schema.pattern is not None:
            parts.append("Pattern: '" + schema.pattern + "'")

        if schema.notes != "":
            parts.append(schema.notes)

        desctd.settext('; '.join(parts))


class ParamTable(PropTable):
    def __init__(self, parameters):
        PropTable.__init__(self, parameters)

    def process(self, parameters):
        for p in parameters:
            self.makerow(parameters[p], p)

                         
class SchemaTable(PropTable):
    def __init__(self, schema):
        PropTable.__init__(self, schema)

    def process(self, schema):
        self.makerow(schema, schema.fullname())

        for child in schema.children:
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
