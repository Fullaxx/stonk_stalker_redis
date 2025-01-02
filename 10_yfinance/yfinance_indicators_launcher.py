#!/usr/bin/env python3
# pip3 install redis
# https://www.geeksforgeeks.org/create-temporary-files-and-directories-using-python-tempfile/

import os
import sys
#import csv
#import json
import time
import pytz
import redis
import shutil
import datetime
import tempfile

#from pprint import pprint
#from pytz import timezone
#from datetime import datetime,date
#from contextlib import suppress
#from argparse import ArgumentParser

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis

g_debug_python = False

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def process_table(key, today_stamp):
	val = r.get(key)
	table_name = key.split(':')[4]
	table_name_formatted = table_name.replace('/','-')
	print(key, val, table_name_formatted)

#	print(tempfile.gettempdir())
#	tempfile.tempdir = "/tmp"
#	print(tempfile.gettempdir())
	secure_temp_dir = tempfile.mkdtemp(prefix=f'{today_stamp}_', suffix=f'_{table_name_formatted}')

	cmd = f'./indicators2redis.py -d {secure_temp_dir} -k {key}'
	os.system(cmd)

	if not g_debug_python:
		shutil.rmtree(secure_temp_dir)

def get_date_stamp(use_strict_date_calculation):
#	Assume TZ=US/Eastern
	today_stamp = datetime.date.today().strftime('%y%m%d')

	if use_strict_date_calculation:
		zulu_dt = datetime.datetime.utcnow()
		etz = pytz.timezone('US/Eastern')
		eastern_dt = zulu_dt.astimezone(etz)
		today_stamp = eastern_dt.strftime('%y%m%d')

	return today_stamp

def acquire_environment():
	global g_debug_python

	redis_url = os.getenv('REDIS_URL')
	if redis_url is None: bailmsg('Set REDIS_URL')

	debug_env_var = os.getenv('DEBUG_PYTHON')
	if debug_env_var is not None:
		flags = ('1', 'y', 'Y', 't', 'T')
		if (debug_env_var.startswith(flags)): g_debug_python = True
		if (debug_env_var == 'on'): g_debug_python = True
		if (debug_env_var == 'ON'): g_debug_python = True

	return redis_url

if __name__ == '__main__':
#	parser = ArgumentParser()
#	parser.add_argument('--symbol', '-s', type=str, required=True)
#	args = parser.parse_args()

	redis_url = acquire_environment()
	r = connect_to_redis(redis_url, True, False, g_debug_python)

#	Assume TZ=US/Eastern
	today_stamp = get_date_stamp(False)

#	XXX TODO FIXME: RE-WRITE THIS LOOP TO LAUNCH AFTER 8PM AND HANDLE SIGNALS
	searchpattern = f'DASHBOARD:TABLES:SORTED:MCAP:*'
	for key in sorted(r.scan_iter(searchpattern)):
		process_table(key, today_stamp)
		time.sleep(30)
