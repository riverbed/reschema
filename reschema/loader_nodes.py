# Copyright (c) 2019 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from yaml.error import Mark

def obj_key_node(obj, prop):
    idx = list(obj.keys()).index(prop)
    return list(obj.keys())[idx]


def add_marks_to_node(obj, start_mark=None, end_mark=None):
    if start_mark is not None:
        obj.start_mark = start_mark
    else:
        obj.start_mark = Mark(None, None, 0, 0, None, None)
    if end_mark is not None:
        obj.end_mark = end_mark
    else:
        obj.end_mark = obj.start_mark


def create_str_node_class(cls):
    class node_class(cls):
        def __init__(self, x, start_mark=None, end_mark=None):
            cls.__init__(self)
            add_marks_to_node(self, start_mark, end_mark)

        def __new__(self, x=None, start_mark=None, end_mark=None):
            return cls.__new__(self, x)
    node_class.__name__ = '%s_node' % cls.__name__
    return node_class


def create_mutable_node_class(cls):
    class node_class(cls):
        def __init__(self, x, start_mark=None, end_mark=None):
            cls.__init__(self, x)
            add_marks_to_node(self, start_mark, end_mark)

        def __new__(self, x=None, start_mark=None, end_mark=None):
            return cls.__new__(self, x)
    node_class.__name__ = '%s_node' % cls.__name__
    return node_class


dict_node = create_mutable_node_class(dict)
list_node = create_mutable_node_class(list)
str_node = create_str_node_class(str)
