import os
import sys
import subprocess
import datetime
import json
import logging
import shutil
import contextlib
import resource
import tarfile
import MySQLdb

from logging.handlers import RotatingFileHandler
from uuid import uuid4
from lxml import etree
from prl_parser import PrlParser
from settings import *


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FOLDER = os.path.normpath(os.path.join(CURRENT_DIR, 'logs'))
if(not os.path.exists(LOG_FOLDER)):
    os.makedirs(LOG_FOLDER)

LOG_FILE = os.path.join(LOG_FOLDER, '{0}.log'.format(datetime.datetime.now().strftime('%Y-%m-%d')))

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)-15s %(message)s', datefmt='%Y-%m-%d,%H:%M:%S', stream=sys.stdout)
logger = logging.getLogger()

handler = RotatingFileHandler(LOG_FILE, maxBytes=100000, backupCount=1)
handler.setLevel(logging.INFO)

logger.addHandler(handler)
logger.setLevel(logging.INFO)

UNPACK_DIR = os.path.join(TMP, 'extract_folder')
if not os.path.exists(UNPACK_DIR):
    os.makedirs(UNPACK_DIR)


# Helper context manager
@contextlib.contextmanager
def limit_resources(resource_limit_dict):
    """This context manager limits resources for the wrapped code.
    The limits are accepted as {resource_name (constants from resource module): resource limit.
    For example, if we need to limit address space usage to 16 MB
    and maximum file size that process can create to 128 MB the following dict should be passed
    to this context manager: {resource.RLIMIT_AS:  1 <<  24, resource, resource.RLIMIT_FSIZE: 1 << 27}"""
    old_limits = {}
    for resource_type, limit in resource_limit_dict.iteritems():
        old_limits.update({resource_type: resource.getrlimit(resource_type)})
        resource.setrlimit(resource_type, (limit, old_limits[resource_type][1]))  # set soft limit
    try:
        yield
    finally:
        for resource_type, limits in old_limits.iteritems():
            resource.setrlimit(resource_type, (limits[0], limits[1])) # restore



def clean_unpack_dir(unpk_dir):
    for unpk in os.listdir(unpk_dir):
        unpk_full = os.path.join(unpk_dir, unpk)
        if os.path.isdir(unpk_full):
            shutil.rmtree(unpk_full)
        else:
            os.unlink(unpk_full)


def extract_report_archive(archive_file):
    retval = None
    archive_file = archive_file.replace('\\', '/')
    extract_folder = os.path.join(UNPACK_DIR, str(uuid4())).replace('\\', '/')

    if not os.path.exists(extract_folder):
        os.makedirs(extract_folder)

    # Fail if archive is not tar
    if not tarfile.is_tarfile(archive_file):
        raise Exception('Specified archive is not in tar format')

    archive_file_tarfile = tarfile.open(archive_file, errorlevel=1)  # raise OSErrors and IOErrors

    with limit_resources({resource.RLIMIT_FSIZE: MAX_COMPRESSED_FILE_SIZE}):
        archive_file_tarfile.extractall(extract_folder)

    archive_file_tarfile.close()

    for root, subdirs, flist in os.walk(extract_folder):
        xml_list = [os.path.join(root, one_file) for one_file in flist if os.path.splitext(one_file)[1] == '.xml']
        if xml_list:
            retval = os.path.split(xml_list[0])[0]
            break

    return retval

def get_product_name(main_xml):
    retval = None
    xml_data = etree.parse(main_xml)
    product_node = xml_data.getroot().find('ProductName')
    if product_node is not None:
        retval = product_node.text

    return retval

def get_product_directory(product_name):
    retval = None
    if 'ati' in product_name.lower():
        retval = 'ATIH'
    elif 'abr' in product_name.lower():
        retval = 'ABR'
    elif 'add' in product_name.lower():
        retval = 'ADD'
    elif 'asd' in product_name.lower():
        retval = 'ASD'
    elif 'vmprotect' in product_name.lower():
        retval = 'VMPROTECT'
    else:
        pass

    return retval

def get_report_id(archive_file):
    archive_fname = os.path.split(archive_file)[1]
    report_id = archive_fname.split('_')[0].replace('.', '')

    return report_id


