import os
from StringIO import StringIO
from uuid import uuid4
from lxml import etree
import acep_xml_extractor as AE
import acep_report_parser as AP
from settings import TMP

class PrlParser(object):

    def __init__(self, fname, product_name):
        self.ignored_tags = ['HostStatistic', 'HostInfo']
        self.root_dir = os.path.split(fname)[0]
        self.tree = etree.parse(fname).getroot()
        self.product_name = product_name
        self.version = None
        self.build_number = None
        self.guid = None
        self.report_type = None

    def get_xml_dict(self):
        xml_dict = self._make_header(self.tree)

        return xml_dict

    def get_xml_dict_v2(self, hi_file, hs_file):
        res = {'ParallelsProblemReport': {}}
        self._scan_xml_recurse(self.tree, res['ParallelsProblemReport'])
        self._process_hostinfo(hi_file, res['ParallelsProblemReport'])
        hs_node = etree.parse(hs_file)
        self._process_hoststatistics(hs_node.getroot(), res['ParallelsProblemReport'], True)
        res['ParallelsProblemReport'].update(self._get_installed_software())

        return res

    def _make_header(self, node):
        res = dict()
        res['ParallelsProblemReport'] = dict()
        self._scan_xml_recurse(node, res['ParallelsProblemReport'])
        self._append_hostinfo(node, res['ParallelsProblemReport'])
        self._append_hoststatistics(node, res['ParallelsProblemReport'])        

        return res

    def _scan_xml_recurse(self, node, res):
        rep = dict()
        if len(node):
            for i in list(node):
                if i.tag in self.ignored_tags:
                    res.update({i.tag: dict()})
                    continue
                rep[i.tag] = dict()
                self._scan_xml_recurse(i, rep[i.tag])
                if len(i):
                    value = rep[i.tag]
                    res.update({i.tag: value})
                else:
                    res.update({i.tag: i.text})
        else:
            res.update({node.tag: node.text})

    def _append_hostinfo(self, node, res):
        hostinfo = node.find('HostInfo')
        if hostinfo is None: 
            return
        hi_value = StringIO(hostinfo.text)
        self._process_hostinfo(node, res)

    def _process_hostinfo(self, hi_value, res):
        hi_parser = HostInfoParser(hi_value)
        res.update({'HostInfo': hi_parser.get_hostinfo_dict()})

    def _append_hoststatistics(self, node, res):
        hoststat = node.find('HostStatistic')
        if hoststat is None: 
            return
        self._process_hoststatistics(node, res)

    def _get_installed_software(self):
        installed_software = {'installed_software': []}
        installed_software_file = os.path.join(self.root_dir, 'InstalledSoftware.txt')
        if os.path.exists(installed_software_file):
            installed = set([i.strip() for i in open(installed_software_file, 'r')])
            installed_software['installed_software'].extend(sorted(installed))

        return installed_software

    def _process_hoststatistics(self, node, res, new_extract=False):
        extract_dir = os.path.join(TMP, str(uuid4()))
        if 'ati' in self.product_name.lower() or 'add' in self.product_name.lower() or 'asd' in self.product_name.lower():
            try:
                extract = AE.AtihAcepXmlExtractor(node, extract_dir, new_extract)
                parser = AP.AtihReportParser(extract_dir)
                self.guid = parser.get_guid()
                self.build_number = parser.get_build_number()
                res.update({'HostStatistic': parser.get_xml_dict()})
            except Exception, e:
                raise(e)
            finally:
                if 'extract' in locals():
                    extract.remove_extract_dir()
        elif 'abr' in self.product_name.lower():
            try:
                extract = AE.AbrAcepXmlExtractor(node, extract_dir)
                parser = AP.AbrReportParser(extract_dir)
                self.version = parser.get_version()
                self.build_number = parser.get_build_number()
                self.guid = parser.get_guid()
                self.report_type = parser.get_report_type()
                res.update({'HostStatistic': parser.get_xml_dict()})
            except Exception, e:
                raise(e)
            finally:
                if 'extract' in locals():
                    extract.remove_extract_dir()
        elif 'vmprotect' in self.product_name.lower():
            try:
                extract = AE.VMPAcepXmlExtractor(node, extract_dir)
                parser = AP.VmpReportParser(extract_dir)
                self.version = parser.get_version()
                self.build_number = parser.get_build_number()
                self.guid = parser.get_guid()
                res.update({'HostStatistic': parser.get_xml_dict()})
            except Exception, e:
                raise(e)
            finally:
                if 'extract' in locals():
                    extract.remove_extract_dir()
        else:
            raise Exception('Unknown report type - {0} !!'.format(self.product_name))

