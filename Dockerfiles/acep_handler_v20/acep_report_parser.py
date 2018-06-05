import os
from glob import glob
from lxml import etree
from lxml import objectify

class AbrReportParser(object):

    def __init__(self, reports_dir):
        self.ignored_tags = ['provider', 'XML_SERIALIZER', 'View', 'shared_ptr', 'raw_ptr',
                             'ptr_mark', 'ptr_value', 'checked_type', 'LoginCredentials', 'TargetIdentifier',
                             'optional_type', 'Account', 'UserName', 'Password', 'impl', 'Object',
                             'IncomingServerLogon', 'OutgoingServerLogon', 'item']
        self.array_types = ['list', 'vector', 'map', 'multimap']
        self.report_type = None
        self.tree_events = None
        self.reports_list = glob(os.path.join(reports_dir, '*.xml'))
        for i in self.reports_list:
            self.report_type = self._check_report_type(i)
            if self.report_type in ['AMS', 'MMS', 'MC']:
                self.tree = etree.parse(i)
                break
            else:
                continue
        if self.report_type == 'MC':
            self.tree_ext = self._get_product_xml(self.reports_list)
            self.tree_events = self._get_tree_events(self.reports_list)
        self.mp = MsiInfoParser(self.reports_list)
        self.custom_parser = XmlCustomParser()
        
    def get_xml_dict(self):
        xml_dict = self._todict(self.tree.getroot())
        msinfo_part = self.mp.get_xml_dict()
        if msinfo_part is not None:
            xml_dict.update({'msinfo': msinfo_part})
        if self.tree_events is not None:
            mc_events_part = self._todict(self.tree_events.getroot())
            xml_dict.update({'mc_events': mc_events_part})
        for rep in self.reports_list:
            try:
                custom_part = self.custom_parser.get_xml_dict(rep)
            except:
                custom_part = None
            if custom_part is not None:
                xml_dict.update(custom_part)

        return xml_dict

    def get_guid(self):
        if self.report_type == 'MC':
            return self._get_guid_mc()
        else:
            return self._get_guid_ams_mms()

    def get_version(self):
        if self.report_type == 'MC':
            return self._get_version_mc()
        else:
            return self._get_version_ams_mms()

    def get_build_number(self):
        if self.report_type == 'MC':
            return self._get_build_number_mc()
        else:
            return self._get_build_number_ams_mms()

    def get_report_type(self):
        return self.report_type

    def _get_product_xml(self, reports_list):
        for i in reports_list:
            xml_root = etree.parse(i).getroot()
            if xml_root.tag == 'ProductInfo':
                return xml_root

    def _get_tree_events(self, reports_list):
        xml_root = None
        for i in reports_list:
            report_type = self._check_report_type(i)
            if report_type == 'MC_EVENTS':
                xml_root = etree.parse(i)
                break

        return xml_root

    def _check_report_type(self, fname):
        tree = etree.parse(fname)
        rep_name = tree.getroot().get('name')
        if rep_name == 'AMS full report':
            return 'AMS'
        elif rep_name == 'MMS full report':
            return 'MMS'
        elif rep_name == 'MC full report':
            check_prop = tree.getroot().find('object/property')
            if check_prop is None:
                return 'MC'
            else:
                if check_prop.text == 'McFirstEventTime':
                    return 'MC_EVENTS'
                else:
                    return 'MC'
        else:
            return None

    def _todict(self, node):
        res = dict()
        node_name = node.get('name').replace('.', '_')
        res[node_name] = dict()
        self._scan_xml_recurse(node, res[node_name])
        return res

    def _scan_xml_recurse(self, node, res):
        rep = dict()
        if len(node):
            for i in list(node):
                new_name = i.get('name').replace('.', '_')
                if new_name in self.array_types:
                    rep[new_name] = list()
                else:
                    rep[new_name] = dict()
                self._scan_xml_recurse(i, rep[new_name])
                if len(i):
                    value = rep[new_name]
                    if new_name in self.ignored_tags:
                        if type(res) is list:
                            res.append(value)
                        else:
                            res.update(value)
                    else:
                        self._insert_xml_record(res, new_name, value)
                else:
                    if i.tag.lower() == 'property':
                        self._insert_xml_record(res, i.get('name').replace('.', '_'), i.text)
                    else:
                        self._insert_xml_record(res, i.get('name').replace('.', '_'), dict())
        else:
            if node.tag.lower() == 'property':
                self._insert_xml_record(res, node.get('name').replace('.', '_'), node.text)
            else:
                self._insert_xml_record(res, node.get('name').replace('.', '_'), dict())

    def _insert_xml_record(self, res, key, value):
        if type(res) is list:
            res.append({key: value})
        else:
            if res.has_key(key) and type(value) == dict:
                res.update(value)
            else:
                res.update({key: value})

    def _get_guid_ams_mms(self):
        guid_raw = self.tree.find("//property[@name='MachineID']")
        return guid_raw.text

    def _get_version_ams_mms(self):
        vers_raw = self.tree.find("//property[@name='Version']")
        vers = vers_raw.text.rsplit('.', 1)[0]
        return vers

    def _get_build_number_ams_mms(self):
        bn_raw = self.tree.find("//property[@name='Version']")
        bn = bn_raw.text.rsplit('.', 1)[1]
        return bn

    def _get_guid_mc(self):
        if self.tree_ext is None:
            return
        guid = self.tree_ext.find('Guid').text
        return guid

    def _get_version_mc(self):
        if self.tree_ext is None:
            return
        vers_raw = self.tree_ext.find('Build').text
        vers = vers_raw.rsplit('.', 1)[0]
        return vers

    def _get_build_number_mc(self):
        if self.tree_ext is None:
            return
        bn_raw = self.tree_ext.find('Build').text
        bn = bn_raw.rsplit('.', 1)[1]
        return bn


