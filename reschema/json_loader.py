import json
import inspect
from collections import OrderedDict

from yaml.error import Mark
from json.scanner import py_make_scanner
from json.decoder import JSONDecoder


def linecol(doc, pos):
    # assume zero-indexed
    lineno = doc.count('\n', 0, pos)
    if lineno == 0:
        colno = pos - 1
    else:
        colno = pos - doc.rindex('\n', 0, pos) - 1
    return lineno, colno


class Decoder(JSONDecoder):
    def __init__(self, *args, **kwargs):
        super(Decoder, self).__init__(*args, **kwargs)
        self.scan_once = py_make_scanner(self)


def obj_hook(obj):
    """Hook to create OrderedDicts with start/end marks."""
    # this approach requires the json python scanner
    # the c-module doesn't lend itself to frame inspection
    # which means we don't get the line-by-line info needed
    # to create good marks

    frame = inspect.currentframe().f_back
    s = frame.f_locals['s']
    start = frame.f_locals['s_and_end'][1] - 1
    end = frame.f_locals['end']

    o = OrderedDict(obj)
    line, col = linecol(s, start)
    o.start_mark = Mark('JSONObject', start, line, col, s, start)
    line, col = linecol(s, end)
    o.end_mark = Mark('JSONObject', end, line, col, s, end)

    return o


def marked_load(stream):
    return json.load(stream, cls=Decoder, object_hook=obj_hook, object_pairs_hook=obj_hook)


def clean_load(stream):
    return json.load(stream, object_pairs_hook=OrderedDict)
