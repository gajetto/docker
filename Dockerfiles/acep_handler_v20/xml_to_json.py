import json
from lxml import etree

class XmltoJson(object):

    def __init__(self, fname):
        self.tree = etree.parse(fname)
        
    def get_json_object(self):
        xml_dict = self._todict(self.tree.getroot())
        js_obj = json.dumps(xml_dict)
        return js_obj

    def _todict(self, node):
        res = dict()
        res[node.tag] = list()
        self._scan_xml_recurse(node, res[node.tag])
        reply = dict()
        reply[node.tag] = {'value':res[node.tag],'attributes':dict(node.attrib),'tail':node.tail}
        return reply

    def _scan_xml_recurse(self, node, res):
        rep = dict()
        if len(node):
            for i in list(node):
                rep[node.tag] = list()
                self._scan_xml_recurse(i, rep[node.tag])
                if len(i):
                    value = {'value':rep[node.tag], 'attributes':dict(i.attrib), 'tail':i.tail}
                    res.append({i.tag:value})
                else:
                    res.append(rep[node.tag][0])
        else:
            value = dict()
            value.update({'value':node.text, 'attributes':dict(node.attrib), 'tail':node.tail})
            res.append({node.tag:value})
		
if __name__ == '__main__' :                            
    a = XmltoJson(r'test.xml')
    b = a.get_json_object()
    print b
