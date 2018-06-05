#!/usr/bin/python2.7
import sys
import logging
from logging.handlers import RotatingFileHandler

if '/var/www/acep-rest' not in sys.path:
    sys.path.insert(0, '/var/www/acep-rest')

from settings import LOG
from rest_service import app

handler = RotatingFileHandler(LOG, maxBytes=10000, backupCount=1)
handler.setLevel(logging.INFO)

application = app
application.debug = True
application.logger.addHandler(handler)
