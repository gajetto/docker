import os
import json
import datetime
import traceback
import prl_parser as prl
from uuid import uuid4
from StringIO import StringIO
from settings import REPORTS, REPORTS_RAW, FAILED

class CESParser(object):

    def __init__(self, form_dict):
        self.processed_raw_list = ['ATIH', 'ADD', 'ABR']
        self.form_dict = form_dict
        self.product_name = self.form_dict['Product'].replace(' ', '_').replace('.', '_')

    def save_report(self):
        report = dict()
        try:
            report.update({'Location': self.form_dict.get('Location')})
        except Exception, e:
            report.update({'Location': 'n/a'})
        try:            
            report.update({'Product': self.product_name})
            report.update({'Received': datetime.datetime.now().isoformat()})
            report.update({'IP': self.form_dict.get('HostIp')})
            report.update({'ReportId': self.form_dict.get('ReportId')})
            self._handle_internal_xml(report)
        except Exception, e:
            #self._save_failed_request()
            tb_object = traceback.format_exc()
            raise(Exception(tb_object))

    def _handle_internal_xml(self, report):
        xml_raw = StringIO(self.form_dict.get('XML'))
        prl_parser = prl.PrlParser(xml_raw, self.product_name)
        prl_part = prl_parser.get_xml_dict()
        if prl_parser.guid is None:
             raise Exception('Guid for {0} is None'.format(self.product_name))
        report.update({'InstanceId': prl_parser.guid})
        report.update(prl_part)
        product_full_name = self._generate_full_name(prl_parser)
        report.update({'Product_Full_Name': product_full_name})
        report.update({'Build_Number': prl_parser.build_number})
        report.update({'Version': str(prl_parser.version)})
        self._save_json_object(prl_parser.guid, report)       
        
    def _generate_full_name(self, prl_object):
        base_name = self.product_name.replace('_MC', '').replace('_MMS', '').replace('_AMS', '')
        if prl_object.version is not None:
            base_name += '_{0}'.format(prl_object.version).replace(' ', '_').replace('.', '_')
        if prl_object.report_type is not None:
            base_name += '_{0}'.format(prl_object.report_type).replace(' ', '_').replace('.', '_')
        return base_name

    def _save_json_object(self, guid, report):
        product_dir = self._get_product_directory()
        if product_dir is None:
            raise Exception('Product directory is None')
        if guid is None:
            raise Exception('Guid for {0} is None'.format(self.product_name))
        save_dir = os.path.join(REPORTS, product_dir)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        report_fname_bkp = os.path.join(save_dir, guid + '.out')
        report_fname = os.path.join(save_dir, guid + '.rep')
        with open(report_fname_bkp, 'w') as report_out:
            json_body = json.dumps(report)
            report_out.write(json_body)
        os.rename(report_fname_bkp, report_fname)
        self._save_json_raw_data(report, product_dir, guid)

    def _get_product_directory(self):
        retval = None
        if 'ati' in self.product_name.lower():
            retval = 'ATIH'
        elif 'abr' in self.product_name.lower():
            retval = 'ABR'
        elif 'add' in self.product_name.lower():
            retval = 'ADD'
        elif 'asd' in self.product_name.lower():
            retval = 'ASD'
        elif 'vmprotect' in self.product_name.lower():
            retval = 'VMPROTECT'
        else:
            pass
        return retval

    def _save_failed_request(self):
        failed_items = '&'.join(['{0}={1}'.format(k.encode('utf-8'), v.encode('utf-8')) for (k, v ) in self.form_dict.items()])
        failed_dir = os.path.join(FAILED, self.product_name)
        if not os.path.exists(failed_dir):
            os.makedirs(failed_dir)
        failed_fname = os.path.join(failed_dir, str(uuid4()) + '.out')
        with open(failed_fname, 'w') as failed_out:
            failed_out.write(failed_items)

    def _save_json_raw_data(self, report, product_dir, guid):
        if product_dir not in self.processed_raw_list:
            return
        raw_report = report.copy()
        if 'ParallelsProblemReport' in raw_report:
            del raw_report['ParallelsProblemReport']
        raw_report.update({'Raw_Data': self.form_dict.get('XML')})
        date_folder = report.get('Received').split('T')[0]
        save_dir = os.path.join(REPORTS_RAW, product_dir, date_folder)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        raw_report_fname_bkp = os.path.join(save_dir, guid + '.out')
        raw_report_fname = os.path.join(save_dir, guid + '.rep')
        with open(raw_report_fname_bkp, 'w') as raw_out:
            json_body = json.dumps(raw_report)
            raw_out.write(json_body)
        os.rename(raw_report_fname_bkp, raw_report_fname)
       