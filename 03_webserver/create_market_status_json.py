#!/usr/bin/env python3
# pip3 install redis

import os
import sys
import json
import redis
import datetime

from contextlib import suppress

import pytz
g_tz_utc = pytz.UTC
g_tz_et = pytz.timezone('US/Eastern')

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis,wait_for_ready

g_debug_python = False

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def write_to_file(text, filename):
	with open(filename, 'w') as f:
		f.write(text)
		f.close()

def dump_market_status(r, filename):
	market_clock_str = r.get('ALPACA:MARKET:CLOCK:JSON')
	if market_clock_str is None:
		eprint(f'ALPACA:MARKET:CLOCK:JSON returned None!', flush=True)
		return
	if g_debug_python:
		now_z = datetime.datetime.now(g_tz_utc)
		now_et = now_z.astimezone(g_tz_et)
		timestamp_str = now_et.strftime('%Y-%m-%d %H:%M:%S')
		print(f'{timestamp_str}: Writing {filename} ...', flush=True)
	write_to_file(market_clock_str, filename)

def acquire_environment():
	global g_debug_python

	wwwdir = os.getenv('WWWDIR')
	if wwwdir is not None: os.chdir(wwwdir)
	with suppress(FileExistsError): os.mkdir('market_data')
	os.chdir('market_data')

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
	redis_url = acquire_environment()
	r = connect_to_redis(redis_url, True, False, g_debug_python)
#	wait_for_ready(r, 'DASHBOARD:READY', 0.1)

	dump_market_status(r, f'market_status.json')
