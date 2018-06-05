import sys
import os
import base64
import string
import random
import zlib
from StringIO import StringIO
from lxml import etree
from zipfile import ZipFile
from shutil import rmtree

class AcepXmlExtractor(object):

    def __init__(self, xml_struct, exctract_dir='.', new_extract=False):
        if 'lxml.etree' in str(type(xml_struct)):
            self.xml_data_full = xml_struct
        else:
            self.xml_data_full = etree.parse(xml_struct)
        self.exctract_dir = exctract_dir
        if new_extract:
            self.process_internal_xml(self.xml_data_full)
        else:
            for i in self.xml_data_full.findall('HostStatistic'):
                self.handle_internal_xml(i)
    
    def handle_internal_xml(self, xml_cdata):
        pass

    def process_internal_xml(self, xml_cdata):
        pass

    def extract_reports(self, fname_xml, fbody_xml):
        fname = fname_xml.text
        fbody = StringIO(base64.b64decode(fbody_xml.text))
        self.extract_file(fname, fbody)

    def extract_file(self, fname, fbody):
        if not os.path.exists(self.exctract_dir):
            os.makedirs(self.exctract_dir)
        with ZipFile(fbody, 'r',) as report_zip:
            report_zip.extract(fname, self.exctract_dir)

    def id_generator(self, size=6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for x in range(size))

    def remove_extract_dir(self):
        if os.path.exists(self.exctract_dir):
            rmtree(self.exctract_dir)


class AbrAcepXmlExtractor(AcepXmlExtractor):

    def process_internal_xml(self, xml_cdata):
        raise Exception('Not needed in the AbrAcepXmlExtractor!!')

    def handle_internal_xml(self, xml_cdata):
        xml_reps = etree.fromstring(xml_cdata.text)
        for i in xml_reps.findall('*'):
            fname_xml, fbody_xml = i.getchildren()
            self.extract_reports(fname_xml, fbody_xml)


class AtihAcepXmlExtractor(AcepXmlExtractor):
    
    def handle_internal_xml(self, xml_cdata):
        xml_str = xml_cdata.text[3:].encode('utf-8')
        xml_reps = etree.fromstring(xml_str)
        self.process_internal_xml(xml_reps)

    def process_internal_xml(self, xml_reps):
        for i in xml_reps.findall('ItemList/*'):
            fname_xml, dirname_xml, fbody_xml = i.getchildren()
            self.extract_reports(fname_xml, fbody_xml)

    def extract_reports(self, fname_xml, fbody_xml):
        if not os.path.exists(self.exctract_dir):
            os.makedirs(self.exctract_dir)

        try:
            fname = fname_xml.text.decode('utf-8')
        except:
            fname = self.id_generator() + '.log'

        #print('fname:{0} '.format(fname))
        fname = os.path.join(self.exctract_dir, fname)
        fbody = base64.b64decode(fbody_xml.text)
        
        with open(fname, 'w') as fout:
            fout.write(fbody)


class VMPAcepXmlExtractor(AcepXmlExtractor):

    def process_internal_xml(self, xml_cdata):
        raise Exception('Not needed in the VMPAcepXmlExtractor')

    def handle_internal_xml(self, xml_cdata):
        if not os.path.exists(self.exctract_dir):
             os.makedirs(self.exctract_dir)
        fname = os.path.join(self.exctract_dir, 'report.xml')
        fbody = base64.b64decode(xml_cdata.text.encode('utf-8'))
        with open(fname, 'w') as report_out:
            report = zlib.decompress(fbody)
            report_out.write(report)


if __name__ == '__main__':
#    x = etree.parse('143636729_55f6c92b194b9234c62c923e6a0c23a5.xml')
#    a = AbrAcepXmlExtractor(x, 'out')
    a = AtihAcepXmlExtractor(r'C:\WorkDirectory\PyScripts\ACEP_WEB_SERVICE\111\data\HostStatistics.xml', 'out', True)
#    a = VMPAcepXmlExtractor('144342431_02e63295cf06b199b1a1c73f58ee0868.xml', 'out_2')
   
    print('Done.')
