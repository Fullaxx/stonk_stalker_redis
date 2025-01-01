#!/usr/bin/env python3
# pip3 install redis

import os
import sys
import json
import time
import redis
import signal

from datetime import datetime
from contextlib import suppress

sys.path.append('.')
sys.path.append('/app')
from redis_helpers import connect_to_redis,wait_for_ready

usleep = lambda x: time.sleep(x/1000000.0)

g_debug_python = False

g_shutdown = False
def signal_handler(sig, frame):
	global g_shutdown
	g_shutdown = True

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def bailmsg(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(1)

def write_to_file(text, filename):
	with open(filename, 'w') as f:
		f.write(text)
		f.close()

def dump_market_status(r, now_dt, filename):
	market_clock_str = r.get('MARKET:CLOCK')
	if market_clock_str is None: return
	print(f'{now_dt} Writing {filename} ...', flush=True)
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

	signal.signal(signal.SIGINT,  signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

	next = 0
	while not g_shutdown:
		now_dt = datetime.utcnow()
		now_s = int(now_dt.timestamp())
		if (now_s >= next):
			dump_market_status(r, now_dt, f'market_status.json')
			next = now_s + 1
		usleep(1000)
