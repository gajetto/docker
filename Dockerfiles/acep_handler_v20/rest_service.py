import sys
import logging
import datetime
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, json
import ces_parser as CP
from settings import LOG

app = Flask(__name__)

@app.route('/', methods = ['GET'])
def index_handler():
    resp = {'message': 'Acronis Acep REST service'}
    return jsonify(resp)

@app.route('/save_xml_json', methods = ['POST'])
def save_xml_json_handler():
    resp = {'message': 'Incorrect input parameters'}
    if request.headers['Content-Type'] == 'application/json':
        resp = {'Send params': json.dumps(request.json)}
    return jsonify(resp)

@app.route('/save_xml_test', methods = ['POST'])
def save_xml_test_handler():
    data = '\n'.join(['{0} - {1}'.format(k.encode('utf-8'), v.encode('utf-8')) for (k, v ) in request.form.items()])
    return data

@app.route('/save_xml', methods = ['POST'])
def save_xml_handler():
    retval = {'status': 'ok'}
    app.logger.info('Begin - {0}'.format(datetime.datetime.now()))
    ces_parser = CP.CESParser(request.form)
    try:
        retval.update({'product': ces_parser.product_name})
        ces_parser.save_report()
        app.logger.info('Done - {0}'.format(datetime.datetime.now()))
    except Exception, e:
        retval['status'] = 'fail'
        message = str(e).encode('utf-8')
        app.logger.critical(message)
    return jsonify(retval)
   
if __name__ == '__main__':
    handler = RotatingFileHandler(LOG, maxBytes=10000, backupCount=1)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.run(debug=True)