class AtihReportParser(object):

    def __init__(self, reports_dir):
        self.reports_dir = reports_dir
        self.custom_parser = XmlCustomParser()
        self.truieimg_reps = self._get_all_cep_reports()
        self.diskinfo_rep = os.path.join(self.reports_dir, 'DiskInfo.xml')
        self.productinfo_rep = os.path.join(self.reports_dir, 'ProductInfo.xml')
        self.archives_rep = os.path.join(self.reports_dir, 'archives.xml')
        self.machineinfo_rep = os.path.join(self.reports_dir, 'MachineInfo.xml')
        self.tib_flist = [os.path.join(self.reports_dir, i) for i in os.listdir(self.reports_dir) if i.endswith('.tib.tis')]

    def get_xml_dict(self):
        xml_dict = dict()
        xml_dict.update(self._get_truieimg_part())
        xml_dict.update(self._get_diskinfo_part())
        xml_dict.update(self._get_productinfo_part())
        xml_dict.update(self._get_archives_part())
        xml_dict.update(self._get_tiblist_part())
        xml_dict.update(self._get_machineinfo_part())

        return xml_dict

    def get_guid(self):
        guid = etree.parse(self.productinfo_rep).find('//Guid').text.rstrip().strip()

        return guid

    def get_build_number(self):
        bn = etree.parse(self.productinfo_rep).find('//Build').text.rstrip().strip()

        return bn

    def _get_all_cep_reports(self):
        cep_list = list()
        for d, dirs, files in os.walk(self.reports_dir):
            for f in files:
                if os.path.splitext(f)[1] == '.ctr':
                    cep_list.append(os.path.join(d, f))

        return cep_list

    def _get_truieimg_part(self):
        cep_report = list()
        if not self.truieimg_reps:
            return {'cep_report': cep_report}

        for truieimg_rep in self.truieimg_reps:
            xml_root = etree.parse(truieimg_rep)
            trueimg_out = [{'id': i.get('id'), 'value': i.get('value')} for i in xml_root.iterfind('//item')]
            cep_report.extend(trueimg_out)

        return {'cep_report': cep_report}

    def _get_tiblist_part(self):
        tib_parsed = list()
        for tib in self.tib_flist:
            try:
                tib_xml_dict = self.custom_parser.get_xml_dict(tib)
                if tib_xml_dict is not None:
                    tib_data = tib_xml_dict['guid_batch']
                    tib_parsed.append(tib_data)
            except:
                continue

        return {'tib_tis': tib_parsed}

    def _get_diskinfo_part(self):
        xml_root = etree.parse(self.diskinfo_rep)
        diskinfo_out = list()
        for i in xml_root.iterfind('HardDisk'):
            drive_item = dict()
            partition_list = list()
            unallocated_list = list()
            for j in i.getchildren():
                if j.tag == 'Partition':
                    partition_item = dict((k.tag, unicode(k.text).rstrip().strip()) for k in j.getchildren())
                    partition_list.append(partition_item)
                elif j.tag == 'Unallocated':
                    unallocated_item = dict((k.tag, unicode(k.text).rstrip().strip()) for k in j.getchildren())
                    unallocated_list.append(unallocated_item)
                else:
                    value = j.text
                    if value is not None:
                        drive_item.update({j.tag: value.rstrip().strip()})
            if len(partition_list) > 0: drive_item.update({'Partitions': partition_list})
            if len(unallocated_list) > 0: drive_item.update({'Unallocated': unallocated_list[0]})
            diskinfo_out.append(drive_item)

        return {'hard_disks': diskinfo_out}

    def _get_productinfo_part(self):
        xml_root = etree.parse(self.productinfo_rep)
        productinfo_out = dict((i.tag, i.text.rstrip().strip()) for i in xml_root.iterfind('*'))

        return {'productinfo': productinfo_out}

    def _get_archives_part(self):
        if not os.path.exists(self.archives_rep):
            return {'archives_database': {}}
        xml_root = etree.parse(self.archives_rep).getroot()
        archives_out = dict()
        archives_out.update({'Flags':xml_root.get('Flags'), 'generator':xml_root.get('generator'), 
                             'ver_major':xml_root.get('ver_major'), 'ver_minor':xml_root.get('ver_minor')})
        archives_list = list()
        for i in xml_root.iterfind('OnlineArchivesGroups/OnlineArchiveGroup'):
            archives_item = dict()
            archives_item.update({'Account':i.get('Account'), 'Key': i.get('Key')})
            online_archives = list()
            for j in i.iterfind('OnlineArchives/OnlineArchive'):
                online_archive_item = dict()
                online_archive_item.update({'Key':j.get('Key'), 'SessionStatus':j.get('SessionStatus'), 
                                            'Type':j.get('Type'), 'versionsstatus':j.get('VersionsStatus')})
                online_archive_item.update(dict((k.tag, unicode(k.text).rstrip().strip()) for k in j.getchildren()))
                online_archives.append(online_archive_item)
            archives_item.update({'OnlineArchives': online_archives})
            archives_list.append(archives_item)
        archives_out.update({'OnlineArchivesGroups': archives_list})

        return {'archives_database': archives_out}

    def _get_machineinfo_part(self):
        machineinfo_out = {}
        if os.path.exists(self.machineinfo_rep):
            xml_root = etree.parse(self.machineinfo_rep)
            machineinfo_out = dict((i.tag, i.text.strip()) for i in xml_root.iterfind('*') if i.text is not None)

        return {'machineinfo': machineinfo_out}    


