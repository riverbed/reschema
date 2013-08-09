import yaml
from collections import OrderedDict

### Construct OrderedDict
### Inspired by http://stackoverflow.com/questions/5121931/in-python-how-can-you-load-yaml-mappings-as-ordereddicts

def construct_ordereddict(load, node):
    mapping = OrderedDict()
    yield mapping
    if not isinstance(node, yaml.MappingNode):
        raise yaml.constructor.ConstructorError(
            "while constructing an ordered map",
            node.start_mark,
            "expected a mapping node, but found %s" % node.id, node.start_mark
        )
    for key_node, value_node in node.value:
        key = load.construct_object(key_node)
        try:
            hash(key)
        except TypeError, exc:
            raise yaml.constructor.ConstructorError('while constructing a mapping',
                                                    node.start_mark, 'found unacceptable key (%s)' % exc, key_node.start_mark)
        value = load.construct_object(value_node)
        mapping[key] = value

yaml.add_constructor(u'tag:yaml.org,2002:map', construct_ordereddict)

