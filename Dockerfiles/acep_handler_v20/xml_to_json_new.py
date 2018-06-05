from lxml import objectify
try: 
    import simplejson as json
except ImportError: 
    import json

# This follows google's rules for conversion of XML to JSON

def iter_nodes(node, parent_dict):
    node_dict = dict()
    try:
        node_dict.update(node.attrib)
    except AttributeError:
        pass

    for i in node.iterchildren():
        child_dict = dict()
        new_dict = dict()
        new_dict = iter_nodes(i, child_dict)
        new_list = list()
        if i.tag in node_dict:
            try:
                node_dict[i.tag].append(new_dict[i.tag])
            except:
                new_list.append(node_dict[i.tag])
                node_dict[i.tag] = new_list
                node_dict[i.tag].append(new_dict[i.tag])
        else:
                node_dict.update(new_dict)

    tag_list = node.tag.split(':')
    namespace = '$'.join(tag_list)
    if len(node_dict) == 0: 
        if node.text != None:
             parent_dict.update({node.tag: node.text})
    else:
        if node.text != None:
            node_dict['$text'] = node.text
        parent_dict[namespace] = node_dict

    return parent_dict

def parse_xml(xmlFile):
    with open(xmlFile) as f:
         xml = f.read()

    root = objectify.fromstring(xml)
	
    empty_dict = dict()
    parsed_dict = iter_nodes(root, empty_dict)

    return json.dumps(parsed_dict)

print parse_xml('report457437806.xml')