class VmpReportParser(object):

    def __init__(self, reports_dir):
        self.tree = etree.parse(os.path.join(reports_dir, 'report.xml'))

    def get_xml_dict(self):
        xml_dict = self._to_dict(self.tree)
        return xml_dict

    def get_guid(self):
        guid = self.tree.getroot().get('InstallationID')
        return guid

    def get_version(self):
        agent_info = self.tree.getroot().find('AcronisAgentInfo/AcronisAgent').get('AgentBuild')
        return agent_info.rsplit('.', 1)[0]

    def get_build_number(self):
        agent_info = self.tree.getroot().find('AcronisAgentInfo/AcronisAgent').get('AgentBuild')
        return agent_info.rsplit('.', 1)[1]

    def _to_dict(self, etree):
        xml_root = etree.getroot()
        vmp_out = dict()
        vmp_out.update(self._vm_get_header(xml_root))
        vmp_out.update(self._vm_get_vcenters(xml_root))
        vmp_out.update(self._vm_get_hosts(xml_root))
        vmp_out.update(self._vm_get_vmachines(xml_root))
        vmp_out.update(self._vm_get_acronisagent(xml_root))
        return {'vmProtect-ACEP':vmp_out}

    def _vm_get_header(self, node):
        head_out = dict(node.attrib.items())
        return head_out

    def _vm_get_vcenters(self, node):
        vcenters_out = list()
        for i in node.iterfind('vCenters/vCenter'):
            vcenters_out.append(dict((i, j) for i, j in i.attrib.items()))
        return {'vCenters': vcenters_out}

    def _vm_get_hosts(self, node):
        vhosts_out = list()
        for i in node.iterfind('Hosts/Host'):
            datastore_list = list()
            vhost_item = dict((i, j) for i, j in i.attrib.items())
            for j in i.iterfind('Datastores/Datastore'):
                datastore_list.append(dict((i, j) for i, j in j.attrib.items()))
            vhost_item.update({'Datastores': datastore_list})
            vhosts_out.append(vhost_item)
        return {'Hosts': vhosts_out}

    def _vm_get_vmachines(self, node):
        vmachines_out = list()
        for i in node.iterfind('VirtualMachines/VirtualMachine'):
            vdisk_list = list()
            vmachine_item = dict((i, j) for i, j in i.attrib.items())
            for j in i.iterfind('VMDisks/VMDisk'):
                vdisk_list.append(dict((i, j) for i, j in j.attrib.items()))
            vmachine_item.update({'VMDisks': vdisk_list})
            vmachines_out.append(vmachine_item)
        return {'VirtualMachines': vmachines_out}

    def _vm_get_acronisagent(self, node):
        agentinfo = dict()
        agent = {'AcronisAgent': dict((i, unicode(j).rstrip().strip()) for i, j in node.find('AcronisAgentInfo/AcronisAgent').attrib.items())}
        agentinfo.update(agent)
        backuplist = list()
        for i in node.iterfind('AcronisAgentInfo/BackupLocations/StorageInfo'):
            backuplist.append(dict((i, unicode(j).rstrip().strip()) for i, j in i.attrib.items()))
        agentinfo.update({'BackupLocations': backuplist})
        tasklist = list()
        for i in node.iterfind('AcronisAgentInfo/AcronisTasks/TaskInfo'):
            tasklist.append(dict((i, unicode(j).rstrip().strip()) for i, j in i.attrib.items()))
        agentinfo.update({'AcronisTasks': tasklist})
        loglist = list()
        for i in node.iterfind('AcronisAgentInfo/Logs/Log'):
            loglist.append(dict((i, unicode(j).rstrip().strip()) for i, j in i.attrib.items()))
        agentinfo.update({'Logs': loglist})
        return {'AcronisAgentInfo': agentinfo}