def process_one_acep(archive_file):
    report_folder = extract_report_archive(archive_file)
    report_id = get_report_id(archive_file)

    try:
        if report_folder is None:
            raise Exception('Report folder is empty!!')
        main_xml = os.path.join(report_folder, 'Report.xml')
        if not os.path.exists(main_xml):
            raise Exception('Main Report.xml not found in acep archive!!')
        product_name = get_product_name(main_xml)
        if product_name is None:
            raise Exception('ProductName not found in the Main Report.xml!!')

    except Exception as e:
        logger.error(e, exc_info=True)
        report_status_to_db(status=False)
        raise e

    try:
        hostinfo_xml = os.path.join(report_folder, 'HostInfo.xml')
        if not os.path.exists(hostinfo_xml):
            raise Exception('HostInfo.xml not found in acep archive!!')
        hoststat_xml = os.path.join(report_folder, 'HostStatistics.xml')
        if not os.path.exists(hoststat_xml):
            raise Exception('HostStatistics.xml not found in acep archive!!')

        prl_parser = PrlParser(main_xml, product_name)
        received_date = datetime.datetime.now()
        report = prl_parser.get_xml_dict_v2(hostinfo_xml, hoststat_xml)
        report.update({'Received': received_date.isoformat()})
        report.update({'Product': product_name})
        report.update({'Product_Full_Name': product_name})
        report.update({'ReportId': report_id})
        if prl_parser.guid is None:
            raise Exception('Guid for {0} is None'.format(product_name))
        report.update({'InstanceId': prl_parser.guid})
        report.update({'Build_Number': prl_parser.build_number})
        report.update({'Version': prl_parser.version})
        save_json_object(product_name, prl_parser.guid, report)
        save_raw_report(archive_file, product_name, report_id, received_date)

    except Exception as e:
        logger.error(e, exc_info=True)
        report_status_to_db(status=False, product=product_name)
        raise e

    else:
        report_status_to_db(status=True, product=product_name, report_id=int(report_id))



def save_json_object(product_name, guid, report):
    product_dir = get_product_directory(product_name)
    if product_dir is None:
        raise Exception('Product directory is None')    
    save_dir = os.path.join(REPORTS, product_dir)
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    report_fname_bkp = os.path.join(save_dir, guid + '.out')
    report_fname = os.path.join(save_dir, guid + '.rep')
    with open(report_fname_bkp, 'w') as report_out:
        json_body = json.dumps(report)
        report_out.write(json_body)
    os.rename(report_fname_bkp, report_fname)

def save_raw_report(archive_file, product_name, report_id, recieved_date):
    product_dir = get_product_directory(product_name)
    date_folder = recieved_date.isoformat().split('T')[0]
    save_dir_raw = os.path.join(REPORTS_RAW, product_dir, date_folder)
    if not os.path.exists(save_dir_raw):
        os.makedirs(save_dir_raw)
    raw_report_fname = os.path.join(save_dir_raw, report_id + '.tar.gz')
    shutil.copy(archive_file, raw_report_fname)
    os.unlink(archive_file)


def report_status_to_db(status, product='Undefined', report_id=0):
    """This function writes the status of ACEP report parsing to specified DB table.
    If provided argument 'status' is true, the record in DB will have 1 as status, else it will have 0.
    If product name is specified it will be present in the DB record too.
    If report_id is specified it will be present in the DB record, defaults to 0."""
    status_code = 1 if status else 0
    try:
        db_connection = MySQLdb.connect(host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, passwd=MYSQL_PASSWD,
                                        db=MYSQL_DB)
        cursor = db_connection.cursor()
    except Exception as e:
        logger.error(e, exc_info=True)
        logger.error("Couldn't connect to MySQL!")
        return 0

    try:
        cursor.execute("INSERT INTO sendReportsStatus (status, product, date, report_id) VALUES (%s, %s, %s, %s)",
                       (status_code, product, datetime.datetime.now(), report_id))
        db_connection.commit()
    except Exception as e:
        logger.error(e, exc_info=True)
        logger.error('An error occurred while trying to insert into MySQL DB!')
        return 0
    finally:
        del db_connection


def main(reports_raw_dir):
    clean_unpack_dir(UNPACK_DIR)
    for i in [j for j in os.listdir(reports_raw_dir) if os.path.splitext(j)[1]=='.gz']:
        cur_report = os.path.join(reports_raw_dir, i)
        logger.info(' --- Process {0} acep report - BEGIN --- '.format(cur_report))
        try:
            process_one_acep(cur_report)
        except Exception as e:
            if os.path.exists(cur_report):
                if MOVE_FAILED_REPORTS:
                    failed_report_full = os.path.join(FAILED, i)
                    if os.path.exists(failed_report_full):
                        os.unlink(failed_report_full)
                    shutil.move(cur_report, FAILED)
                    logger.error('Could not process report at {}, moving it to {}'.format(cur_report, FAILED))
                else:
                    os.unlink(cur_report)
            logger.error(e, exc_info=True)
            logger.error(' --- Process {0} acep report - ERROR!! --- '.format(cur_report))
        else:
            logger.info(' --- Process {0} acep report - DONE --- '.format(cur_report))



if __name__ == '__main__':
    main(sys.argv[1])