class HostInfoParser(object):

    def __init__(self, fname):
        parser = etree.XMLParser(recover=True)
        self.tree = etree.parse(fname, parser).getroot()

    def get_hostinfo_dict(self):
        xml_dict = dict()
        xml_dict.update(self.get_header())
        xml_dict.update(self._get_xml_dictonary('MemorySettings'))
        xml_dict.update(self._get_network_info())
        xml_dict.update(self._get_xml_list('FloppyDisks/FloppyDisk', 'FloppyDisks'))
        xml_dict.update(self._get_xml_list('CdROMs/CdROM', 'CdROMs'))
        xml_dict.update(self._get_hdd_info())
        xml_dict.update(self._get_xml_list('SerialPorts/SerialPort', 'SerialPorts'))
        xml_dict.update(self._get_xml_list('ParallelPorts/ParallelPort', 'ParallelPorts'))
        xml_dict.update(self._get_sound_devices_info())
        xml_dict.update(self._get_xml_list('UsbDevices/UsbDevice', 'UsbDevices'))
        xml_dict.update(self._get_xml_list('Printers/Printer', 'Printers'))
        xml_dict.update(self._get_xml_dictonary('Cpu'))
        xml_dict.update(self._get_xml_dictonary('OsVersion'))

        return {self.tree.tag: xml_dict}

    def _get_xml_dictonary(self, tag_name, dict_name=None):
        if dict_name is None:
            dict_name = tag_name
        dict_out = dict()
        for i in self.tree.find(tag_name).getchildren():
            dict_out.update({i.tag: i.text})

        return {dict_name: dict_out}

    def _get_xml_list(self, tag_path, list_name):
        list_out = list()
        for i in self.tree.iterfind(tag_path):
            dict_item = dict((j.tag, j.text) for j in i.getchildren())
            list_out.append(dict_item)

        return {list_name: list_out}
    
    def _get_sound_devices_info(self):
        sound_out = dict()
        sound_out.update(self._get_xml_list('SoundDevices/OutputDevices/OutputDevice', 'OutputDevices'))
        sound_out.update(self._get_xml_list('SoundDevices/MixerDevices/MixerDevice', 'MixerDevices'))

        return {'SoundDevices': sound_out}

    def _get_network_info(self):
        network_out = dict()
        value = self.tree.find('NetworkSettings/MaxVmNetAdapters')
        network_out.update({value.tag: value.text})
        network_out.update(self._get_xml_dictonary('NetworkSettings/GlobalNetwork', 'GlobalNetwork'))

        return {'NetworkSettings': network_out}

    def _get_hdd_info(self):
        hdd_out = dict()
        value = self.tree.find('HardDisks/BootCamp')
        hdd_out.update({value.tag: value.text})
        hdd_list = list()
        for i in self.tree.iterfind('HardDisks/HardDisk'):
            hdd_item = dict()
            partition_list = list()
            for j in i.getchildren():
                if j.tag == 'Partition':
                    partition_item = dict((k.tag, k.text) for k in j.getchildren())
                    partition_list.append(partition_item)
                else:
                    hdd_item.update({j.tag: j.text})
            hdd_item.update({'Partitions': partition_list})
            hdd_list.append(hdd_item)
        hdd_out.update({'HardDisk': hdd_list})

        return {'HardDisks': hdd_out}

    def get_header(self):
        head_fields = ['SoundDefaultEnabled', 'UsbSupported', 'VtdSupported', 'HostNotebookFlag']
        head_item = dict()
        for i in head_fields:
            value = self.tree.find('HardDisks/BootCamp')
            head_item.update({value.tag: value.text})

        return head_item

if __name__ == '__main__':
    p = PrlParser(r'144342431_02e63295cf06b199b1a1c73f58ee0868.xml', 'ADD11')
    print p.get_xml_dict()
    print p.guid

