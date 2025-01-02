#!/usr/bin/env python3
# pip3 install redis
# https://www.geeksforgeeks.org/create-temporary-files-and-directories-using-python-tempfile/

import os
import sys
import time
import pytz
import redis
import shutil
import signal
import datetime
import tempfile

from pytz import timezone
g_tz_utc = timezone('UTC')
g_tz_et = timezone('US/Eastern')

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis,wait_for_ready

g_debug_python = False
g_wait_for_ready = True

g_shutdown = False
def signal_handler(sig, frame):
	global g_shutdown
	g_shutdown = True

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def process_table(key):
	val = r.get(key)
	table_name = key.split(':')[4]
	table_name_formatted = table_name.replace('/','-')
	print(key, val, table_name_formatted)

#	print(tempfile.gettempdir())
#	tempfile.tempdir = "/tmp"
#	print(tempfile.gettempdir())
	secure_temp_dir = tempfile.mkdtemp(prefix=f'{g_today_stamp}_', suffix=f'_{table_name_formatted}')

	cmd = f'./indicators2redis.py -d {secure_temp_dir} -k {key}'
	os.system(cmd)

	if not g_debug_python:
		shutil.rmtree(secure_temp_dir)

def acquire_environment():
	global g_wait_for_ready, g_debug_python

	redis_url = os.getenv('REDIS_URL')
	if redis_url is None: bailmsg('Set REDIS_URL')

	swfr_env_var = os.getenv('WAIT_FOR_READY')
	if swfr_env_var is not None:
		flags = ('0', 'n', 'N', 'f', 'F')
		if (swfr_env_var.startswith(flags)): g_wait_for_ready = False
		if (swfr_env_var == 'off'): g_wait_for_ready = False
		if (swfr_env_var == 'OFF'): g_wait_for_ready = False

	debug_env_var = os.getenv('DEBUG_PYTHON')
	if debug_env_var is not None:
		flags = ('1', 'y', 'Y', 't', 'T')
		if (debug_env_var.startswith(flags)): g_debug_python = True
		if (debug_env_var == 'on'): g_debug_python = True
		if (debug_env_var == 'ON'): g_debug_python = True

	return redis_url

if __name__ == '__main__':
	g_today_stamp = datetime.datetime.now(g_tz_et).strftime('%y%m%d')

#	parser = ArgumentParser()
#	parser.add_argument('--symbol', '-s', type=str, required=True)
#	args = parser.parse_args()

	redis_url = acquire_environment()
	r = connect_to_redis(redis_url, True, False, g_debug_python)

	if g_wait_for_ready:
		wait_for_ready(r, 'DASHBOARD:READY', 0.1)

	searchpattern = f'DASHBOARD:TABLES:SORTED:MCAP:*'
	tables_list = sorted(r.scan_iter(searchpattern))

	signal.signal(signal.SIGINT,  signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

#	While we are looping pop a table from loop_list and pass it to process_table())
#	Whenever loop_list becomes empty, copy tables_list back into loop_list and start over
	next = 0
	loop_list = []
	while not g_shutdown:
		if (len(loop_list) == 0):
			loop_list = tables_list.copy()
		now_dt = datetime.datetime.now(g_tz_utc)
		now_s = int(now_dt.timestamp())
		if (now_s >= next):
			key = loop_list.pop()
			process_table(key)
			next = now_s + 30
		time.sleep(0.1)