class MsiInfoParser(object):

    def __init__(self, report_list):
        self.tree = None
        self._get_msinfo_report(report_list)

    def get_xml_dict(self):
        xml_dict = dict()
        if self.tree is None:
            return None
        if not self._check_is_english():
            return None
        xml_dict.update(self._get_metadata_part())
        xml_dict.update(self._get_msi_info_body())
        return xml_dict

    def _get_metadata_part(self):
        metadata = [{i.tag: i.text.rstrip().strip()} for i in self.tree.iterfind('//Metadata/*')]
        return {'metadata': metadata}

    def _get_msi_info_body(self):
        body_dict = dict()        
        for category in self.tree.iterfind('/Category'):
            self._get_msi_info_recurse(category, body_dict)
        return body_dict

    def _get_msi_info_recurse(self, category, body):        
        category_name = category.get('name')
        data_list = list()
        for elem in list(category):
            if elem.tag == 'Data':
                data_dict = {i.tag: i.text.rstrip().strip() for i in elem.iterfind('*') if i.text is not None}
                if len(data_dict) > 0:
                    data_list.append(data_dict) 
                if type(body) == dict:                   
                    body.update({category_name: data_list})
                else:
                    body.append({category_name: data_list})
            else:
                if category_name not in body:
                    if type(body) == dict:
                        body[category_name] = dict()
                    self._get_msi_info_recurse(elem, body[category_name])
                else:
                    self._get_msi_info_recurse(elem, body)

    def _get_msinfo_report(self, report_list):
        for i in report_list:
            try:
                tag = etree.parse(i).getroot().tag
            except Exception as e:
                continue
            if tag == 'MsInfo':
                self.tree = etree.parse(i)
                break

    def _check_is_english(self):
        check_field = self.tree.find('.//Category[@name="System Summary"]')
        if check_field is None:
            return False
        return True

class XmlCustomParser(object):

    def get_section_name(self, node):
        retval = None
        if node.tag == 'MSSQL_INFO':
            retval = 'mssql_info'
        elif node.attrib.get('name') == 'ActiveDirectoryAcepReport':
            retval = 'ad_acep_report'
        elif node.tag == 'batch':
            retval = 'guid_batch'
        else:
            pass

        return retval

    def iter_nodes(self, node, parent_dict):
        node_dict = dict()
        try:
            node_dict.update(node.attrib)
        except AttributeError:
            pass

        for i in node.iterchildren():
            child_dict = dict()
            new_dict = dict()
            new_dict = self.iter_nodes(i, child_dict)
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
                node_dict['text'] = node.text
            parent_dict[namespace] = node_dict

        return parent_dict

    def get_xml_dict(self, xml_file):
        root = objectify.parse(xml_file).getroot()
        report_key = self.get_section_name(root)

        if report_key is None:
            return None

        empty_dict = dict()
        parsed_dict = self.iter_nodes(root, empty_dict)

        return {report_key: parsed_dict}

if __name__ == '__main__':                            
    #a = AbrReportParser(r'dc2abda4-f9d5-4928-91d3-cc3f87fd9124')
    #print a.get_xml_dict()
    #print a.get_guid()
    #print a.get_version()
    #print a.get_build_number()
    #print a.get_report_type()
    b = AtihReportParser('.')
    print b.get_xml_dict()
    print b.get_guid()
    print b.get_build_number()
    #c = VmpReportParser('out_2')
    #print c.get_xml_dict()
    #print c.get_guid()
    #print c.get_version()
    #print c.get_build_number()

