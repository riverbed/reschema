import markdown

def parse_prop(obj, srcobj, prop, defaultValue=None, map=None, required=False):
    if prop in srcobj:
        val = srcobj[prop]
    elif required:
        raise ValueError("Missing required property '%s'" % prop)
    else:
        val = defaultValue
        
    if val and map:
        val = map[val]
        
    setattr(obj, prop, val)

def a_or_an(str):
    if str[0] in ('a', 'e', 'i', 'o'):
        return "an"
    else:
        return "a"
